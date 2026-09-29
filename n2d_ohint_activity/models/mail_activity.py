from odoo import api, fields, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    ohint_employee_id = fields.Many2one(
        "hr.employee",
        string="Assign to employee",
        index=True,
        ondelete="set null",
        help="The employee who does this activity in the OHINT app. Use it for "
        "employees without an Odoo user; for one who has a user, "
        "'Assigned to' follows automatically.",
    )

    @api.onchange("ohint_employee_id")
    def _onchange_ohint_employee_id(self):
        if self.ohint_employee_id.user_id:
            self.user_id = self.ohint_employee_id.user_id

    @api.model_create_multi
    def create(self, vals_list):
        # Same rule over RPC as in the dialog: the employee is the source of
        # truth, so one who has a user also takes "Assigned to". (Odoo's
        # activity_schedule always fills user_id with the current user before
        # create, so a default cannot be told from a choice here.)
        for vals in vals_list:
            if vals.get("ohint_employee_id"):
                emp = self.env["hr.employee"].sudo().browse(vals["ohint_employee_id"])
                if emp.user_id:
                    vals["user_id"] = emp.user_id.id
        return super().create(vals_list)

    def _prepare_next_activity_values(self):
        # Odoo's automatic follow-up (triggered chaining, "done & schedule
        # next") is built here; without this it would lose the employee and
        # vanish from their app.
        vals = super()._prepare_next_activity_values()
        if self.ohint_employee_id:
            vals["ohint_employee_id"] = self.ohint_employee_id.id
        return vals
