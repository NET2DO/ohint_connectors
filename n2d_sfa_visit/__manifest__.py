{
    "name": "N2D SFA Field Visit",
    "summary": "Customer-anchored field-sales visits with geofence proof. "
               "A standalone visit (no open attendance punch required) that "
               "records the salesperson's check-in geolocation and verifies "
               "it falls within a configurable radius of the customer.",
    "version": "19.0.1.2.0",
    "license": "LGPL-3",
    "author": "N2D",
    "category": "Sales",
    # hr_attendance_geolocation: reuse of the geo conventions / "Location"
    #   decimal precision and the check_in_* lat/long + _compute_map pattern.
    # base_geolocalize: provides res.partner.partner_latitude / partner_longitude,
    #   which the haversine distance computes against. Without it those fields do
    #   not exist and the compute would raise. (See deviations note in README.)
    # hr: salesperson is an hr.employee (field reps are not Odoo users —
    #   SPEC-017A-SEC). Replaces the old sales_team/user_id scoping; access is
    #   controlled in OHINT, not by Odoo record rules.
    "depends": [
        "hr_attendance_geolocation",
        "base_geolocalize",
        "hr",
    ],
    "data": [
        "security/sfa_visit_security.xml",
        "security/ir.model.access.csv",
        "views/sfa_visit_views.xml",
    ],
    "installable": True,
    "application": True,
}
