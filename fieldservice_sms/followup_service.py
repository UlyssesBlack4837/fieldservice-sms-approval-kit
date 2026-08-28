from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .infrai_sms import InfraiSmsClient


class DispatchStatus(str, Enum):
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    ON_SITE = "on_site"
    COMPLETED = "completed"


class SignatureRequest(BaseModel):
    name: str = Field(min_length=2, max_length=32)
    type: str = "company"
    proof_url: str
    remark: str = "Field-service appointment messages"


class TemplateRequest(BaseModel):
    body: str = Field(min_length=10, max_length=500)
    locale: str = "en-US"
    variables: list[str] = Field(
        default_factory=lambda: ["work_order", "technician", "follow_up_at"]
    )


class SmsAssetRegistration(BaseModel):
    namespace: str = Field(pattern=r"^[a-z0-9-]{3,24}$")
    signature: SignatureRequest
    template: TemplateRequest


class WorkOrderUpdate(BaseModel):
    work_order: str = Field(min_length=1)
    technician: str = Field(min_length=1)
    dispatch_status: DispatchStatus
    photo_count: int = Field(ge=0)
    follow_up_at: datetime | None = None


class FollowUpDecision(BaseModel):
    action: str
    reason: str
    template_vars: dict[str, str] | None = None


def register_sms_assets(
    request: SmsAssetRegistration, client: InfraiSmsClient
) -> dict[str, Any]:
    signature = client.create_signature(
        request.signature.model_dump(),
        idempotency_key=f"{request.namespace}:signature",
    )
    template_payload = request.template.model_dump()
    template_payload["name"] = f"{request.namespace}-technician-follow-up"
    template = client.create_template(
        template_payload,
        idempotency_key=f"{request.namespace}:template",
    )
    return {"signature": signature, "template": template}


def decide_follow_up(update: WorkOrderUpdate) -> FollowUpDecision:
    if update.dispatch_status is not DispatchStatus.COMPLETED:
        return FollowUpDecision(
            action="hold", reason="The technician has not completed the visit."
        )
    if update.photo_count < 1:
        return FollowUpDecision(
            action="hold", reason="A completion photo is required before follow-up."
        )
    if update.follow_up_at is None:
        return FollowUpDecision(
            action="hold", reason="The customer follow-up time is not scheduled."
        )

    follow_up_at = update.follow_up_at
    if follow_up_at.tzinfo is None:
        follow_up_at = follow_up_at.replace(tzinfo=timezone.utc)
    return FollowUpDecision(
        action="ready",
        reason="The completed visit has photo evidence and a follow-up time.",
        template_vars={
            "work_order": update.work_order,
            "technician": update.technician,
            "follow_up_at": follow_up_at.isoformat(),
        },
    )
