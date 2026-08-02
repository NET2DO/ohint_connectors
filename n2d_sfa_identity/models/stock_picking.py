from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    salesperson_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Salesperson (Field)",
        index=True,
        copy=False,
        tracking=True,
        help="Field salesperson (OHINT employee) who confirmed this delivery. "
             "Field reps are not Odoo users; set by the OHINT connector.",
    )
