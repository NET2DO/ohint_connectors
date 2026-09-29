{
    "name": "OHINT Activities for Employees",
    "summary": "Assign activities to an employee, with or without an Odoo user, for the OHINT app",
    "description": "Adds Assign to employee to activities so the OHINT app can show and notify activities of employees without an Odoo user. Picking an employee who has a user also fills Assigned to; automatic follow-ups keep the employee.",
    "version": "18.0.1.1.0",
    "category": "Productivity",
    "author": "OHINT",
    "website": "https://www.ohint.net",
    "license": "LGPL-3",
    "depends": ["mail", "hr"],
    "data": ["views/mail_activity_views.xml", "views/mail_activity_schedule_views.xml"],
    "installable": True,
    "application": False,
}
