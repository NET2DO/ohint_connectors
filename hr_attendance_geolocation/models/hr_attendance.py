# Copyright 2019 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"
    
    # Adding date field to fix view error
    date = fields.Datetime(string="Date", related="check_in", store=True)

    check_in_latitude = fields.Float(
        "Check-in Latitude", digits="Location", readonly=True
    )
    check_in_longitude = fields.Float(
        "Check-in Longitude", digits="Location", readonly=True
    )
    check_out_latitude = fields.Float(
        "Check-out Latitude", digits="Location", readonly=True
    )
    check_out_longitude = fields.Float(
        "Check-out Longitude", digits="Location", readonly=True
    )

    check_in_map = fields.Char(string="", required=False, compute='_compute_map')
    check_out_map = fields.Char(string="", required=False, compute='_compute_map')
    check_in_address = fields.Char(string="Check-in Address", required=False)
    check_out_address = fields.Char(string="Check-out Address", required=False)
    visit_ids = fields.One2many(comodel_name="employee.visit", inverse_name="attend_id", string="Visits", required=False, )
    site_id = fields.Many2one('company.location', string='Site')



    def _compute_map(self):
        for rec in self:
            rec.check_in_map = (
                "http://maps.google.com/maps?q={},{}".format(rec.check_in_latitude, rec.check_in_longitude))

            rec.check_out_map = (
                "http://maps.google.com/maps?q={},{}".format(rec.check_out_latitude, rec.check_out_longitude))
