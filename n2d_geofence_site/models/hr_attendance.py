from odoo import models, fields, api

from . import geocode


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    site_id = fields.Many2one("company.location", string="Site")
    visit_ids = fields.One2many(
        "employee.visit", "attend_id", string="Visits"
    )
    check_in_map = fields.Char(
        string="Check-in Map", compute="_compute_map"
    )
    check_out_map = fields.Char(
        string="Check-out Map", compute="_compute_map"
    )

    @api.depends(
        "check_in_latitude",
        "check_in_longitude",
        "check_out_latitude",
        "check_out_longitude",
    )
    def _compute_map(self):
        for rec in self:
            rec.check_in_map = (
                "http://maps.google.com/maps?q={},{}".format(
                    rec.check_in_latitude, rec.check_in_longitude
                )
                if rec.check_in_latitude or rec.check_in_longitude
                else False
            )
            rec.check_out_map = (
                "http://maps.google.com/maps?q={},{}".format(
                    rec.check_out_latitude, rec.check_out_longitude
                )
                if rec.check_out_latitude or rec.check_out_longitude
                else False
            )

    # Both address computes are overridden purely to make them safe — see
    # models/geocode.py. The base module calls Nominatim once per record with no
    # error handling, so a recompute during any module install aborts the install.
    @api.depends("check_in_latitude", "check_in_longitude")
    def _compute_check_in_address(self):
        geocode.apply(
            self, "check_in_latitude", "check_in_longitude", "check_in_address"
        )

    @api.depends("check_out_latitude", "check_out_longitude")
    def _compute_check_out_address(self):
        geocode.apply(
            self, "check_out_latitude", "check_out_longitude", "check_out_address"
        )
