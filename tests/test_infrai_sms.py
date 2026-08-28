import httpx

from fieldservice_sms.infrai_sms import InfraiSmsClient


def test_signature_request_uses_bearer_auth_and_idempotency_key() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["authorization"] = request.headers["Authorization"]
        seen["idempotency"] = request.headers["Idempotency-Key"]
        return httpx.Response(200, json={"ok": True, "data": {"id": "sig_123"}})

    with InfraiSmsClient(
        "test-key", transport=httpx.MockTransport(handler)
    ) as client:
        result = client.create_signature(
            {"name": "Northside Repair"}, idempotency_key="northside:signature"
        )

    assert result == {"id": "sig_123"}
    assert seen == {
        "method": "POST",
        "authorization": "Bearer test-key",
        "idempotency": "northside:signature",
    }

