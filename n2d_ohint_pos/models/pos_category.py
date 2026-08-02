"""SPEC-041 Amendment C (C1): report POS category edits to the middleware.

Note there is deliberately no separate "membership changed" event. A product's
categories live in `pos_categ_ids` ON product.template, and the branch reads
them off the product's own row — so moving a product between categories is a
product change as far as the sync is concerned, already covered by
product_template.py's write(). That absence is the first thing someone looks
for, hence this note.
"""

from odoo import api, models


class PosCategory(models.Model):
    """Categories are what the till's left-hand rail is built from, so a rename
    or a re-sequence has to reach the branch the same way a price change does.
    """

    _inherit = "pos.category"

    def write(self, vals):
        res = super().write(vals)
        if self.ids:
            self.env["ohint.pos.catalog"]._mark_dirty("pos.category", self.ids)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if records:
            self.env["ohint.pos.catalog"]._mark_dirty("pos.category", records.ids)
        return records

    def unlink(self):
        # Marked BEFORE the delete: after super() the ids are gone, and the
        # branch still has to be told the category no longer exists or it keeps
        # showing an empty tab forever.
        if self.ids:
            self.env["ohint.pos.catalog"]._mark_dirty("pos.category", self.ids)
        return super().unlink()
