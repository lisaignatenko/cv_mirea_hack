from pydantic import BaseModel, Field


class RequestPayload(BaseModel):
    id: int = Field(ge=0, description="id of requested video in chronological order")
