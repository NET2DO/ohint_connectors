{
    "name": "N2D Geofence Sites",
    "summary": "Manage circular geofence sites (company.location) and employee "
               "tracking flags used by the OHINT mobile app. Sets traceable / "
               "traceable_type / site_ids on hr.employee and stores GPS "
               "waypoints (employee.visit). Radius enforcement is performed by "
               "the OHINT middleware, not by this module.",
    "version": "16.0.1.0.0",
    "license": "LGPL-3",
    "author": "N2D",
    "category": "Human Resources",
    # Additive overlay. On the n2d16 fleet `hr_attendance_geolocation` is
    # already installed in ~30 live customer databases and already provides
    # company.location, employee.visit, hr.employee.site_ids/traceable and the
    # hr.attendance geo fields. This module only ADDS the handful of fields the
    # OHINT middleware needs on top of it — it never replaces that module, so
    # installing it does not rewrite any existing schema or data.
    "depends": ["hr_attendance_geolocation"],
    "data": [
        "security/ir.model.access.csv",
        "views/geofence_views.xml",
        "views/hr_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
