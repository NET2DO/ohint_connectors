from odoo import api, fields, models

# Partner fields the enrolled-branch catalog serves (customers + service_men
# slices, selfservice-cloud internal/odoo/pos.go). A write touching any of
# these must bump the tenant catalog version, or the till only ever learns
# about the partner on its next full resync — which in practice is never.
_POS_PARTNER_FIELDS = {
    "name",
    "phone",
    "mobile",
    "email",
    "vat",
    "active",
    "is_service_man",
}


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
        if self.ids and _POS_PARTNER_FIELDS.intersection(vals):
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
    #
    # Every created partner is marked dirty, not just service men: the
    # customers catalog slice means a contact created anywhere in Odoo (back
    # office, portal, the middleware's own customer.upsert) must reach
    # enrolled tills on the next delta.
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if records:
            self.env["ohint.pos.catalog"]._mark_dirty("res.partner", records.ids)
        return records
