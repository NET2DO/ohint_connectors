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
# Completely removed all asset declarations to prevent loading of problematic files
    'assets': {
        'web.assets_backend': [
            "hr_attendance_geolocation/static/src/js/attendance_geolocation.js",
        ],
    },
    # Add a flag to indicate this module has been fixed
    'hr_attendance_geolocation_fix': True
}
