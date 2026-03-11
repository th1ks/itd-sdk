from __future__ import annotations

from collections.abc import Mapping
from typing import Any, BinaryIO
from urllib.parse import quote

from ._http import _HTTPClient
from ._normalizers import (
    extract_next_cursor,
    normalize_comment,
    normalize_hashtag,
    normalize_notification,
    normalize_post,
    normalize_profile,
    normalize_relation_user,
)
from ._utils import build_query, build_upload_file, drop_none
from .exceptions import ApiError
from .models import Page, SDKObject, to_model


DEFAULT_ORIGIN = "https://итд.com"


class _BaseAPI:
    def __init__(self, http: _HTTPClient) -> None:
        self._http = http


class RawAPI(_BaseAPI):
    async def request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = False,
        json: dict[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        files: Any | None = None,
    ) -> Any:
        if auth:
            if files is not None:
                raise ValueError("Auth requests with files are not supported")
            return await self._http.request_auth(method, path, json=json, params=params, headers=headers)
        return await self._http.request_api(method, path, json=json, params=params, headers=headers, files=files)


class AuthAPI(_BaseAPI):
    async def register(
        self,
        *,
        email: str,
        password: str,
        turnstile_token: str | None = None,
    ) -> SDKObject:
        payload = drop_none(email=email, password=password, turnstileToken=turnstile_token)
        return to_model(await self._http.request_auth("POST", "/sign-up", json=payload))

    async def login(
        self,
        *,
        email: str,
        password: str,
        turnstile_token: str | None = None,
    ) -> SDKObject:
        payload = drop_none(email=email, password=password, turnstileToken=turnstile_token)
        response = await self._http.request_auth("POST", "/sign-in", json=payload)
        if isinstance(response, dict) and response.get("accessToken"):
            self._http.set_access_token(str(response["accessToken"]))
        return to_model(response)

    async def verify_otp(self, *, email: str, password: str, otp: str, flow_token: str) -> SDKObject:
        payload = {
            "email": email,
            "password": password,
            "otp": otp,
            "flowToken": flow_token,
        }
        response = await self._http.request_auth("POST", "/verify-otp", json=payload)
        if isinstance(response, dict) and response.get("accessToken"):
            self._http.set_access_token(str(response["accessToken"]))
        return to_model(response)

    async def resend_otp(self, *, email: str, flow_token: str) -> None:
        payload = {"email": email, "flowToken": flow_token}
        await self._http.request_auth("POST", "/resend-otp", json=payload)

    async def refresh_session(self) -> SDKObject:
        response = await self._http.request_auth("POST", "/refresh")
        if isinstance(response, dict) and response.get("accessToken"):
            self._http.set_access_token(str(response["accessToken"]))
        return to_model(response)

    async def logout(self) -> None:
        try:
            await self._http.request_auth("POST", "/logout")
        finally:
            self._http.set_access_token(None)

    async def logout_all(self) -> None:
        try:
            await self._http.request_auth("POST", "/logout-all")
        finally:
            self._http.set_access_token(None)

    async def forgot_password(
        self,
        *,
        email: str,
        turnstile_token: str | None = None,
    ) -> SDKObject:
        payload = drop_none(email=email, turnstileToken=turnstile_token)
        return to_model(await self._http.request_auth("POST", "/forgot-password", json=payload))

    async def reset_password(
        self,
        *,
        new_password: str,
        email: str | None = None,
        flow_token: str | None = None,
        otp: str | None = None,
    ) -> None:
        payload = drop_none(
            email=email,
            flowToken=flow_token,
            otp=otp,
            newPassword=new_password,
        )
        await self._http.request_auth("POST", "/reset-password", json=payload)

    async def change_password(self, payload: Mapping[str, Any]) -> None:
        await self._http.request_auth("POST", "/change-password", json=dict(payload))


class UsersAPI(_BaseAPI):
    async def check_username(self, username: str) -> bool:
        result = await self._http.request_api("GET", "/users/check-username", params={"username": username})
        return bool(result.get("available"))

    async def create_profile(self, payload: Mapping[str, Any]) -> SDKObject:
        return to_model(await self._http.request_api("POST", "/users/profile", json=dict(payload)))

    async def get_me(self) -> SDKObject:
        return to_model(normalize_profile(await self._http.request_api("GET", "/users/me")))

    async def update_me(self, payload: Mapping[str, Any]) -> SDKObject:
        return to_model(await self._http.request_api("PUT", "/users/me", json=dict(payload)))

    async def get_profile(self, username: str) -> SDKObject:
        return to_model(normalize_profile(await self._http.request_api("GET", f"/users/{username}")))

    async def follow(self, user_id: str) -> None:
        await self._http.request_api("POST", f"/users/{user_id}/follow", json={})

    async def unfollow(self, user_id: str) -> None:
        await self._http.request_api("DELETE", f"/users/{user_id}/follow")

    async def get_privacy_settings(self) -> SDKObject:
        response = await self._http.request_api("GET", "/users/me/privacy")
        return to_model(
            {
                "isPrivate": response.get("isPrivate", False),
                "showLastSeen": response.get("showLastSeen", True),
                "whoCanPostOnWall": response.get("whoCanPostOnWall", response.get("wallAccess", "everyone")),
                "whoCanSeeMyPostReactions": response.get(
                    "whoCanSeeMyPostReactions",
                    response.get("likesVisibility", "everyone"),
                ),
            }
        )

    async def update_privacy_settings(
        self,
        *,
        show_last_seen: bool | None = None,
        who_can_post_on_wall: str | None = None,
        who_can_see_my_post_reactions: str | None = None,
    ) -> None:
        payload = drop_none(
            showLastSeen=show_last_seen,
            wallAccess=who_can_post_on_wall,
            likesVisibility=who_can_see_my_post_reactions,
        )
        await self._http.request_api("PUT", "/users/me/privacy", json=payload)

    async def get_verification_status(self) -> SDKObject | None:
        try:
            return to_model(await self._http.request_api("GET", "/verification/status"))
        except ApiError as exc:
            if exc.status_code == 404:
                return None
            raise

    async def submit_verification_request(self, video_url: str) -> SDKObject:
        return to_model(
            await self._http.request_api("POST", "/verification/submit", json={"videoUrl": video_url})
        )

    async def get_my_pins(self) -> SDKObject:
        response = await self._http.request_api("GET", "/users/me/pins")
        data = response.get("data", response)
        return to_model(
            {
                "pins": data.get("pins", []),
                "activePin": data.get("activePin"),
            }
        )

    async def set_active_pin(self, slug: str) -> None:
        await self._http.request_api("PUT", "/users/me/pin", json={"slug": slug})

    async def remove_active_pin(self) -> None:
        await self._http.request_api("DELETE", "/users/me/pin")

    async def delete_account(self) -> None:
        await self._http.request_api("DELETE", "/users/me")

    async def restore_account(self) -> None:
        await self._http.request_api("POST", "/users/me/restore")


class PostsAPI(_BaseAPI):
    async def get_feed(
        self,
        *,
        tab: str = "global",
        limit: int = 20,
        cursor: str | None = None,
    ) -> Page[SDKObject]:
        tab_value = {"global": "popular", "clan": "clan", "following": "following"}.get(tab, tab)
        params = build_query(limit=limit, tab=tab_value, cursor=cursor)
        response = await self._http.request_api("GET", "/posts", params=params)
        payload = response.get("data", response)
        posts = [to_model(normalize_post(item)) for item in payload.get("posts", [])]
        return Page(items=posts, next_cursor=extract_next_cursor(payload))

    async def get_post(self, post_id: str) -> SDKObject:
        response = await self._http.request_api("GET", f"/posts/{post_id}")
        return to_model(normalize_post(response.get("data", response)))

    async def get_user_wall(
        self,
        user_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        pinned_post_id: str | None = None,
    ) -> Page[SDKObject]:
        params = build_query(limit=limit, sort="new", cursor=cursor, pinnedPostId=pinned_post_id)
        response = await self._http.request_api("GET", f"/posts/user/{user_id}", params=params)
        payload = response.get("data", response)
        posts = [to_model(normalize_post(item)) for item in payload.get("posts", [])]
        return Page(items=posts, next_cursor=extract_next_cursor(payload))

    async def get_user_posts(
        self,
        user_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        sort: str | None = None,
        pinned_post_id: str | None = None,
    ) -> Page[SDKObject]:
        params = build_query(limit=limit, cursor=cursor, sort=sort, pinnedPostId=pinned_post_id)
        response = await self._http.request_api("GET", f"/posts/user/{user_id}", params=params)
        payload = response.get("data", response)
        posts = [to_model(normalize_post(item)) for item in payload.get("posts", [])]
        return Page(items=posts, next_cursor=extract_next_cursor(payload))

    async def get_user_liked_posts(
        self,
        user_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page[SDKObject]:
        params = build_query(limit=limit, cursor=cursor)
        response = await self._http.request_api("GET", f"/posts/user/{user_id}/liked", params=params)
        payload = response.get("data", response)
        posts = [to_model(normalize_post(item)) for item in payload.get("posts", [])]
        return Page(items=posts, next_cursor=extract_next_cursor(payload))

    async def get_posts_by_hashtag(
        self,
        hashtag: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page[SDKObject]:
        params = build_query(limit=limit, cursor=cursor)
        encoded = quote(hashtag, safe="")
        response = await self._http.request_api("GET", f"/hashtags/{encoded}/posts", params=params)
        payload = response.get("data", response)
        posts = [to_model(normalize_post(item)) for item in payload.get("posts", [])]
        return Page(items=posts, next_cursor=extract_next_cursor(payload))

    async def create_post(
        self,
        *,
        text: str,
        spans: list[dict[str, Any]] | None = None,
        wall_owner_id: str | None = None,
        attachment_ids: list[str] | None = None,
        poll: dict[str, Any] | None = None,
    ) -> SDKObject:
        payload = drop_none(
            content=text,
            spans=spans,
            wallRecipientId=wall_owner_id,
            attachmentIds=attachment_ids,
            poll=poll,
        )
        return to_model(await self._http.request_api("POST", "/posts", json=payload))

    async def create_repost(self, post_id: str, *, content: str | None = None) -> SDKObject:
        payload = drop_none(content=content)
        return to_model(await self._http.request_api("POST", f"/posts/{post_id}/repost", json=payload))

    async def edit_post(
        self,
        post_id: str,
        *,
        text: str | None = None,
        content: str | None = None,
        spans: list[dict[str, Any]] | None = None,
    ) -> None:
        payload = drop_none(content=content or text, spans=spans)
        await self._http.request_api("PUT", f"/posts/{post_id}", json=payload)

    async def delete_post(self, post_id: str) -> None:
        await self._http.request_api("DELETE", f"/posts/{post_id}")

    async def restore_post(self, post_id: str) -> None:
        await self._http.request_api("POST", f"/posts/{post_id}/restore")

    async def like(self, post_id: str) -> None:
        await self._http.request_api("POST", f"/posts/{post_id}/like")

    async def unlike(self, post_id: str) -> None:
        await self._http.request_api("DELETE", f"/posts/{post_id}/like")

    async def pin(self, post_id: str) -> None:
        await self._http.request_api("POST", f"/posts/{post_id}/pin")

    async def unpin(self, post_id: str) -> None:
        await self._http.request_api("DELETE", f"/posts/{post_id}/pin")

    async def vote_poll(self, post_id: str, option_ids: list[str]) -> SDKObject:
        response = await self._http.request_api(
            "POST",
            f"/posts/{post_id}/poll/vote",
            json={"optionIds": option_ids},
        )
        return to_model(response.get("data", response))

    async def unrepost(self, post_id: str) -> None:
        await self._http.request_api("DELETE", f"/posts/{post_id}/repost")

    async def track_view(self, post_id: str) -> None:
        await self._http.request_api("POST", f"/posts/{post_id}/view")

    async def track_views_batch(self, post_ids: list[str]) -> None:
        for post_id in post_ids:
            await self.track_view(post_id)


class CommentsAPI(_BaseAPI):
    async def get_comments(
        self,
        post_id: str,
        *,
        limit: int | None = None,
        sort: str | None = None,
        cursor: str | None = None,
    ) -> Page[SDKObject]:
        sort_map = {"new": "newest", "old": "oldest", "popular": "popular"}
        params = build_query(limit=limit, sort=sort_map.get(sort, sort), cursor=cursor)
        response = await self._http.request_api("GET", f"/posts/{post_id}/comments", params=params)

        items: list[dict[str, Any]]
        next_cursor: str | None = None
        data = response.get("data")
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "comments" in data:
            items = data.get("comments", [])
            next_cursor = data.get("nextCursor")
        else:
            items = response.get("comments", [])
        next_cursor = next_cursor or response.get("cursor") or extract_next_cursor(response)
        return Page(items=[to_model(normalize_comment(item)) for item in items], next_cursor=next_cursor)

    async def get_replies(
        self,
        comment_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page[SDKObject]:
        params = build_query(limit=limit, cursor=cursor)
        response = await self._http.request_api("GET", f"/comments/{comment_id}/replies", params=params)

        items: list[dict[str, Any]]
        next_cursor: str | None = None
        data = response.get("data")
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "replies" in data:
            items = data.get("replies", [])
            next_cursor = data.get("nextCursor")
        else:
            items = response.get("replies", [])
        next_cursor = next_cursor or response.get("cursor") or extract_next_cursor(response)
        return Page(items=[to_model(normalize_comment(item)) for item in items], next_cursor=next_cursor)

    async def create_comment(
        self,
        post_id: str,
        *,
        content: str,
        attachment_ids: list[str] | None = None,
    ) -> SDKObject:
        payload = drop_none(content=content, attachmentIds=attachment_ids)
        return to_model(await self._http.request_api("POST", f"/posts/{post_id}/comments", json=payload))

    async def create_reply(
        self,
        comment_id: str,
        *,
        content: str,
        reply_to_user_id: str | None = None,
        attachment_ids: list[str] | None = None,
    ) -> SDKObject:
        payload = drop_none(content=content, replyToUserId=reply_to_user_id, attachmentIds=attachment_ids)
        return to_model(await self._http.request_api("POST", f"/comments/{comment_id}/replies", json=payload))

    async def edit_comment(self, comment_id: str, *, content: str) -> None:
        await self._http.request_api("PATCH", f"/comments/{comment_id}", json={"content": content})

    async def delete_comment(self, comment_id: str) -> None:
        await self._http.request_api("DELETE", f"/comments/{comment_id}")

    async def like(self, comment_id: str) -> None:
        await self._http.request_api("POST", f"/comments/{comment_id}/like")

    async def unlike(self, comment_id: str) -> None:
        await self._http.request_api("DELETE", f"/comments/{comment_id}/like")


class NotificationsAPI(_BaseAPI):
    async def get_notifications(
        self,
        *,
        limit: int = 20,
        cursor: str | None = None,
        offset: int | None = None,
    ) -> Page[SDKObject]:
        effective_offset = int(cursor) if cursor is not None else offset or 0
        params = build_query(limit=limit, offset=effective_offset if effective_offset > 0 else None)
        response = await self._http.request_api("GET", "/notifications/", params=params)
        items = response.get("notifications") or response.get("data") or []
        has_more = response.get("hasMore", False)
        next_cursor = str(effective_offset + len(items)) if has_more else None
        return Page(items=[to_model(normalize_notification(item)) for item in items], next_cursor=next_cursor)

    async def get_unread_count(self) -> int:
        response = await self._http.request_api("GET", "/notifications/count")
        return int(response.get("count", 0))

    async def mark_as_read(self, ids: list[str]) -> int:
        if len(ids) == 1:
            response = await self._http.request_api("POST", f"/notifications/{ids[0]}/read")
            return int(response.get("markedCount", response.get("marked", 1)))

        marked_total = 0
        for start in range(0, len(ids), 20):
            chunk = ids[start : start + 20]
            response = await self._http.request_api("POST", "/notifications/read-batch", json={"ids": chunk})
            marked_total += int(response.get("markedCount", response.get("marked", len(chunk))))
        return marked_total

    async def mark_all_as_read(self) -> int:
        response = await self._http.request_api("POST", "/notifications/read-all")
        return int(response.get("markedCount", response.get("marked", 0)))

    async def get_settings(self) -> SDKObject:
        response = await self._http.request_api("GET", "/notifications/settings")
        return to_model(
            {
                "webEnabled": response.get("webEnabled", response.get("enabled", True)),
                "soundEnabled": response.get("soundEnabled", response.get("sound", True)),
                "preferences": response.get("preferences")
                or {
                    "follows": response.get("follows", True),
                    "reactions": response.get("reactions", response.get("likes", True)),
                    "replies": response.get("replies", response.get("comments", True)),
                    "mentions": response.get("mentions", True),
                    "wallPosts": response.get("wallPosts", True),
                },
            }
        )

    async def update_settings(
        self,
        *,
        web_enabled: bool | None = None,
        sound_enabled: bool | None = None,
        preferences: Mapping[str, bool] | None = None,
    ) -> None:
        payload = drop_none(enabled=web_enabled, sound=sound_enabled)
        if preferences:
            prefs = dict(preferences)
            if "follows" in prefs:
                payload["follows"] = prefs["follows"]
            if "reactions" in prefs:
                payload["reactions"] = prefs["reactions"]
                payload["likes"] = prefs["reactions"]
            if "replies" in prefs:
                payload["replies"] = prefs["replies"]
                payload["comments"] = prefs["replies"]
            if "mentions" in prefs:
                payload["mentions"] = prefs["mentions"]
            if "wallPosts" in prefs:
                payload["wallPosts"] = prefs["wallPosts"]
        await self._http.request_api("PUT", "/notifications/settings", json=payload)


class FilesAPI(_BaseAPI):
    async def upload_media(
        self,
        file: str | bytes | BinaryIO,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> SDKObject:
        upload_file, opened = build_upload_file(file, filename=filename, content_type=content_type)
        try:
            return to_model(await self._http.request_api("POST", "/files/upload", files={"file": upload_file}))
        finally:
            if opened is not None:
                opened.close()

    async def delete_file(self, file_id: str) -> None:
        await self._http.request_api("DELETE", f"/files/{file_id}")


class SocialAPI(_BaseAPI):
    async def get_followers(
        self,
        user_id: str,
        *,
        limit: int = 20,
        cursor: str | None = None,
        page: int | None = None,
    ) -> Page[SDKObject]:
        page_number = int(cursor) if cursor is not None else page or 1
        params = build_query(limit=limit, page=page_number)
        response = await self._http.request_api("GET", f"/users/{user_id}/followers", params=params)
        payload = response.get("data", response)
        users = payload.get("users", payload.get("followers", []))
        next_cursor = str(page_number + 1) if payload.get("pagination", {}).get("hasMore") else None
        return Page(items=[to_model(normalize_relation_user(item)) for item in users], next_cursor=next_cursor)

    async def get_following(
        self,
        user_id: str,
        *,
        limit: int = 20,
        cursor: str | None = None,
        page: int | None = None,
    ) -> Page[SDKObject]:
        page_number = int(cursor) if cursor is not None else page or 1
        params = build_query(limit=limit, page=page_number)
        response = await self._http.request_api("GET", f"/users/{user_id}/following", params=params)
        payload = response.get("data", response)
        users = payload.get("users", payload.get("following", []))
        next_cursor = str(page_number + 1) if payload.get("pagination", {}).get("hasMore") else None
        return Page(items=[to_model(normalize_relation_user(item)) for item in users], next_cursor=next_cursor)

    async def block(self, user_id: str) -> None:
        await self._http.request_api("POST", f"/users/{user_id}/block", json={})

    async def unblock(self, user_id: str) -> None:
        await self._http.request_api("DELETE", f"/users/{user_id}/block")

    async def get_blocked_users(
        self,
        *,
        limit: int = 20,
        cursor: str | None = None,
        page: int | None = None,
    ) -> Page[SDKObject]:
        page_number = int(cursor) if cursor is not None else page or 1
        params = build_query(limit=limit, page=page_number)
        response = await self._http.request_api("GET", "/users/me/blocked", params=params)
        payload = response.get("data", response)
        if isinstance(payload, list):
            users = payload
            has_more = False
        else:
            users = payload.get("users", [])
            has_more = payload.get("pagination", {}).get("hasMore", False)

        normalized = []
        for item in users:
            user = item.get("user") or item
            normalized.append(
                {
                    "id": user.get("id"),
                    "username": user.get("username"),
                    "displayName": user.get("displayName", ""),
                    "avatar": user.get("avatar"),
                    "isVerified": user.get("isVerified", user.get("verified", False)),
                    "isPrivate": user.get("isPrivate", False),
                    "isBlocked": True,
                }
            )
        next_cursor = str(page_number + 1) if has_more else None
        return Page(items=[to_model(item) for item in normalized], next_cursor=next_cursor)

    async def batch_follow_status(self, user_ids: list[str]) -> SDKObject:
        if not user_ids:
            return SDKObject()
        response = await self._http.request_api("POST", "/users/follow-status", json={"userIds": user_ids})
        return to_model(response.get("data", response))


class SearchAPI(_BaseAPI):
    async def get_trending_hashtags(self, *, limit: int = 10) -> list[SDKObject]:
        response = await self._http.request_api("GET", "/hashtags/trending", params=build_query(limit=limit))
        data = response.get("data", response)
        hashtags = data.get("hashtags", [])
        return [to_model(normalize_hashtag(item)) for item in hashtags]

    async def get_top_clans(self) -> list[SDKObject]:
        response = await self._http.request_api("GET", "/users/stats/top-clans")
        items = response.get("clans") or response.get("data") or []
        result = []
        for item in items:
            normalized = dict(item)
            normalized["count"] = normalized.get("count", normalized.get("memberCount", 0))
            result.append(to_model(normalized))
        return result

    async def search_users(self, query: str, *, limit: int = 20, cursor: str | None = None) -> Page[SDKObject]:
        params = build_query(q=query, limit=limit, cursor=cursor)
        response = await self._http.request_api("GET", "/users/search", params=params)
        users = response.get("data", {}).get("users") or response.get("users") or []
        return Page(items=[to_model(item) for item in users], next_cursor=None)

    async def global_search(
        self,
        query: str,
        *,
        user_limit: int = 5,
        hashtag_limit: int = 5,
    ) -> SDKObject:
        params = build_query(q=query, userLimit=user_limit, hashtagLimit=hashtag_limit)
        response = await self._http.request_api("GET", "/search", params=params)
        data = response.get("data", response)
        return to_model(
            {
                "users": data.get("users", []),
                "hashtags": [normalize_hashtag(item) for item in data.get("hashtags", [])],
            }
        )

    async def search_hashtags(self, query: str | None = None, *, limit: int = 10) -> list[SDKObject]:
        params = build_query(limit=limit, q=query)
        response = await self._http.request_api("GET", "/hashtags", params=params)
        data = response.get("data", response)
        hashtags = data.get("hashtags")
        if hashtags is None:
            hashtags = response.get("hashtags")
        if hashtags is None and isinstance(data, list):
            hashtags = data
        return [to_model(normalize_hashtag(item)) for item in hashtags or []]


class ReportsAPI(_BaseAPI):
    async def create_report(self, payload: Mapping[str, Any]) -> SDKObject:
        response = await self._http.request_api("POST", "/reports", json=dict(payload))
        return to_model(response.get("data", response))


class PlatformAPI(_BaseAPI):
    async def get_changelog(self) -> list[SDKObject]:
        response = await self._http.request_api("GET", "/platform/changelog")
        return [to_model(item) for item in response.get("data", response)]


class ITDClient:
    def __init__(
        self,
        *,
        origin: str = DEFAULT_ORIGIN,
        access_token: str | None = None,
        cookies: str | Mapping[str, str] | None = None,
        device_id: str | None = None,
        timeout: float = 30.0,
        headers: Mapping[str, str] | None = None,
        auto_refresh: bool = True,
    ) -> None:
        self._http = _HTTPClient(
            origin=origin,
            access_token=access_token,
            cookies=cookies,
            device_id=device_id,
            timeout=timeout,
            headers=headers,
            auto_refresh=auto_refresh,
        )
        self.raw = RawAPI(self._http)
        self.auth = AuthAPI(self._http)
        self.users = UsersAPI(self._http)
        self.account = self.users
        self.posts = PostsAPI(self._http)
        self.comments = CommentsAPI(self._http)
        self.notifications = NotificationsAPI(self._http)
        self.files = FilesAPI(self._http)
        self.social = SocialAPI(self._http)
        self.search = SearchAPI(self._http)
        self.reports = ReportsAPI(self._http)
        self.platform = PlatformAPI(self._http)

    @property
    def access_token(self) -> str | None:
        return self._http.access_token

    @property
    def device_id(self) -> str:
        return self._http.device_id

    def set_access_token(self, access_token: str | None) -> None:
        self._http.set_access_token(access_token)

    def set_cookies(self, cookies: str | Mapping[str, str]) -> None:
        self._http.set_cookies(cookies)

    async def open(self) -> ITDClient:
        await self._http.open()
        return self

    async def close(self) -> None:
        await self._http.close()

    async def __aenter__(self) -> ITDClient:
        return await self.open()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    def __enter__(self) -> ITDClient:
        raise RuntimeError("ITDClient is async-only. Use 'async with ITDClient(...) as client'.")

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        raise RuntimeError("ITDClient is async-only. Use 'async with ITDClient(...) as client'.")
