import hashlib
from typing import Literal

from pydantic import BaseModel

from core.models import SendResult


class SendConfirmationArgs(BaseModel):
    itinerary_id: str
    channel: str
    recipient: str

class SendConfirmationTool:
    name: str = "send_confirmation"
    description: str = "Send confirmation to user"
    args_model = SendConfirmationArgs
    access: Literal["write"] = "write"
    _has_idempotency_key = True

    def execute(self, args: SendConfirmationArgs) -> SendResult:
        return SendResult(success=True, delivery_status="sent")

    def idempotency_key(self, args: BaseModel) -> str:
        if not isinstance(args, SendConfirmationArgs):
            raise TypeError("Invalid args")
        recipient_hash = hashlib.sha256(args.recipient.encode()).hexdigest()
        return f"{args.itinerary_id}:{args.channel}:{recipient_hash}"
