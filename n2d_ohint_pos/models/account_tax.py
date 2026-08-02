from odoo import api, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    def write(self, vals):
        res = super().write(vals)
        if self.ids:
            self.env["ohint.pos.catalog"]._mark_dirty("account.tax", self.ids)
        return res

    # @api.model_create_multi must be re-declared on the override — without
    # it, an external XML-RPC create() call with a single (non-list) vals
    # dict breaks with "create() missing 1 required positional argument:
    # 'vals_list'" even though it works fine via direct ORM access. Caught
    # live on res.partner's identical override; applied here too since the
    # risk is the same.
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if records:
            self.env["ohint.pos.catalog"]._mark_dirty("account.tax", records.ids)
        return records
