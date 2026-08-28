from datetime import datetime, timezone

from fieldservice_sms.followup_service import (
    DispatchStatus,
    SignatureRequest,
    SmsAssetRegistration,
    TemplateRequest,
    WorkOrderUpdate,
    decide_follow_up,
    register_sms_assets,
)


def test_completed_order_with_photo_is_ready_for_follow_up() -> None:
    update = WorkOrderUpdate(
        work_order="WO-2048",
        technician="Maya",
        dispatch_status=DispatchStatus.COMPLETED,
        photo_count=3,
        follow_up_at=datetime(2026, 9, 3, 10, 30, tzinfo=timezone.utc),
    )

    decision = decide_follow_up(update)

    assert decision.action == "ready"
    assert decision.template_vars == {
        "work_order": "WO-2048",
        "technician": "Maya",
        "follow_up_at": "2026-09-03T10:30:00+00:00",
    }


def test_completed_order_without_photo_stays_on_hold() -> None:
    update = WorkOrderUpdate(
        work_order="WO-2049",
        technician="Maya",
        dispatch_status=DispatchStatus.COMPLETED,
        photo_count=0,
        follow_up_at=datetime(2026, 9, 3, 10, 30, tzinfo=timezone.utc),
    )

    decision = decide_follow_up(update)

    assert decision.action == "hold"
    assert decision.template_vars is None


def test_asset_registration_uses_supported_template_variables_field() -> None:
    class Client:
        def create_signature(self, payload, *, idempotency_key):
            return {"id": "sig_123"}

        def create_template(self, payload, *, idempotency_key):
            assert payload["variables"] == [
                "work_order",
                "technician",
                "follow_up_at",
            ]
            assert "template_vars" not in payload
            return {"id": "tpl_123"}

    request = SmsAssetRegistration(
        namespace="northside-repair",
        signature=SignatureRequest(
            name="Northside Repair",
            proof_url="https://example.com/brand/northside-repair",
        ),
        template=TemplateRequest(body="Completed by {{technician}}."),
    )

    result = register_sms_assets(request, Client())

    assert result == {
        "signature": {"id": "sig_123"},
        "template": {"id": "tpl_123"},
    }
