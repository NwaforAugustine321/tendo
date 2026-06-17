from typing import Literal

from pydantic import BaseModel, Field


class Option(BaseModel):
    id: str
    label: str
    description: str | None = None
    recommended: bool = False


class ConversationOutput(BaseModel):
    mode: Literal["conversation"] = "conversation"
    text: str = Field(max_length=2000)


class OptionsOutput(BaseModel):
    mode: Literal["structured_options"] = "structured_options"
    option_type: Literal["question", "confirmation", "classification", "missing_info"]
    prompt: str
    options: list[Option] = Field(min_length=2, max_length=10)
    allows_freeform: bool = True
