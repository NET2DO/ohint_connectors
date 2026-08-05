import hashlib
import hmac
import json
import logging
import time

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)

# Keep the outbound POST short — it runs post-commit; a slow middleware must not
# hold an Odoo worker.
_WEBHOOK_TIMEOUT = 10


class OhintNotify(models.AbstractModel):
    """SPEC-037 FR-4b dispatcher.

    Builds an HMAC-signed notification and POSTs it to the OHINT middleware
    ``/webhooks/odoo/notify`` endpoint. The POST fires AFTER the current
    transaction commits (via ``cr.postcommit``) so a rolled-back change never
    notifies and the user's action is never blocked. Silently no-ops when the
    webhook isn't configured.
    """

    _name = "ohint.notify"
    _description = "OHINT middleware notification dispatcher"

    @api.model
    def _config(self):
        icp = self.env["ir.config_parameter"].sudo()
        return (
            icp.get_param("ohint.webhook_url"),
            icp.get_param("ohint.webhook_secret"),
            icp.get_param("ohint.tenant_id"),
        )

    @api.model
    def integration_uid(self):
        """The Odoo user id the middleware authenticates as (optional). Writes by
        this user are treated as app-originated, not back-office edits."""
        return self.env["ir.config_parameter"].sudo().get_param("ohint.integration_uid")

    @api.model
    def _dispatch(self, employee, category, msg_key, args=None, data=None, dedupe_key=None):
        if not employee:
            return
        url, secret, tenant_id = self._config()
        if not (url and secret and tenant_id):
            return  # not configured -> notifications disabled

        body = {
            "tenant_id": tenant_id,
            "odoo_employee_id": str(employee.id),
            "category": category,
            "msg_key": msg_key,
            "args": args or {},
            "data": data or {},
            "dedupe_key": dedupe_key or "",
        }
        # Only plain values are captured — safe to run after the cursor closes.
        self.env.cr.postcommit.add(lambda: self._post(url, secret, body))

    @api.model
    def _dispatch_event(self, body):
        """POST a top-level ``event`` envelope (e.g. ``payment.received``) to the
        middleware webhook. Unlike ``_dispatch`` these events aren't addressed to
        a single hr.employee — the middleware routes them itself (by assigned
        customer, etc.). Injects tenant_id, signs, and fires post-commit, so a
        rolled-back change never notifies and the user's action is never blocked.
        Silently no-ops when the webhook isn't configured. ``body`` must contain
        only plain JSON values (it is captured for a post-commit callback)."""
        url, secret, tenant_id = self._config()
        if not (url and secret and tenant_id):
            return  # not configured -> notifications disabled
        payload = dict(body, tenant_id=tenant_id)
        self.env.cr.postcommit.add(lambda: self._post(url, secret, payload))

    @staticmethod
    def _post(url, secret, body):
        try:
            payload = json.dumps(body, separators=(",", ":"))
            timestamp = str(int(time.time()))
            # Sign the raw body only — the timestamp is a separate replay-guard
            # header, matching the SPEC-017 sale-order-confirmed webhook.
            signature = hmac.new(
                secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
            ).hexdigest()
            requests.post(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-OHINT-Timestamp": timestamp,
                    "X-OHINT-Signature": "sha256=%s" % signature,
                },
                timeout=_WEBHOOK_TIMEOUT,
            )
        except Exception as exc:  # noqa: BLE001 — a notify failure must never surface
            _logger.warning("ohint notify POST failed: %s", exc)
