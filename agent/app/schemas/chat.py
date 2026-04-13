from pydantic import AnyHttpUrl, BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    callback_url: AnyHttpUrl


class ChatTaskResponse(BaseModel):
    task_id: str
