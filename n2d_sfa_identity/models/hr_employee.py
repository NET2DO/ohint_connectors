from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    sfa_order_count = fields.Integer(
        string="Orders", compute="_compute_sfa_sale_counts"
    )
    sfa_invoice_count = fields.Integer(
        string="Invoices", compute="_compute_sfa_sale_counts"
    )
    sfa_payment_count = fields.Integer(
        string="Collections", compute="_compute_sfa_sale_counts"
    )
    sfa_delivery_count = fields.Integer(
        string="Deliveries", compute="_compute_sfa_sale_counts"
    )

    def _compute_sfa_sale_counts(self):
        order = self.env["sale.order"]
        picking = self.env["stock.picking"]
        move = self.env["account.move"]
        payment = self.env["account.payment"]
        for emp in self:
            emp.sfa_order_count = order.search_count(
                [("salesperson_employee_id", "=", emp.id)]
            )
            emp.sfa_delivery_count = picking.search_count(
                [("salesperson_employee_id", "=", emp.id)]
            )
            emp.sfa_invoice_count = move.search_count(
                [
                    ("salesperson_employee_id", "=", emp.id),
                    ("move_type", "in", ("out_invoice", "out_refund")),
                ]
            )
            emp.sfa_payment_count = payment.search_count(
                [("salesperson_employee_id", "=", emp.id)]
            )

    def action_view_sfa_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Orders",
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("salesperson_employee_id", "=", self.id)],
            "context": {"default_salesperson_employee_id": self.id},
        }

    def action_view_sfa_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Invoices",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [
                ("salesperson_employee_id", "=", self.id),
                ("move_type", "in", ("out_invoice", "out_refund")),
            ],
            "context": {"default_move_type": "out_invoice"},
        }

    def action_view_sfa_payments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Collections",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("salesperson_employee_id", "=", self.id)],
        }

    def action_view_sfa_deliveries(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Deliveries",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("salesperson_employee_id", "=", self.id)],
        }
