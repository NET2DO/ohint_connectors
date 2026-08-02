# Copyright 2019 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Hr Attendance Geolocation",
    "summary": """
        With this module the geolocation of the user is tracked at the
        check-in/check-out step""",
    "version": "1.0",
    "license": "AGPL-3",
    "author": "ForgeFlow S.L., Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr",
    "depends": ["hr_attendance"],  # Removed web_gantt dependency as we're providing a workaround
    "installable": True,
    "auto_install": True,
    "data": [
        "views/hr_attendance_views.xml",
        "data/location_data.xml",
        "security/ir.model.access.csv",
        "views/res_company.xml",
        "views/employee_visits.xml",
        "views/attendance_gantt_view.xml",  # Added new view for gantt replacement
    ],
# NOTE: the v16 web-UI geolocation patch (static/src/js/attendance_geolocation.js)
# imports @hr_attendance/js/my_attendances and @hr_attendance/js/kiosk_confirm,
# which DO NOT EXIST in Odoo 19 (the attendance frontend was rewritten as OWL
# components: components/check_in_out, public_kiosk, ...). Loading it leaves two
# JS modules undefined and breaks the whole web.assets_web bundle. Disabled until
# the patch is re-implemented for v19. The model/data (company.location geofence
# sites, attendance site_id, employee site field) are unaffected.
    'assets': {},
}
