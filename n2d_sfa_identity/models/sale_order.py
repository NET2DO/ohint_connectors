from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    salesperson_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Salesperson (Field)",
        index=True,
        copy=False,
        tracking=True,
        help="Field salesperson (OHINT employee) who authored this order. "
             "Field reps are not Odoo users; set by the OHINT connector.",
    )

    def _prepare_invoice(self):
        # Propagate the field salesperson onto the invoice (SPEC-017A-SEC FR-006).
        vals = super()._prepare_invoice()
        if self.salesperson_employee_id:
            vals["salesperson_employee_id"] = self.salesperson_employee_id.id
        return vals

