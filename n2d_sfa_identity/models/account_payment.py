from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    salesperson_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Salesperson (Field)",
        index=True,
        copy=False,
        tracking=True,
        help="Field salesperson (OHINT employee) attributed to this collection; "
             "propagated from the paid invoice.",
    )


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payment_vals_from_wizard(self, batch_result):
        # Propagate the field salesperson invoice->payment (SPEC-017A-SEC FR-006).
        # SPEC-017A8: prefer the collecting rep (passed in ctx) over the invoice's
        # salesperson, so attribution = who collected, not who sold.
        vals = super()._create_payment_vals_from_wizard(batch_result)
        collector = self.env.context.get("sfa_collector_employee_id")
        if collector:
            vals["salesperson_employee_id"] = collector
        else:
            move = self.line_ids.move_id[:1]
            if move and move.salesperson_employee_id:
                vals["salesperson_employee_id"] = move.salesperson_employee_id.id
        return vals
