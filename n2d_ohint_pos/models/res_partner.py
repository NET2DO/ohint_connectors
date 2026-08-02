from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_service_man = fields.Boolean(
        string="Service Man",
        help="Eligible as a delivery/collection contractor for OHint POS "
        "cash-on-delivery orders. Synced to enrolled POS branches via the "
        "service_men catalog type.",
    )

    def write(self, vals):
        res = super().write(vals)
        if "is_service_man" in vals and self.ids:
            self.env["ohint.pos.catalog"]._mark_dirty("res.partner", self.ids)
        return res

    # @api.model_create_multi must be re-declared on the override, not just
    # inherited from the base res.partner.create — without it, an external
    # XML-RPC create() call with a single vals dict (not wrapped in a list,
    # the calling convention selfservice-cloud's Go client uses everywhere)
    # breaks with "create() missing 1 required positional argument:
    # 'vals_list'" even though the exact same call works fine through direct
    # ORM/odoo-shell access — caught live via a real order that failed to
    # post because its customer.upsert-equivalent partner lookup hit this.
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        flagged = records.filtered("is_service_man")
        if flagged:
            self.env["ohint.pos.catalog"]._mark_dirty("res.partner", flagged.ids)
        return records
