from odoo import api, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def write(self, vals):
        res = super().write(vals)
        if self.ids:
            self.env["ohint.pos.catalog"]._mark_dirty("product.pricelist", self.ids)
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
            self.env["ohint.pos.catalog"]._mark_dirty("product.pricelist", records.ids)
        return records


class ProductPricelistItem(models.Model):
    """Pricing rules live on the item, not the pricelist header — a rule edit
    doesn't touch the parent record, but it's exactly what POS branches need
    to see. Reported under "product.pricelist" (the wire model the middleware
    tracks per catalog.go's catalogKeyToModel), keyed by the PARENT pricelist
    id, since that's the id Delta/Full pull by.
    """

    _inherit = "product.pricelist.item"

    def write(self, vals):
        res = super().write(vals)
        ids = self.mapped("pricelist_id").ids
        if ids:
            self.env["ohint.pos.catalog"]._mark_dirty("product.pricelist", ids)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        ids = records.mapped("pricelist_id").ids
        if ids:
            self.env["ohint.pos.catalog"]._mark_dirty("product.pricelist", ids)
        return records
