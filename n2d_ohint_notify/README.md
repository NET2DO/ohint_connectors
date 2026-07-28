# n2d_ohint_notify — Back-office → App notifications (SPEC-037 FR-4b)

When a back-office change is made in Odoo to an employee's records, this addon
POSTs an HMAC-signed event to the OHINT middleware (`/webhooks/odoo/notify`),
which resolves the `hr.employee` → app user and delivers a push + in-app
notification.

## What triggers a notification

| Model | When | Category / msg_key |
|-------|------|--------------------|
| `hr.leave` | state → approved (`validate`) / refused (`refuse`) | `hr_leave` / `hr_leave.approved`, `hr_leave.refused` |
| `hr.employee` | assignment change (`department_id`, `job_id`, `parent_id`, `work_location_id`) | `back_office` / `back_office.assignment_changed` |
| `hr.employee` | profile change (`job_title`, `work_email`, `mobile_phone`, `work_phone`) | `back_office` / `back_office.profile_updated` |
| `hr.attendance` | `check_in`/`check_out` edited *(guarded — see below)* | `back_office` / `back_office.attendance_edited` |

The POST fires **after the transaction commits** (`cr.postcommit`), so a
rolled-back change never notifies and the user's action is never blocked. A
webhook failure is logged and swallowed — it never surfaces to the Odoo user.

## Configuration (`Settings → Technical → System Parameters`)

| Key | Required | Value |
|-----|----------|-------|
| `ohint.webhook_url` | yes | e.g. `https://api.ohint.net/api/v1/webhooks/odoo/notify` (dev: the middleware host) |
| `ohint.webhook_secret` | yes | same value as the middleware env `ODOO_WEBHOOK_SECRET` |
| `ohint.tenant_id` | yes | the middleware tenant UUID this Odoo instance belongs to |
| `ohint.integration_uid` | optional | the Odoo user id the middleware logs in as |

If `ohint.webhook_url`/`ohint.webhook_secret`/`ohint.tenant_id` are unset, the
addon silently no-ops (notifications disabled).

### `ohint.integration_uid`

The app's own check-in/out writes `hr.attendance.check_in/out` through the
middleware's Odoo user. To avoid sending an "attendance corrected" notification
for the employee's *own* app action, attendance notifications only fire when
`ohint.integration_uid` is set **and** the writing user is **not** that uid.
Leave it unset to disable attendance notifications entirely (leave + employee
events are unaffected). Find the uid under `Settings → Users` (Developer mode
shows the id in the URL) for the integration account.

## Payload contract

```json
{
  "tenant_id": "<uuid>",
  "odoo_employee_id": "<hr.employee id>",
  "category": "hr_leave | back_office",
  "msg_key": "hr_leave.approved | back_office.assignment_changed | ...",
  "args": {"type": "Paid Time Off"},
  "data": {"route": "/notifications/leave/42"},
  "dedupe_key": "hr_leave:42:validate"
}
```

Signed exactly like the SPEC-017 sale-order webhook: `X-OHINT-Signature:
sha256=HMAC_SHA256(raw_body, secret)` + `X-OHINT-Timestamp: <unix>` (rejected if
>5 min old). `msg_key` values must match the templates in the middleware
(`backend/internal/notification/model.go`).
