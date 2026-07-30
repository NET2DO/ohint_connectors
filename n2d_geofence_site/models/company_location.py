from odoo import models, fields, api


class CompanyLocation(models.Model):
    # _inherit, NOT _name. `hr_attendance_geolocation` defines this model with a
    # bare `_name`; declaring `_name` again here would REPLACE that definition
    # rather than extend it, dropping its `langitude` field from the registry —
    # and that module's own views/res_company.xml renders `langitude`, so every
    # Company form on the fleet would raise "Field langitude does not exist".
    _inherit = 'company.location'

    # The middleware reads `longitude`; the base module only has the misspelled
    # `langitude`. Not required=True: on databases that already hold sites this
    # column starts NULL, and a required field would make Odoo try (and log a
    # failure for) SET NOT NULL during install. post_init_hook fills it.
    longitude = fields.Float('Longitude', digits='Location')

    # Both spellings have to stay in step, in both directions:
    #   * `langitude` is required=True on the base model, so a site created from
    #     this module's form — which only shows `longitude` — would be rejected
    #     as "Langitude is not set" if we didn't mirror it across;
    #   * a site edited through the base module's own Company form writes only
    #     `langitude`, and the app would then read a stale `longitude`.
    # Mirroring on create/write keeps the two columns from ever disagreeing,
    # which is what lets both views stay usable side by side.
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            _mirror(vals)
        return super().create(vals_list)

    def write(self, vals):
        _mirror(vals)
        return super().write(vals)

    @api.onchange('longitude')
    def _onchange_longitude(self):
        for rec in self:
            rec.langitude = rec.longitude

    @api.onchange('langitude')
    def _onchange_langitude(self):
        for rec in self:
            rec.longitude = rec.langitude


def _mirror(vals):
    """Copy whichever spelling was supplied onto the other one."""
    if 'longitude' in vals and 'langitude' not in vals:
        vals['langitude'] = vals['longitude']
    elif 'langitude' in vals and 'longitude' not in vals:
        vals['longitude'] = vals['langitude']
