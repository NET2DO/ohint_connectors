from odoo import models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def write(self, vals):
        res = super().write(vals)
        if self.ids:
            self.env["ohint.pos.catalog"]._mark_dirty("product.pricelist", self.ids)
        return res

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

    def create(self, vals_list):
        records = super().create(vals_list)
        ids = records.mapped("pricelist_id").ids
        if ids:
            self.env["ohint.pos.catalog"]._mark_dirty("product.pricelist", ids)
        return records
