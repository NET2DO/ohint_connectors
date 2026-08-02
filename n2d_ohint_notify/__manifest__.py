{
    "name": "N2D OHINT Notify (Back-office → App)",
    "summary": "Pushes back-office record changes to the OHINT middleware "
               "notification webhook so the affected employee is notified in the "
               "app (SPEC-037 FR-4b). Leave approved/refused, employee "
               "assignment/profile changes, and back-office attendance "
               "corrections are HMAC-signed and POSTed to /webhooks/odoo/notify "
               "after the transaction commits.",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "author": "N2D",
    "category": "Human Resources",
    "depends": ["hr", "hr_holidays", "hr_attendance"],
    "data": [],
    "installable": True,
    "application": False,
}
