from odoo import fields, models, api
import requests


class EmployeeVisits(models.Model):
    _name = 'employee.visit'
    _description = 'Employee Visit Records'
    _rec_name = 'attend_id'

    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=False)
    attend_id = fields.Many2one(comodel_name="hr.attendance", string="Attendance", required=False)
    
    # Date fields
    date = fields.Datetime(string="Date", required=False)
    check_in = fields.Datetime(string="Check In", required=False, related='date', store=True)
    check_out = fields.Datetime(string="Check Out", required=False)
    
    # Location fields
    location_in = fields.Char(string="Location In", required=False)
    location_out = fields.Char(string="Location Out", required=False)
    
    # Check-in coordinates
    check_in_latitude = fields.Float(
        "Latitude", digits="Location",
    )
    check_in_longitude = fields.Float(
        "Longitude", digits="Location",
    )
    check_in_map = fields.Char(string="Check In Map URL", required=False, compute='_compute_map')
    check_in_address = fields.Char(string="Check-in Address", required=False)
    
    # Check-out coordinates
    check_out_latitude = fields.Float(
        "Checkout Latitude", digits="Location",
    )
    check_out_longitude = fields.Float(
        "Checkout Longitude", digits="Location",
    )
    check_out_map = fields.Char(string="Check Out Map URL", required=False, compute='_compute_checkout_map')

    def _compute_map(self):
        for rec in self:
            rec.check_in_map = (
                "http://maps.google.com/maps?q={},{}".format(rec.check_in_latitude, rec.check_in_longitude))
    
    def _compute_checkout_map(self):
        for rec in self:
            rec.check_out_map = (
                "http://maps.google.com/maps?q={},{}".format(rec.check_out_latitude, rec.check_out_longitude))
