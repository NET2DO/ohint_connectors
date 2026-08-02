from math import asin, cos, radians, sin, sqrt

from odoo import api, fields, models

# Mean Earth radius in metres (haversine).
EARTH_RADIUS_M = 6371000.0


class SfaVisit(models.Model):
    """Standalone, customer-anchored field-sales visit with geofence proof.

    Unlike ``employee.visit`` (from ``hr_attendance_geolocation``) this model is
    NOT tied to an ``hr.attendance`` record: a salesperson can log a visit to a
    customer without an open attendance punch. The check-in geolocation is
    captured by the client, but the distance to the customer and the
    geofence verdict are ALWAYS recomputed server-side so a client cannot fake
    a "within geofence" result.
    """

    _name = "sfa.visit"
    _description = "SFA Field Visit"
    _order = "check_in desc, id desc"
    _rec_name = "partner_id"

    # --- Anchors -----------------------------------------------------------
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=True,
        index=True,
        help="The customer this visit was made to. The geofence is checked "
             "against this customer's geolocation (partner_latitude / "
             "partner_longitude).",
    )
    # Field salesperson = an hr.employee (SPEC-017A-SEC). Field reps are NOT
    # Odoo users, so attribution lives here, never on user_id. The connector
    # (ohint_sales_bot) stamps this on every visit; it is filterable/group-by.
    salesperson_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Salesperson",
        index=True,
        help="The field salesperson (OHINT employee) who made this visit. "
             "Set by the OHINT connector; field reps are not Odoo users.",
    )
    # Optional native salesperson — set ONLY when the employee is linked to an
    # Odoo user (hybrid case). Never defaulted to the connector/bot user.
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson (User)",
        index=True,
        help="Native Odoo salesperson, set only for employees linked to a user.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    # --- Timing ------------------------------------------------------------
    check_in = fields.Datetime(
        string="Check In", default=lambda self: fields.Datetime.now()
    )
    check_out = fields.Datetime(string="Check Out")

    # --- Geolocation (captured client-side) --------------------------------
    check_in_latitude = fields.Float("Check-in Latitude", digits="Location")
    check_in_longitude = fields.Float("Check-in Longitude", digits="Location")
    check_out_latitude = fields.Float("Check-out Latitude", digits="Location")
    check_out_longitude = fields.Float("Check-out Longitude", digits="Location")

    check_in_map = fields.Char(
        string="Check-in Map", compute="_compute_map", help="Google Maps link "
        "for the check-in coordinates."
    )
    check_out_map = fields.Char(
        string="Check-out Map", compute="_compute_map"
    )

    # --- Classification ----------------------------------------------------
    purpose = fields.Selection(
        selection=[
            ("sales", "Sales"),
            ("collection", "Collection"),
            ("survey", "Survey"),
            ("delivery", "Delivery"),
            ("other", "Other"),
        ],
        string="Purpose",
        default="sales",
    )
    # Field-sales outcome vocabulary — single source of truth shared with the
    # OHINT app (SPEC-017A-SEC 3-gap patch); no Go-side translation.
    outcome = fields.Selection(
        selection=[
            ("order_placed", "Order Placed"),
            ("no_order", "No Order"),
            ("follow_up", "Follow Up"),
            ("no_contact", "No Contact"),
        ],
        string="Outcome",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("open", "Open"),
            ("done", "Done"),
        ],
        string="Status",
        default="draft",
        required=True,
        index=True,
    )

    notes = fields.Text(string="Notes")
    signature = fields.Binary(string="Signature")
    photo = fields.Binary(string="Photo")

    # --- Geofence (computed server-side) -----------------------------------
    geofence_radius_m = fields.Float(
        string="Geofence Radius (m)",
        default=150.0,
        help="Maximum allowed distance (in metres) between the check-in "
             "location and the customer for the visit to count as on-site.",
    )
    distance_m = fields.Float(
        string="Distance (m)",
        compute="_compute_distance",
        store=True,
        help="Great-circle (haversine) distance in metres between the "
             "check-in coordinates and the customer's geolocation. Computed "
             "server-side.",
    )
    within_geofence = fields.Boolean(
        string="Within Geofence",
        compute="_compute_within_geofence",
        store=True,
        help="True when the check-in location is within the geofence radius "
             "of the customer. Computed server-side; never set by the client.",
    )

    # --- Computes ----------------------------------------------------------
    def _compute_map(self):
        for rec in self:
            rec.check_in_map = "http://maps.google.com/maps?q={},{}".format(
                rec.check_in_latitude, rec.check_in_longitude
            )
            rec.check_out_map = "http://maps.google.com/maps?q={},{}".format(
                rec.check_out_latitude, rec.check_out_longitude
            )

    @staticmethod
    def _haversine_m(lat1, lon1, lat2, lon2):
        """Great-circle distance between two WGS84 points, in metres."""
        rlat1, rlon1, rlat2, rlon2 = (
            radians(lat1),
            radians(lon1),
            radians(lat2),
            radians(lon2),
        )
        dlat = rlat2 - rlat1
        dlon = rlon2 - rlon1
        a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
        return 2 * EARTH_RADIUS_M * asin(sqrt(a))

    @api.depends(
        "check_in_latitude",
        "check_in_longitude",
        "partner_id.partner_latitude",
        "partner_id.partner_longitude",
    )
    def _compute_distance(self):
        for rec in self:
            p = rec.partner_id
            p_lat = p.partner_latitude if p else 0.0
            p_lon = p.partner_longitude if p else 0.0
            # A 0/0 coordinate means "not geolocated"; treat as no fix.
            if (
                rec.check_in_latitude
                and rec.check_in_longitude
                and p_lat
                and p_lon
            ):
                rec.distance_m = rec._haversine_m(
                    rec.check_in_latitude,
                    rec.check_in_longitude,
                    p_lat,
                    p_lon,
                )
            else:
                rec.distance_m = 0.0

    @api.depends("distance_m", "geofence_radius_m")
    def _compute_within_geofence(self):
        for rec in self:
            p = rec.partner_id
            has_fix = bool(
                rec.check_in_latitude
                and rec.check_in_longitude
                and p
                and p.partner_latitude
                and p.partner_longitude
            )
            rec.within_geofence = has_fix and (
                rec.distance_m <= rec.geofence_radius_m
            )


class HrEmployee(models.Model):
    """Employee smart button → that employee's field visits (SPEC-017A-SEC).

    Lives here (hr-only) so n2d_sfa_visit never depends on sale/account; the
    Orders/Collections buttons live in n2d_sfa_identity.
    """

    _inherit = "hr.employee"

    sfa_visit_count = fields.Integer(
        string="Visits", compute="_compute_sfa_visit_count"
    )

    def _compute_sfa_visit_count(self):
        visit = self.env["sfa.visit"]
        for emp in self:
            emp.sfa_visit_count = visit.search_count(
                [("salesperson_employee_id", "=", emp.id)]
            )

    def action_view_sfa_visits(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Field Visits",
            "res_model": "sfa.visit",
            "view_mode": "list,form",
            "domain": [("salesperson_employee_id", "=", self.id)],
            "context": {"default_salesperson_employee_id": self.id},
        }
