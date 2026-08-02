from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    salesperson_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Salesperson (Field)",
        index=True,
        copy=False,
        tracking=True,
        help="Field salesperson (OHINT employee) attributed to this document; "
             "propagated from the source sale order.",
    )
