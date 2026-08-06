import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    """SPEC-037 FR-4b: notify the salesperson a customer is assigned to when a
    payment is registered against that customer in Odoo.

    Hooks the post of an inbound *customer* payment and POSTs a signed
    ``payment.received`` event to the OHINT middleware, which resolves the
    customer's owning salesperson and notifies them in-app. The middleware
    dedupes on ``dedupe_key`` (``payment.received:<payment_id>``), so a
    reset-to-draft + re-post never double-notifies. Best-effort: a webhook
    failure never blocks posting the payment.
    """

    _inherit = "account.payment"

    def _ohint_notify_payment_received(self):
        dispatcher = self.env["ohint.notify"]
        for pay in self:
            # Only inbound customer payments. No state guard: this runs from
            # action_post() AFTER super() succeeds, so the payment is already
            # confirmed — and on Odoo 18+/19 there is no reliable "posted" signal
            # at this point (payment.state is the reconciliation state
            # in_process/paid/…, and move_id may not be set yet).
            if pay.payment_type != "inbound" or pay.partner_type != "customer":
                continue
            if not pay.partner_id:
                continue

            # Invoice reference(s): the reconciled customer invoice name(s),
            # joined with ", " when a payment settles several. Falls back to the
            # payment memo/ref (the Register-Payment wizard sets this to the
            # invoice reference), then "".
            invoice_ref = ""
            if "reconciled_invoice_ids" in pay._fields:
                names = [n for n in pay.reconciled_invoice_ids.mapped("name") if n]
                invoice_ref = ", ".join(names)
            if not invoice_ref:
                # Odoo 18+/19 renamed account.payment.ref → memo; getattr with a
                # default absorbs the AttributeError on whichever name is absent.
                invoice_ref = getattr(pay, "memo", None) or getattr(pay, "ref", None) or ""

            # "How they paid": the journal name (Cash / Bank / …) is the most
            # user-meaningful label — the payment method line is usually the
            # generic "Manual". Fall back to the method line if the journal is
            # unnamed.
            method = (pay.journal_id.name or pay.payment_method_line_id.name or "")

            # Payment (accounting) date. On Odoo 18+/19 `date` isn't a stored
            # column on account.payment (it lives on the journal entry), so fall
            # back to move_id.date; getattr absorbs the field-name differences.
            pdate = getattr(pay, "date", None) or (pay.move_id.date if pay.move_id else None)
            payment_date = str(pdate) if pdate else ""

            dispatcher._dispatch_event({
                "event": "payment.received",
                "partner_odoo_id": pay.partner_id.id,
                "customer_name": pay.partner_id.name or "",
                "amount": pay.amount,
                "currency": pay.currency_id.name or "",
                "method": method,
                "invoice_ref": invoice_ref,
                "payment_date": payment_date,
                "dedupe_key": "payment.received:%s" % pay.id,
            })

    def action_post(self):
        res = super().action_post()
        try:
            self._ohint_notify_payment_received()
        except Exception:  # noqa: BLE001 — a notify failure must never block posting
            _logger.warning("ohint payment.received dispatch failed", exc_info=True)
        return res
