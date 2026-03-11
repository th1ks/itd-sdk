from __future__ import annotations

from typing import Any


def extract_next_cursor(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    pagination = payload.get("pagination")
    if isinstance(pagination, dict) and pagination.get("nextCursor") is not None:
        return str(pagination["nextCursor"])
    if payload.get("cursor") is not None:
        return str(payload["cursor"])
    meta = payload.get("meta")
    if isinstance(meta, dict):
        cursor = meta.get("cursor")
        if isinstance(cursor, dict) and cursor.get("next") is not None:
            return str(cursor["next"])
    return None


def normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    data = dict(profile)
    if "verified" in data and "isVerified" not in data:
        data["isVerified"] = data["verified"]
    data.setdefault("isVerified", False)
    if data.get("isPrivate") is None:
        data["isPrivate"] = False

    if isinstance(data.get("banner"), str):
        data["banner"] = {"url": data["banner"]}

    if "stats" not in data and ("followersCount" in data or "followingCount" in data):
        data["stats"] = {
            "followers": data.get("followersCount", 0),
            "following": data.get("followingCount", 0),
        }

    if "interaction" not in data and any(
        key in data
        for key in (
            "isFollowing",
            "isFollowedBy",
            "hasOutgoingRequest",
            "hasIncomingRequest",
            "isBlockedByMe",
            "isBlocking",
            "isBlockedBy",
        )
    ):
        data["interaction"] = {
            "isFollowing": data.get("isFollowing", False),
            "isFollowedBy": data.get("isFollowedBy", False),
            "hasOutgoingRequest": data.get("hasOutgoingRequest", False),
            "hasIncomingRequest": data.get("hasIncomingRequest", False),
            "isBlocking": data.get("isBlocking", data.get("isBlockedByMe", False)),
            "isBlockedBy": data.get("isBlockedBy", False),
        }

    if "privacySettings" not in data and ("wallAccess" in data or "likesVisibility" in data):
        data["privacySettings"] = {
            "whoCanPostOnWall": data.get("wallAccess", "everyone"),
            "whoCanSeeMyPostReactions": data.get("likesVisibility", "everyone"),
        }

    return data


def normalize_post_author(author: dict[str, Any] | None) -> dict[str, Any]:
    author = dict(author or {})
    return {
        "id": author.get("id"),
        "username": author.get("username"),
        "displayName": author.get("displayName"),
        "avatar": author.get("avatar"),
        "isVerified": author.get("isVerified", author.get("verified", False)),
        "pin": author.get("pin"),
    }


def normalize_comment_author(author: dict[str, Any] | None) -> dict[str, Any]:
    author = dict(author or {})
    return {
        "id": author.get("id"),
        "username": author.get("username"),
        "displayName": author.get("displayName"),
        "avatar": author.get("avatar"),
        "isVerified": author.get("isVerified", author.get("verified", False)),
        "pin": author.get("pin"),
    }


def normalize_post(raw_post: dict[str, Any]) -> dict[str, Any]:
    attachments: list[dict[str, Any]] = []
    for attachment in raw_post.get("attachments") or []:
        item = dict(attachment)
        if item.get("type") == "poll":
            options = []
            for option in item.get("options") or []:
                options.append(
                    {
                        "id": option.get("id"),
                        "text": option.get("text"),
                        "votes": option.get("votesCount", option.get("voteCount", option.get("votes", 0))),
                    }
                )
            item["options"] = options
            item["totalVotes"] = item.get("totalVotes", 0)
            item["multipleChoice"] = item.get("multipleChoice", False)
            voted_option_ids = item.get("votedOptionIds") or []
            viewer_status = raw_post.get("viewerStatus") or {}
            poll_vote = viewer_status.get("pollVote")
            item["myVotes"] = voted_option_ids or ([poll_vote] if poll_vote else [])
            item["myVote"] = voted_option_ids[0] if voted_option_ids else poll_vote
        attachments.append(item)

    embedded_poll = raw_post.get("poll")
    if embedded_poll and not any(item.get("type") == "poll" for item in attachments):
        attachments.append(
            {
                "id": embedded_poll.get("id"),
                "type": "poll",
                "question": embedded_poll.get("question"),
                "multipleChoice": embedded_poll.get("multipleChoice", False),
                "options": [
                    {
                        "id": option.get("id"),
                        "text": option.get("text"),
                        "votes": option.get("votesCount", option.get("voteCount", 0)),
                    }
                    for option in embedded_poll.get("options") or []
                ],
                "totalVotes": embedded_poll.get("totalVotes", 0),
                "myVotes": embedded_poll.get("votedOptionIds") or [],
                "myVote": (embedded_poll.get("votedOptionIds") or [None])[0],
            }
        )

    stats = raw_post.get("stats") or {}
    viewer_status = raw_post.get("viewerStatus") or {}
    return {
        "id": raw_post.get("id"),
        "author": normalize_post_author(raw_post.get("author")),
        "wallOwnerId": raw_post.get("wallOwnerId", raw_post.get("authorId", (raw_post.get("author") or {}).get("id"))),
        "text": raw_post.get("text", raw_post.get("content", "")),
        "spans": raw_post.get("spans") or [],
        "attachments": attachments,
        "reactions": {
            "total": stats.get("reactions", raw_post.get("likesCount", 0)),
            "myReaction": viewer_status.get("reaction", "like" if raw_post.get("isLiked") else None),
        },
        "stats": {
            "views": stats.get("views", raw_post.get("viewsCount", 0)),
            "comments": stats.get("comments", raw_post.get("commentsCount", 0)),
            "reposts": stats.get("reposts", raw_post.get("repostsCount", 0)),
        },
        "originalPost": normalize_post(raw_post["originalPost"]) if raw_post.get("originalPost") else None,
        "dominantEmoji": raw_post.get("dominantEmoji"),
        "createdAt": raw_post.get("createdAt"),
        "editedAt": raw_post.get("editedAt"),
    }


def normalize_comment(raw_comment: dict[str, Any]) -> dict[str, Any]:
    stats = raw_comment.get("stats") or {}
    viewer_status = raw_comment.get("viewerStatus") or {}
    preview_source = raw_comment.get("previewReplies") or raw_comment.get("replies") or []
    return {
        "id": raw_comment.get("id"),
        "postId": raw_comment.get("postId"),
        "author": normalize_comment_author(raw_comment.get("author")),
        "parentId": raw_comment.get("parentId"),
        "rootId": raw_comment.get("rootId"),
        "text": raw_comment.get("text", raw_comment.get("content", "")),
        "spans": raw_comment.get("spans") or [],
        "attachments": raw_comment.get("attachments") or [],
        "reactions": {
            "total": stats.get("reactions", raw_comment.get("likesCount", 0)),
            "myReaction": viewer_status.get("reaction", "like" if raw_comment.get("isLiked") else None),
        },
        "stats": {
            "replies": stats.get("replies", raw_comment.get("repliesCount", 0)),
        },
        "replyTo": raw_comment.get("replyTo"),
        "previewReplies": [normalize_comment(item) for item in preview_source] if preview_source else None,
        "createdAt": raw_comment.get("createdAt"),
        "editedAt": raw_comment.get("editedAt"),
    }


def normalize_notification(raw_notification: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "like": "post_reaction",
        "comment": "post_comment",
        "reply": "comment_reply",
        "repost": "post_repost",
        "mention": "post_mention",
        "follow": "follow",
        "follow_request": "follow_request",
        "follow_accepted": "follow_accepted",
        "post_reaction": "post_reaction",
        "post_comment": "post_comment",
        "post_repost": "post_repost",
        "comment_reaction": "comment_reaction",
        "comment_reply": "comment_reply",
        "post_mention": "post_mention",
        "comment_mention": "comment_mention",
        "wall_post": "wall_post",
    }
    payload = raw_notification.get("payload") or {}
    actors = payload.get("actors")
    if actors is None and raw_notification.get("actor"):
        actor = raw_notification["actor"]
        actors = [
            {
                "id": actor.get("id"),
                "username": actor.get("username"),
                "displayName": actor.get("displayName"),
                "avatar": actor.get("avatar"),
                "isFollowing": actor.get("isFollowing"),
                "isFollowedBy": actor.get("isFollowedBy"),
            }
        ]

    return {
        "id": raw_notification.get("id"),
        "type": mapping.get(raw_notification.get("type"), "follow"),
        "entityId": raw_notification.get("entityId", raw_notification.get("targetId")),
        "parentEntityId": raw_notification.get("parentEntityId"),
        "isRead": raw_notification.get("isRead", raw_notification.get("read", False)),
        "payload": {
            "actors": actors or [],
            "count": payload.get("count", 1),
            "clickUrl": payload.get("clickUrl"),
            "entityPreview": payload.get("entityPreview", raw_notification.get("preview")),
        },
        "createdAt": raw_notification.get("createdAt"),
        "updatedAt": raw_notification.get("updatedAt", raw_notification.get("readAt", raw_notification.get("createdAt"))),
    }


def normalize_relation_user(raw_user: dict[str, Any]) -> dict[str, Any]:
    user = raw_user.get("user") or raw_user
    return {
        "id": raw_user.get("id"),
        "userId": user.get("id", raw_user.get("id")),
        "displayName": user.get("displayName", ""),
        "username": user.get("username"),
        "avatar": user.get("avatar", ""),
        "isVerified": user.get("isVerified", user.get("verified", False)),
        "isPrivate": user.get("isPrivate", False),
        "interaction": raw_user.get("interaction")
        or {
            "isFollowing": raw_user.get("isFollowing", False),
            "isFollowedBy": raw_user.get("isFollowedBy", False),
            "hasOutgoingRequest": raw_user.get("hasOutgoingRequest", False),
            "hasIncomingRequest": raw_user.get("hasIncomingRequest", False),
            "isBlocking": raw_user.get("isBlocking", False),
            "isBlockedBy": raw_user.get("isBlockedBy", False),
        },
    }


def normalize_hashtag(raw_hashtag: dict[str, Any]) -> dict[str, Any]:
    data = dict(raw_hashtag)
    data["count"] = data.get("count", data.get("postsCount", 0))
    return data
