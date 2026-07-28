from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def write(self, vals):
        res = super().write(vals)
        if self.ids:
            self.env["ohint.pos.catalog"]._mark_dirty("pos.payment.method", self.ids)
        return res

    def create(self, vals_list):
        records = super().create(vals_list)
        if records:
            self.env["ohint.pos.catalog"]._mark_dirty("pos.payment.method", records.ids)
        return records
