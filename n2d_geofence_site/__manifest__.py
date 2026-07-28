{
    "name": "N2D Geofence Sites",
    "summary": "Manage circular geofence sites (company.location) used by "
               "attendance check-in and the OHINT mobile app. Employees set to "
               "'Company Site' can only check in/out within an assigned site's "
               "radius.",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "author": "N2D",
    "category": "Human Resources",
    "depends": ["hr_attendance_geolocation"],
    "data": [
        "views/geofence_views.xml",
    ],
    "installable": True,
    "application": False,
}
