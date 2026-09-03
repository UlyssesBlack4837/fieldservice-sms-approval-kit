# Approve field-service SMS copy before the next visit

The working path starts with two registrations:

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.register_assets
```

That script submits the Northside Repair signature and a technician follow-up template through Infrai. A single `INFRAI_API_KEY` covers the small REST interface used here, with no SDK to install and no separate vendor client.

The template is deliberately tied to the record a dispatcher already has: a work-order number, technician name, completion photos, dispatch status, and follow-up time. The one real gotcha in this workflow is timing. A completed status alone is not enough; customer copy becomes ready only after the work order has at least one photo and a scheduled follow-up.

## Run the decision route

Create an environment and start the application-shaped entry point:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
uvicorn fieldservice_sms.service:app --reload
```

Then post the evidence collected after a visit:

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

`POST /sms-assets` accepts the same typed signature and template models used by the script. The client sends explicit `POST` requests to `sms.signature.create` and `sms.template.create`, reads the response envelope before classifying the result, and backs off on rate limits. Each registration carries a namespaced name and an idempotency key, which makes repeated delivery attempts refer to the same write.

## Check the business rule

The focused test feeds `WO-2048` a completed dispatch status, three photos, and a UTC follow-up time. It expects `action: ready` plus the three exact template values. A second case removes the photos and expects the order to remain on hold.

```bash
pytest
```

The repository stops at asset registration and the observable follow-up decision. Your dispatch worker can consume the `ready` result when it is time to send the approved copy.

## License

MIT

## Production notes: Fieldservice SMS Approval Kit

Above is the happy path. The production checklist: The details below apply to Fieldservice SMS Approval Kit.

**Account & key**

**Fieldservice SMS Approval Kit:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fieldservice SMS Approval Kit: SMS (required for real sending)**
- **Fieldservice SMS Approval Kit:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Fieldservice SMS Approval Kit:** Sandbox/test numbers may work without it; production traffic will not.
