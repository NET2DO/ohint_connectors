"""Refuse a new point of sale the OHINT subscription has no room for.

A pos.config IS a branch as far as the middleware is concerned: each one maps to
a branch a till enrolls against, and the subscription says how many an account
may run. Without this check a customer can add tills in Odoo all day; the
middleware simply declines to mirror the extra ones, and the first anyone
notices is a till that can never be enrolled.

The check is deliberately FAIL-OPEN. If the middleware cannot be reached, or is
not configured on this database, the create proceeds: an unreachable middleware
must not stop a customer configuring their own ERP, and little is lost by
allowing it — an unmirrored pos.config gets no branch, no enrollment code and
therefore no working till, so the limit still holds where it decides anything.

Configuration (ir.config_parameter), all three required or the check no-ops:
    ohint.middleware_url    e.g. https://api.ohint.net/api/v1
    ohint.webhook_secret    the shared ODOO_WEBHOOK_SECRET
    ohint.tenant_id         this database's tenant uuid in the middleware
"""

import hashlib
import hmac
import json
import logging
import time

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Short: this runs in front of a user pressing Save.
_ALLOWANCE_TIMEOUT = 6

# The middleware's own POS bot creates pos.configs when an operator adds a
# branch from the console. That create must never be refused — the branch row
# it belongs to has already been counted against the cap, so asking again would
# see its own reservation and lock the middleware out of provisioning.
_MIDDLEWARE_BOT_LOGIN = "ohint_pos_bot"


class PosConfig(models.Model):
    _inherit = "pos.config"

    @api.model_create_multi
    def create(self, vals_list):
        self._ohint_check_branch_allowance()
        return super().create(vals_list)

    @api.model
    def _ohint_is_middleware_user(self):
        if self.env.user.login == _MIDDLEWARE_BOT_LOGIN:
            return True
        integration_uid = (
            self.env["ir.config_parameter"].sudo().get_param("ohint.integration_uid")
        )
        return bool(integration_uid) and str(self.env.uid) == str(integration_uid)

    @api.model
    def _ohint_allowance_config(self):
        """(url, secret, tenant_id), or None when the middleware isn't
        configured on this database."""
        icp = self.env["ir.config_parameter"].sudo()
        base = icp.get_param("ohint.middleware_url")
        secret = icp.get_param("ohint.webhook_secret")
        tenant_id = icp.get_param("ohint.tenant_id")
        if not (base and secret and tenant_id):
            return None
        return (
            "%s/webhooks/odoo/pos/allowance" % base.rstrip("/"),
            secret,
            tenant_id,
        )

    @api.model
    def _ohint_check_branch_allowance(self):
        if self._ohint_is_middleware_user():
            return
        config = self._ohint_allowance_config()
        if not config:
            return
        url, secret, tenant_id = config

        # Count what the middleware cannot see for itself: the tills this
        # database already has. Archived configs are excluded by the default
        # active domain — they sell nothing.
        current = self.env["pos.config"].sudo().search_count([])

        body = json.dumps(
            {"tenant_id": tenant_id, "current_configs": current},
            separators=(",", ":"),
        )
        signature = hmac.new(
            secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        try:
            response = requests.post(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-OHINT-Timestamp": str(int(time.time())),
                    "X-OHINT-Signature": "sha256=%s" % signature,
                },
                timeout=_ALLOWANCE_TIMEOUT,
            )
            response.raise_for_status()
            answer = response.json()
        except Exception as exc:  # noqa: BLE001 — see the fail-open note above
            _logger.warning("OHINT branch allowance check failed, allowing: %s", exc)
            return

        if answer.get("may_create"):
            return

        allowed = answer.get("allowed_branches")
        if allowed is None:
            raise UserError(
                _(
                    "Point of Sale is not enabled for this account in OHINT.\n\n"
                    "Ask your OHINT operator to set a branch limit before adding a "
                    "point of sale."
                )
            )
        used = max(current, answer.get("branches_in_use") or 0)
        raise UserError(
            _(
                "Your OHINT subscription allows %(allowed)s point(s) of sale and "
                "%(used)s already exist.\n\n"
                "Ask your OHINT operator to raise the branch limit, or archive a "
                "point of sale you no longer use."
            )
            % {"allowed": allowed, "used": used}
        )
