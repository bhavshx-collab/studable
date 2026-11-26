"""
Studable API — Messaging Service (Phase 6).

Handles all conversation and message logic:
- send_message: persist + publish
- get_message_history: paginated
- mark_messages_read: update status, publish receipt
- get_unread_count: across all conversations
- end_conversation: status=ended, notify both
- is_blocked: check if either participant has blocked the other
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from redis.asyncio import Redis
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.pubsub import publish_to_user
from app.models.block import Block
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.notification import Notification
from app.models.user import User
from app.services.presence_service import PresenceStatus, set_presence

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000


def _is_participant(conv: Conversation, user_id: str) -> bool:
    return conv.participant_a == user_id or conv.participant_b == user_id


def _peer_id(conv: Conversation, user_id: str) -> Optional[str]:
    if conv.participant_a == user_id:
        return conv.participant_b
    if conv.participant_b == user_id:
        return conv.participant_a
    return None


def is_blocked(db: Session, user_a: str, user_b: str) -> bool:
    """Return True if either user has blocked the other."""
    return db.execute(
        select(Block).where(
            or_(
                and_(Block.blocker_id == user_a, Block.blocked_id == user_b),
                and_(Block.blocker_id == user_b, Block.blocked_id == user_a),
            )
        ).limit(1)
    ).scalar_one_or_none() is not None


def get_conversation_or_none(db: Session, conversation_id: str, user_id: str) -> Optional[Conversation]:
    conv = db.get(Conversation, conversation_id)
    if conv is None or not _is_participant(conv, user_id):
        return None
    return conv


async def send_message(
    db: Session,
    redis: Redis,
    conversation_id: str,
    sender_id: str,
    content: str,
    client_message_id: Optional[str] = None,
) -> Optional[Message]:
    """
    Persist a new message and publish it to both participants.
    Supports deduplication via client_message_id idempotency key (60s TTL).
    Returns None if the conversation doesn't exist, sender isn't a participant,
    conversation is ended, or either party has blocked the other.
    """
    content = content.strip()
    if not content or len(content) > MAX_MESSAGE_LENGTH:
        return None

    # Idempotent deduplication check
    if client_message_id:
        dedup_key = f"msg:dedup:{sender_id}:{client_message_id}"
        try:
            cached_id = await redis.get(dedup_key)
            if cached_id:
                if isinstance(cached_id, bytes):
                    cached_id = cached_id.decode("utf-8")
                existing = db.get(Message, cached_id)
                if existing:
                    return existing
        except Exception:
            pass

    conv = db.get(Conversation, conversation_id)
    if conv is None or not _is_participant(conv, sender_id):
        return None
    if conv.status == "ended":
        return None

    peer_id = _peer_id(conv, sender_id)
    if peer_id and is_blocked(db, sender_id, peer_id):
        return None

    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
        status="sent",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    if client_message_id:
        try:
            await redis.set(dedup_key, msg.id, ex=60)
        except Exception:
            pass

    event = {
        "type": "message.new",
        "conversation_id": conversation_id,
        "message": {
            "id": msg.id,
            "sender_id": sender_id,
            "content": content,
            "status": msg.status,
            "created_at": msg.created_at.isoformat(),
        },
    }
    await publish_to_user(redis, sender_id, event)
    if peer_id:
        await publish_to_user(redis, peer_id, event)

    return msg


async def mark_message_delivered(
    db: Session,
    redis: Redis,
    conversation_id: str,
    message_id: str,
    recipient_id: str,
) -> bool:
    """
    Mark a message as 'delivered' when received by recipient.
    Publishes a message.delivered event to the sender.
    """
    msg = db.get(Message, message_id)
    if msg is None or msg.conversation_id != conversation_id:
        return False
    if msg.sender_id == recipient_id:
        return False
    if msg.status == "sent":
        msg.status = "delivered"
        db.commit()
        if msg.sender_id:
            await publish_to_user(redis, msg.sender_id, {
                "type": "message.delivered",
                "conversation_id": conversation_id,
                "message_id": message_id,
            })
        return True
    return False


async def mark_messages_read(
    db: Session,
    redis: Redis,
    conversation_id: str,
    reader_id: str,
) -> int:
    """
    Mark all unread messages in a conversation (sent by the peer) as 'read'.
    Publishes a message.read event to both participants.
    Returns the number of messages updated.
    """
    conv = db.get(Conversation, conversation_id)
    if conv is None or not _is_participant(conv, reader_id):
        return 0

    # Update all 'sent' or 'delivered' messages from peer
    msgs = db.execute(
        select(Message).where(
            and_(
                Message.conversation_id == conversation_id,
                Message.sender_id != reader_id,
                Message.status != "read",
            )
        )
    ).scalars().all()

    count = 0
    for m in msgs:
        m.status = "read"
        count += 1

    if count:
        db.commit()
        peer_id = _peer_id(conv, reader_id)
        event = {
            "type": "message.read",
            "conversation_id": conversation_id,
            "reader_id": reader_id,
        }
        await publish_to_user(redis, reader_id, event)
        if peer_id:
            await publish_to_user(redis, peer_id, event)

    return count


def get_message_history(
    db: Session,
    conversation_id: str,
    user_id: str,
    limit: int = 50,
    before_id: Optional[str] = None,
) -> Optional[List[Message]]:
    """
    Return up to `limit` messages in the conversation (most recent first).
    If `before_id` is given, only return messages older than that message.
    Returns None if the user is not a participant.
    """
    conv = db.get(Conversation, conversation_id)
    if conv is None or not _is_participant(conv, user_id):
        return None

    q = select(Message).where(Message.conversation_id == conversation_id)

    if before_id:
        ref = db.get(Message, before_id)
        if ref:
            q = q.where(Message.created_at < ref.created_at)

    q = q.order_by(Message.created_at.desc()).limit(min(limit, 100))
    msgs = db.execute(q).scalars().all()
    return list(reversed(msgs))  # chronological order


def get_unread_count(db: Session, user_id: str) -> int:
    """
    Count messages in all active conversations where the user is a participant
    and the message was NOT sent by them and status != 'read'.
    """
    conv_subq = select(Conversation.id).where(
        and_(
            or_(Conversation.participant_a == user_id, Conversation.participant_b == user_id),
            Conversation.status == "active",
        )
    )
    result = db.execute(
        select(func.count()).select_from(Message).where(
            and_(
                Message.conversation_id.in_(conv_subq),
                Message.sender_id != user_id,
                Message.status != "read",
            )
        )
    ).scalar_one()
    return result or 0


def list_conversations(db: Session, user_id: str) -> List[Conversation]:
    """Return all conversations (active and ended) for a user, newest first."""
    rows = db.execute(
        select(Conversation)
        .where(
            or_(Conversation.participant_a == user_id, Conversation.participant_b == user_id)
        )
        .order_by(Conversation.created_at.desc())
    ).scalars().all()
    return list(rows)


async def end_conversation(
    db: Session,
    redis: Redis,
    conversation_id: str,
    user_id: str,
) -> bool:
    """
    Mark a conversation as ended, update presence, notify both participants.
    Returns True on success, False if not found or already ended.
    """
    conv = db.get(Conversation, conversation_id)
    if conv is None or not _is_participant(conv, user_id):
        return False
    if conv.status == "ended":
        return False

    conv.status = "ended"
    conv.ended_at = datetime.now(timezone.utc)
    db.commit()

    # Move both participants from IN_CONVERSATION → ONLINE
    for pid in [conv.participant_a, conv.participant_b]:
        if pid:
            try:
                await set_presence(redis, pid, PresenceStatus.ONLINE)
            except Exception:
                pass

    event = {
        "type": "conversation.ended",
        "conversation_id": conversation_id,
        "ended_by": user_id,
    }
    for pid in [conv.participant_a, conv.participant_b]:
        if pid:
            await publish_to_user(redis, pid, event)

    return True


async def publish_typing(
    redis: Redis,
    conversation_id: str,
    sender_id: str,
    peer_id: str,
    is_typing: bool,
) -> None:
    """Publish a typing indicator to the peer only."""
    await publish_to_user(redis, peer_id, {
        "type": "typing.start" if is_typing else "typing.stop",
        "conversation_id": conversation_id,
        "user_id": sender_id,
    })
