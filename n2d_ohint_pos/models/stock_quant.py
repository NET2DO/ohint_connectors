from odoo import api, models


class StockQuant(models.Model):
    """SPEC-041 Amendment B (B1): emit `stock.changed` when on-hand moves.

    Hooked on stock.quant rather than stock.move deliberately. A move only
    covers transfers; inventory adjustments, scrap and the "Update Quantity"
    form write quants directly, and a move-based hook silently misses them —
    which is exactly the case the product owner hit (editing a quantity in the
    Downtown warehouse produced no sync).

    Note this is NOT the catalog path: writing a quant does not touch
    product.template, so product.template.write never fires and the product
    never enters the catalog dirty set. Stock needs its own signal.
    """

    _inherit = "stock.quant"

    def _ohint_mark_stock_dirty(self):
        """Group this recordset by warehouse and report changed templates.

        Only internal locations carry sellable on-hand stock — customer,
        supplier, inventory-loss and production locations are counterparties in
        the double-entry, and reporting them would emit noise for every sale.
        """
        by_warehouse = {}
        for quant in self:
            location = quant.location_id
            if not location or location.usage != "internal":
                continue
            warehouse = location.warehouse_id
            if not warehouse:
                continue  # internal but outside any warehouse — nothing maps to it
            tmpl_id = quant.product_id.product_tmpl_id.id
            if tmpl_id:
                by_warehouse.setdefault(warehouse.id, set()).add(tmpl_id)

        catalog = self.env["ohint.pos.catalog"]
        for warehouse_id, tmpl_ids in by_warehouse.items():
            catalog._mark_stock_dirty(warehouse_id, tmpl_ids)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ohint_mark_stock_dirty()
        return records

    def write(self, vals):
        # Capture the pre-write grouping first: a quant whose location_id moves
        # changes the on-hand of BOTH warehouses, and after super() the old one
        # is unreachable. Harmless duplication when location is untouched — the
        # middleware's dirty set coalesces ids.
        if "location_id" in vals:
            self._ohint_mark_stock_dirty()
        res = super().write(vals)
        self._ohint_mark_stock_dirty()
        return res

    def unlink(self):
        # Must run before the rows go: after super() there is no location or
        # product left to resolve a warehouse from.
        self._ohint_mark_stock_dirty()
        return super().unlink()
