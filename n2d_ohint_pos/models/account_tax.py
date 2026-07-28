from odoo import models


class AccountTax(models.Model):
    _inherit = "account.tax"

    def write(self, vals):
        res = super().write(vals)
        if self.ids:
            self.env["ohint.pos.catalog"]._mark_dirty("account.tax", self.ids)
        return res

    def create(self, vals_list):
        records = super().create(vals_list)
        if records:
            self.env["ohint.pos.catalog"]._mark_dirty("account.tax", records.ids)
        return records
