from pydantic import BaseModel, Field
from typing import Literal

class EmailRequest(BaseModel):
    email_text: str = Field(..., description="The raw customer email text")

class OutputResponse(BaseModel):
    intent: Literal["refund", "exchange", "store_credit", "escalate", "unknown"]
    urgency: Literal["low", "medium", "high"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    suggested_reply: str
