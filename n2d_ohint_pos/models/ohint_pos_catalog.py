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


class OhintPosCatalog(models.AbstractModel):
    """SPEC-041 §Webhook extension dispatcher.

    Accumulates POS-catalog-relevant model/id writes across the current
    transaction and POSTs ONE HMAC-signed ``catalog.changed`` event to the
    OHINT middleware (``/webhooks/odoo/notify``) after commit — a bulk price
    update touching 50 products fires one webhook call with 50 ids, not 50
    calls. Reuses ``ohint.notify``'s already-configured webhook url/secret/
    tenant_id (n2d_ohint_notify is a hard dependency) rather than duplicating
    that setup. Silently no-ops when the webhook isn't configured, and never
    raises — a notify failure must not block the Odoo write that triggered it.
    """

    _name = "ohint.pos.catalog"
    _description = "OHINT POS catalog-change dispatcher"

    # odoo.tools.misc.Callbacks.data key for this addon's per-transaction
    # dirty-model buffer — documented as the aggregation mechanism for
    # exactly this pattern ("{module}.{feature}", cleared automatically once
    # postcommit callbacks run).
    _DIRTY_KEY = "n2d_ohint_pos.dirty"

    # Stock buffers separately from the catalog: it is keyed by warehouse (a
    # quantity belongs to one warehouse, unlike catalog rows which are
    # tenant-wide) and travels as its own `stock.changed` event, so the two
    # cannot share one buffer. See SPEC-041 Amendment B, D27.
    _STOCK_DIRTY_KEY = "n2d_ohint_pos.stock_dirty"

    @api.model
    def _mark_dirty(self, model_name, ids):
        """Record that `ids` of `model_name` changed in this transaction.

        Buffers on `self.env.cr.postcommit.data` — Odoo's own aggregation
        dict for postcommit callbacks, cleared automatically once `run()`
        fires — so multiple writes to different catalog models in one
        transaction still produce exactly one webhook call, registered the
        first time any of them calls in.
        """
        if not ids:
            return
        url, secret, tenant_id = self.env["ohint.notify"]._config()
        if not (url and secret and tenant_id):
            return  # not configured -> catalog sync disabled

        postcommit = self.env.cr.postcommit
        first_call = self._DIRTY_KEY not in postcommit.data
        buf = postcommit.data.setdefault(self._DIRTY_KEY, {})
        if first_call:
            postcommit.add(lambda: self._flush(url, secret, tenant_id, buf))
        buf.setdefault(model_name, set()).update(ids)

    @api.model
    def _mark_stock_dirty(self, warehouse_id, product_tmpl_ids):
        """Record that `product_tmpl_ids` changed quantity in `warehouse_id`.

        Product template ids (not variant ids) are reported deliberately: the
        catalog the branch already holds is keyed on product.template, so
        quantities must arrive in the same id space to be joinable client-side.
        Buffers and flushes exactly like _mark_dirty, on its own key.
        """
        if not (warehouse_id and product_tmpl_ids):
            return
        url, secret, tenant_id = self.env["ohint.notify"]._config()
        if not (url and secret and tenant_id):
            return  # not configured -> stock sync disabled

        postcommit = self.env.cr.postcommit
        first_call = self._STOCK_DIRTY_KEY not in postcommit.data
        buf = postcommit.data.setdefault(self._STOCK_DIRTY_KEY, {})
        if first_call:
            postcommit.add(lambda: self._flush_stock(url, secret, tenant_id, buf))
        buf.setdefault(warehouse_id, set()).update(product_tmpl_ids)

    @staticmethod
    def _flush_stock(url, secret, tenant_id, buf):
        warehouses = {
            str(wh_id): sorted(ids) for wh_id, ids in buf.items() if ids
        }
        if not warehouses:
            return
        # JSON object keys must be strings; the middleware parses them back to
        # int64 warehouse ids when resolving which branch(es) to mark dirty.
        OhintPosCatalog._post(
            url,
            secret,
            {
                "tenant_id": tenant_id,
                "event": "stock.changed",
                "warehouses": warehouses,
            },
        )

    @staticmethod
    def _flush(url, secret, tenant_id, buf):
        models_payload = {model: sorted(ids) for model, ids in buf.items() if ids}
        if not models_payload:
            return
        body = {
            "tenant_id": tenant_id,
            "event": "catalog.changed",
            "models": models_payload,
        }
        OhintPosCatalog._post(url, secret, body)

    @staticmethod
    def _post(url, secret, body):
        try:
            payload = json.dumps(body, separators=(",", ":"))
            timestamp = str(int(time.time()))
            # Sign the raw body only — the timestamp is a separate replay-guard
            # header, matching ohint.notify / the SPEC-017 sale-order-confirmed
            # webhook.
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
            _logger.warning("ohint pos catalog POST failed: %s", exc)
