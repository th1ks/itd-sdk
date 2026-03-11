from __future__ import annotations

import asyncio
import unittest
from typing import Any

from itd_sdk.client import CommentsAPI, NotificationsAPI, PostsAPI, SearchAPI, SocialAPI


class FakeHTTP:
    def __init__(self, responses: dict[tuple[str, str], Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def request_api(self, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append({"method": method, "path": path, **kwargs})
        return self.responses[(method, path)]


class ClientAPITestCase(unittest.IsolatedAsyncioTestCase):
    async def test_create_post_unwraps_and_normalizes_response(self) -> None:
        http = FakeHTTP(
            {
                ("POST", "/posts"): {
                    "data": {
                        "id": "post-1",
                        "content": "hello",
                        "author": {
                            "id": "user-1",
                            "username": "alice",
                            "displayName": "Alice",
                            "verified": True,
                        },
                        "likesCount": 7,
                        "commentsCount": 3,
                        "repostsCount": 2,
                        "attachments": [],
                    }
                }
            }
        )
        api = PostsAPI(http)

        post = await api.create_post(text="hello")

        self.assertEqual(post.id, "post-1")
        self.assertEqual(post.text, "hello")
        self.assertTrue(post.author.isVerified)
        self.assertEqual(post.reactions.total, 7)
        self.assertEqual(post.stats.comments, 3)
        self.assertEqual(http.calls[0]["json"], {"content": "hello"})

    async def test_create_comment_unwraps_and_normalizes_response(self) -> None:
        http = FakeHTTP(
            {
                ("POST", "/posts/post-1/comments"): {
                    "data": {
                        "id": "comment-1",
                        "postId": "post-1",
                        "content": "nice",
                        "author": {
                            "id": "user-1",
                            "username": "alice",
                            "displayName": "Alice",
                            "verified": True,
                        },
                        "likesCount": 2,
                        "repliesCount": 1,
                        "attachments": [],
                    }
                }
            }
        )
        api = CommentsAPI(http)

        comment = await api.create_comment("post-1", content="nice")

        self.assertEqual(comment.id, "comment-1")
        self.assertEqual(comment.text, "nice")
        self.assertTrue(comment.author.isVerified)
        self.assertEqual(comment.reactions.total, 2)
        self.assertEqual(comment.stats.replies, 1)

    async def test_comments_use_nested_pagination_cursor(self) -> None:
        http = FakeHTTP(
            {
                ("GET", "/posts/post-1/comments"): {
                    "data": {
                        "comments": [
                            {
                                "id": "comment-1",
                                "postId": "post-1",
                                "content": "first",
                                "author": {"id": "user-1", "username": "alice"},
                                "attachments": [],
                            }
                        ],
                        "pagination": {"nextCursor": "cursor-2"},
                    }
                }
            }
        )
        api = CommentsAPI(http)

        page = await api.get_comments("post-1")

        self.assertEqual(page.next_cursor, "cursor-2")
        self.assertEqual(page.items[0].text, "first")

    async def test_notifications_unwrap_nested_payload(self) -> None:
        http = FakeHTTP(
            {
                ("GET", "/notifications/"): {
                    "data": {
                        "notifications": [
                            {
                                "id": "notif-1",
                                "type": "like",
                                "targetId": "post-1",
                                "read": False,
                                "createdAt": "2026-03-11T00:00:00Z",
                                "actor": {
                                    "id": "user-1",
                                    "username": "alice",
                                    "displayName": "Alice",
                                    "avatar": "A",
                                },
                            }
                        ],
                        "hasMore": True,
                    }
                }
            }
        )
        api = NotificationsAPI(http)

        page = await api.get_notifications(limit=1)

        self.assertEqual(page.next_cursor, "1")
        self.assertEqual(page.items[0].type, "post_reaction")
        self.assertEqual(page.items[0].payload.actors[0].username, "alice")

    async def test_search_users_normalizes_profiles_and_cursor(self) -> None:
        http = FakeHTTP(
            {
                ("GET", "/users/search"): {
                    "data": {
                        "users": [
                            {
                                "id": "user-1",
                                "username": "alice",
                                "displayName": "Alice",
                                "verified": True,
                                "followersCount": 5,
                            }
                        ],
                        "pagination": {"nextCursor": "cursor-2"},
                    }
                }
            }
        )
        api = SearchAPI(http)

        page = await api.search_users("ali")

        self.assertEqual(page.next_cursor, "cursor-2")
        self.assertTrue(page.items[0].isVerified)
        self.assertEqual(page.items[0].stats.followers, 5)

    async def test_global_search_normalizes_users(self) -> None:
        http = FakeHTTP(
            {
                ("GET", "/search"): {
                    "data": {
                        "users": [
                            {
                                "id": "user-1",
                                "username": "alice",
                                "displayName": "Alice",
                                "verified": True,
                            }
                        ],
                        "hashtags": [{"name": "python", "postsCount": 4}],
                    }
                }
            }
        )
        api = SearchAPI(http)

        result = await api.global_search("ali")

        self.assertTrue(result.users[0].isVerified)
        self.assertEqual(result.hashtags[0].count, 4)

    async def test_track_views_batch_uses_bounded_concurrency(self) -> None:
        class RecordingPostsAPI(PostsAPI):
            def __init__(self) -> None:
                self.active = 0
                self.peak = 0
                self.seen: list[str] = []

            async def track_view(self, post_id: str) -> None:
                self.active += 1
                self.peak = max(self.peak, self.active)
                await asyncio.sleep(0.01)
                self.seen.append(post_id)
                self.active -= 1

        api = RecordingPostsAPI()

        await api.track_views_batch([f"post-{index}" for index in range(25)])

        self.assertEqual(len(api.seen), 25)
        self.assertGreater(api.peak, 1)
        self.assertLessEqual(api.peak, 10)

    async def test_social_supports_opaque_cursor_without_casting(self) -> None:
        http = FakeHTTP(
            {
                ("GET", "/users/user-1/followers"): {
                    "data": {
                        "users": [
                            {
                                "id": "user-2",
                                "username": "bob",
                                "displayName": "Bob",
                                "verified": True,
                            }
                        ],
                        "pagination": {"nextCursor": "cursor-2"},
                    }
                }
            }
        )
        api = SocialAPI(http)

        page = await api.get_followers("user-1", cursor="cursor-1")

        self.assertEqual(http.calls[0]["params"], {"cursor": "cursor-1", "limit": "20"})
        self.assertEqual(page.next_cursor, "cursor-2")
        self.assertTrue(page.items[0].isVerified)

    async def test_social_falls_back_to_page_numbers_when_cursor_is_numeric(self) -> None:
        http = FakeHTTP(
            {
                ("GET", "/users/user-1/following"): {
                    "data": {
                        "users": [
                            {
                                "id": "user-2",
                                "username": "bob",
                                "displayName": "Bob",
                            }
                        ],
                        "pagination": {"hasMore": True},
                    }
                }
            }
        )
        api = SocialAPI(http)

        page = await api.get_following("user-1", cursor="2")

        self.assertEqual(http.calls[0]["params"], {"page": "2", "limit": "20"})
        self.assertEqual(page.next_cursor, "3")


if __name__ == "__main__":
    unittest.main()
