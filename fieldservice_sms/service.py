from fastapi import FastAPI, HTTPException

from .followup_service import (
    SmsAssetRegistration,
    WorkOrderUpdate,
    decide_follow_up,
    register_sms_assets,
)
from .infrai_sms import InfraiError, InfraiSmsClient

app = FastAPI(title="Field-service SMS approvals")


@app.post("/sms-assets", status_code=201)
def create_sms_assets(request: SmsAssetRegistration) -> dict[str, object]:
    try:
        with InfraiSmsClient() as client:
            return register_sms_assets(request, client)
    except InfraiError as error:
        status_code = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": str(error)},
        ) from error


@app.post("/work-orders/follow-up-decision")
def follow_up_decision(update: WorkOrderUpdate) -> dict[str, object]:
    return decide_follow_up(update).model_dump()

