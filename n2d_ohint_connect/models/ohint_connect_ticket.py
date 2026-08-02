from odoo import api, fields, models


class OhintConnectTicket(models.Model):
    """A spent Connect ticket.

    Existence of a row means the ticket has been used. The unique index on
    ``jti`` is what actually enforces single-use: the controller INSERTs and
    lets the database reject a duplicate, rather than reading first and then
    writing, which would let two concurrent replays both pass the read.
    """

    _name = "ohint.connect.ticket"
    _description = "OHINT Connect spent ticket"
    _rec_name = "jti"
    _order = "create_date desc"

    jti = fields.Char(string="Ticket ID", required=True, index=True)
    user_id = fields.Many2one("res.users", string="Signed in as", ondelete="cascade")
    operator = fields.Char(string="OHINT operator", help="Operator the middleware named in the ticket.")
    remote_addr = fields.Char(string="Remote address")

    _sql_constraints = [
        ("jti_uniq", "UNIQUE (jti)", "This Connect ticket has already been used."),
    ]

    @api.autovacuum
    def _gc_tickets(self):
        """Spent tickets only need to outlive the ticket TTL; keep 7 days for audit."""
        horizon = fields.Datetime.subtract(fields.Datetime.now(), days=7)
        self.sudo().search([("create_date", "<", horizon)]).unlink()
