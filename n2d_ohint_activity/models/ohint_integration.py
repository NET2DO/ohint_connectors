from odoo import _, api, models
from odoo.exceptions import AccessError

# Fields an app edit may change; anything else is refused.
_EDITABLE = {"date_deadline", "summary", "note"}


class MailActivityIntegration(models.Model):
    """Integration entry points for the OHINT middleware.

    The middleware reads and acts on activities as the tenant's integration
    account. Odoo's record rules hide some records even from an administrator
    — a task without a project is a private to-do, visible only to its
    assignees — and an activity on a record you cannot read is itself
    invisible. The employee the activity is for must still see it in the app,
    so these methods run the same reads and actions with sudo().

    Only a Settings administrator (the integration account) may call them, and
    the middleware only ever asks for the caller's own activities (by user or
    by ohint_employee_id) and authorizes every action before calling.
    """

    _inherit = "mail.activity"

    def _ohint_check(self):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("Only the OHINT integration account may call this."))

    @api.model
    def ohint_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        self._ohint_check()
        return self.sudo().search_read(domain or [], fields, offset=offset, limit=limit, order=order)

    @api.model
    def ohint_search_count(self, domain=None):
        self._ohint_check()
        return self.sudo().search_count(domain or [])

    def ohint_read(self, fields=None):
        self._ohint_check()
        return self.sudo().read(fields)

    def ohint_feedback(self, feedback=False, attachment_ids=None):
        self._ohint_check()
        self.sudo().action_feedback(feedback=feedback, attachment_ids=attachment_ids)
        return True

    def ohint_write(self, vals):
        self._ohint_check()
        bad = set(vals) - _EDITABLE
        if bad:
            raise AccessError(_("These fields cannot be changed from the app: %s", ", ".join(sorted(bad))))
        return self.sudo().write(vals)

    def ohint_unlink(self):
        self._ohint_check()
        return self.sudo().unlink()

    @api.model
    def ohint_schedule(self, res_model, res_id, vals):
        """Schedule on a record the integration account may not be able to
        read. Returns the new activity ids (a list, never a recordset)."""
        self._ohint_check()
        record = self.env[res_model].sudo().browse(int(res_id)).exists()
        if not record:
            raise AccessError(_("That record no longer exists."))
        return record.activity_schedule(**(vals or {})).ids

    @api.model
    def ohint_create_attachment(self, res_model, res_id, name, datas):
        """Attach a file (a done activity's photo) to a record the integration
        account may not be able to read. Returns the attachment id."""
        self._ohint_check()
        record = self.env[res_model].sudo().browse(int(res_id)).exists()
        if not record:
            raise AccessError(_("That record no longer exists."))
        return self.env["ir.attachment"].sudo().create({
            "name": name, "res_model": res_model, "res_id": record.id, "datas": datas}).id
