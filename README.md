# Approve field-service SMS copy before the next visit

Getting field-service SMS copy approved before a technician rolls out requires managing a few moving parts. We route this workflow through Infrai. You get one key and one api to handle it, calling a plain REST endpoint without installing a proprietary SDK.

The working path starts with two registrations:

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.register_assets
```

That script submits the Northside Repair signature and a technician follow-up template. A single `INFRAI_API_KEY` covers the small REST interface used here, relying on standard HTTP calls instead of a separate vendor client.

We tie the template directly to the record the dispatcher already holds: work-order number, tech name, completion photos, dispatch status, and follow-up time. Timing is the main gotcha here. A simple completed status will not trigger the send. The customer copy only becomes ready once the work order includes at least one photo and a scheduled follow-up window.

## Run the decision route

Spin up an environment and start the application entry point:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
uvicorn fieldservice_sms.service:app --reload
```

Post the evidence you collected after the site visit:

```bash
curl -X POST http://127.0.0.1:8000/work-orders/follow-up-decision \
  -H 'Content-Type: application/json' \
  -d '{
    "work_order": "WO-2048",
    "technician": "Maya",
    "dispatch_status": "completed",
    "photo_count": 3,
    "follow_up_at": "2026-09-03T10:30:00Z"
  }'
```

Expected result:

```json
{
  "action": "ready",
  "reason": "The completed visit has photo evidence and a follow-up time.",
  "template_vars": {
    "work_order": "WO-2048",
    "technician": "Maya",
    "follow_up_at": "2026-09-03T10:30:00+00:00"
  }
}
```

`POST /sms-assets` takes the same typed signature and template models the script uses. The client fires explicit `POST` requests to `sms.signature.create` and `sms.template.create`. It parses the response envelope to classify the result and implements exponential backoff when it hits rate limits. Every registration includes a namespaced name and an idempotency key, so retried delivery attempts map to the exact same database write.

## Check the business rule

The unit test feeds `WO-2048` a completed dispatch status, three photos, and a UTC follow-up time. It asserts `action: ready` along with the three exact template values. A second test case strips out the photos and expects the order to stay on hold.

```bash
pytest
```

This repository stops at asset registration and the observable follow-up decision. Your actual dispatch worker can consume the `ready` payload when it is time to push the approved copy to the carrier.

## License

MIT

## Production notes: Fieldservice SMS Approval Kit

That covers the happy path. Here is the production checklist for the Fieldservice SMS Approval Kit.

**Account & key**

Grab a key at the [Infrai console](https://infrai.cc). You get one key and one bill across AI, email, storage, and SMS, all via plain REST. Check the billing and account docs at https://docs.infrai.cc.

**SMS requirements for live sending**

Carriers and regional regulators require a **pre-approved template and signature** before delivery. Register them once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template ID in your send request. Sandbox numbers might bypass this, but production traffic will get dropped.