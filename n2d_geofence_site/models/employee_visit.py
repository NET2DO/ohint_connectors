from odoo import models, fields, api

from . import geocode


class EmployeeVisit(models.Model):
    # _inherit, NOT _name — see company_location.py. Re-declaring `_name` here
    # replaced the base module's model outright and silently dropped its
    # check_in_address field.
    _inherit = "employee.visit"
    _order = "check_in asc"

    # The two fields the OHINT middleware writes on every waypoint and that the
    # hr_attendance_geolocation build on the n2d16 fleet does not have —
    # employee_id is literally commented out in its source. Without them a visit
    # can never be created (hr.go sets both on create, and reads back ordered by
    # check_in).
    employee_id = fields.Many2one(
        "hr.employee", string="Employee", index=True, ondelete="cascade"
    )
    check_in = fields.Datetime(string="Check In")

    # Re-declared only to attach @api.depends: the base module's version has no
    # depends at all, so the URL never refreshes when the coordinates change.
    check_in_map = fields.Char(string="Map URL", compute="_compute_map")

    @api.depends("check_in_latitude", "check_in_longitude")
    def _compute_map(self):
        for rec in self:
            rec.check_in_map = (
                "http://maps.google.com/maps?q={},{}".format(
                    rec.check_in_latitude, rec.check_in_longitude
                )
                if rec.check_in_latitude or rec.check_in_longitude
                else False
            )

    # Same reasoning as hr.attendance — see models/geocode.py. The base module's
    # `_compute_address` reverse-geocodes every row it is handed, unguarded.
    @api.depends("check_in_latitude", "check_in_longitude")
    def _compute_address(self):
        geocode.apply(
            self, "check_in_latitude", "check_in_longitude", "check_in_address"
        )
