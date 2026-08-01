# Copyright 2019 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    traceable = fields.Boolean(
        string='Traceable',
        required=False
    )
    traceable_type = fields.Selection(
        string="Traceable Type", 
        selection=[
            ('Traceable', 'Traceable'), 
            ('Company Site', 'Company Site'),
        ],
        required=False,
    )
    site_ids = fields.Many2many(
        'company.location', 
        'employee_site_rel', 
        'employee', 
        'site', 
        string='Site'
    )

    def attendance_manual(self, next_action, entered_pin=False, location=False):
        res = super(
            HrEmployee, self.with_context(attendance_location=location)
        ).attendance_manual(next_action, entered_pin)
        return res

    def _attendance_action_change(self):
        """Override to include geolocation data when employees check in/out."""
        res = super()._attendance_action_change()
        location = self.env.context.get("attendance_location", False)
        if location:
            if self.attendance_state == "checked_in":
                res.write({
                    "check_in_latitude": location[0],
                    "check_in_longitude": location[1],
                })
            else:
                res.write({
                    "check_out_latitude": location[0],
                    "check_out_longitude": location[1],
                })
        return res
