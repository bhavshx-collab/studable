"""
Studable API — Messaging REST endpoints (Phase 6).

Endpoints:
  GET  /api/v1/conversations                      – list conversations
  GET  /api/v1/conversations/unread-count         – total unread
  GET  /api/v1/conversations/{id}                 – conversation details
  GET  /api/v1/conversations/{id}/messages        – paginated history
  POST /api/v1/conversations/{id}/messages        – send message (REST fallback)
  POST /api/v1/conversations/{id}/read            – mark all messages read
  POST /api/v1/conversations/{id}/typing          – typing indicator
  DELETE /api/v1/conversations/{id}               – end conversation
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.redis import get_redis
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services.messaging_service import (
    end_conversation,
    get_conversation_or_none,
    get_message_history,
    get_unread_count,
    list_conversations,
    mark_message_delivered,
    mark_messages_read,
    publish_typing,
    send_message,
)

router = APIRouter(prefix="/conversations", tags=["Messaging"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: str
    conversation_id: str
    sender_id: Optional[str]
    content: str
    status: str
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, m: Message) -> "MessageOut":
        return cls(
            id=m.id,
            conversation_id=m.conversation_id,
            sender_id=m.sender_id,
            content=m.content,
            status=m.status,
            created_at=m.created_at.isoformat(),
        )


class ConversationOut(BaseModel):
    id: str
    participant_a: Optional[str]
    participant_b: Optional[str]
    topic: Optional[str]
    matching_mode: Optional[str]
    status: str
    created_at: str
    ended_at: Optional[str]

    @classmethod
    def from_orm_obj(cls, c: Conversation) -> "ConversationOut":
        return cls(
            id=c.id,
            participant_a=c.participant_a,
            participant_b=c.participant_b,
            topic=c.topic,
            matching_mode=c.matching_mode,
            status=c.status,
            created_at=c.created_at.isoformat(),
            ended_at=c.ended_at.isoformat() if c.ended_at else None,
        )


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    client_message_id: Optional[str] = None


class TypingRequest(BaseModel):
    is_typing: bool


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("", summary="List my conversations")
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ConversationOut]:
    convs = list_conversations(db, current_user.id)
    return [ConversationOut.from_orm_obj(c) for c in convs]


@router.get("/unread-count", summary="Total unread message count")
def unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"unread_count": get_unread_count(db, current_user.id)}


@router.get("/{conversation_id}", summary="Get conversation details")
def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationOut:
    conv = get_conversation_or_none(db, conversation_id, current_user.id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return ConversationOut.from_orm_obj(conv)


@router.get("/{conversation_id}/messages", summary="Paginated message history")
def get_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[str] = Query(None, description="Message ID to paginate before"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MessageOut]:
    msgs = get_message_history(db, conversation_id, current_user.id, limit=limit, before_id=before)
    if msgs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return [MessageOut.from_orm_obj(m) for m in msgs]


@router.post("/{conversation_id}/messages", status_code=status.HTTP_201_CREATED, summary="Send a message (REST)")
async def send_message_rest(
    conversation_id: str,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageOut:
    msg = await send_message(
        db,
        redis,
        conversation_id,
        current_user.id,
        body.content,
        client_message_id=body.client_message_id,
    )
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot send message: conversation not found, ended, or blocked",
        )
    return MessageOut.from_orm_obj(msg)


@router.post("/{conversation_id}/messages/{message_id}/delivered", summary="Acknowledge message delivery")
async def message_delivered(
    conversation_id: str,
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    ok = await mark_message_delivered(db, redis, conversation_id, message_id, current_user.id)
    return {"delivered": ok}


@router.post("/{conversation_id}/read", summary="Mark all messages as read")
async def read_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    conv = get_conversation_or_none(db, conversation_id, current_user.id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    count = await mark_messages_read(db, redis, conversation_id, current_user.id)
    return {"marked_read": count}


@router.post("/{conversation_id}/typing", summary="Send typing indicator")
async def typing_indicator(
    conversation_id: str,
    body: TypingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    conv = get_conversation_or_none(db, conversation_id, current_user.id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conv.status == "ended":
        return {"ok": False}
    peer_id = (
        conv.participant_b if conv.participant_a == current_user.id else conv.participant_a
    )
    if peer_id:
        await publish_typing(redis, conversation_id, current_user.id, peer_id, body.is_typing)
    return {"ok": True}


@router.delete("/{conversation_id}", summary="End a conversation")
async def leave_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    ok = await end_conversation(db, redis, conversation_id, current_user.id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or already ended",
        )
    return {"ended": True}
