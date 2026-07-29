{
    "name": "OHINT Connect (console sign-in)",
    "version": "18.0.1.0.0",
    "summary": "One-click sign-in to this database from the OHINT console (app.ohint.net)",
    "description": """
OHINT Connect
=============

Lets an authorised OHINT operator open this database already signed in as a
chosen internal user, without typing a password — the same "Connect as" flow
odoo.sh offers on its projects.

The console never learns a user's password. It asks the OHINT middleware for a
one-time, short-lived, HMAC-signed ticket; this module verifies that ticket and
establishes the session.

Security
--------
* The signing secret lives in ``ir.config_parameter`` under
  ``ohint_connect.secret`` and is written by the middleware over an
  authenticated JSON-RPC call. Without it, this module refuses every request.
* A ticket is bound to THIS database, expires in seconds, and is single-use —
  replay is blocked by a unique index, not by a check-then-act read.
* Every accepted and every rejected attempt is logged with the operator the
  middleware named, so the database keeps its own audit trail independent of
  the console's.
""",
    "author": "OHINT",
    "website": "https://www.ohint.net",
    "category": "Tools",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
