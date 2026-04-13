from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field

from app.schemas.language import Language


class CreateChatSessionResponse(BaseModel):
    conversation_id: UUID
    session_id: UUID


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    callback_url: AnyHttpUrl
    language: Language | None = None


class ChatTaskResponse(BaseModel):
    task_id: str
