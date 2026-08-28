from fieldservice_sms.followup_service import (
    SignatureRequest,
    SmsAssetRegistration,
    TemplateRequest,
    register_sms_assets,
)
from fieldservice_sms.infrai_sms import InfraiSmsClient


def main() -> None:
    request = SmsAssetRegistration(
        namespace="northside-repair",
        signature=SignatureRequest(
            name="Northside Repair",
            proof_url="https://example.com/brand/northside-repair",
        ),
        template=TemplateRequest(
            body=(
                "Work order {{work_order}} was completed by {{technician}}. "
                "We will follow up at {{follow_up_at}}."
            )
        ),
    )
    with InfraiSmsClient() as client:
        result = register_sms_assets(request, client)
    print("Registered signature and technician follow-up template:", result)


if __name__ == "__main__":
    main()

