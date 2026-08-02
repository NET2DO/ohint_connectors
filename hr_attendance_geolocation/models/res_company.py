from odoo import models, fields, api ,exceptions
from datetime import datetime



class GeoLocation(models.Model):
    _name = 'company.location'

    name = fields.Char('Site Name', required=True)
    latitude = fields.Float('Latitude', digits="Location", required=True, )
    longitude = fields.Float('Longitude', digits="Location", required=True, )
    radius = fields.Float('Radius', required=True, )
    company_id = fields.Many2one(comodel_name="res.company", string="", required=False, )


class ResCompany(models.Model):
    _inherit = 'res.company'
    location_ids = fields.One2many(comodel_name="company.location", inverse_name="company_id", string="", required=False, )




