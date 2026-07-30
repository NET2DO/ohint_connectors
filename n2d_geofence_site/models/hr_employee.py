from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    traceable = fields.Boolean(string="Traceable")
    traceable_type = fields.Selection(
        string="Traceable Type",
        selection=[
            ("Traceable", "Traceable"),
            ("Company Site", "Company Site"),
        ],
    )
    site_ids = fields.Many2many(
        "company.location",
        "employee_site_rel",
        "employee",
        "site",
        string="Sites",
    )

    @api.onchange("traceable")
    def _onchange_traceable(self):
        # The OHINT middleware treats any non-empty traceable_type as "tracked",
        # whatever the checkbox says, so clear it here or unticking Traceable
        # would leave the employee still being tracked.
        for rec in self:
            if not rec.traceable:
                rec.traceable_type = False
                rec.site_ids = [(5, 0, 0)]

    @api.onchange("traceable_type")
    def _onchange_traceable_type(self):
        for rec in self:
            if rec.traceable_type != "Company Site":
                rec.site_ids = [(5, 0, 0)]
