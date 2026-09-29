from odoo import api, fields, models


class MailActivitySchedule(models.TransientModel):
    """Odoo 18's "Schedule Activity" dialog (opened from the chatter) is this
    wizard, not the mail.activity form; the employee has to be offered here."""

    _inherit = "mail.activity.schedule"

    ohint_employee_id = fields.Many2one(
        "hr.employee",
        string="Assign to employee",
        help="The employee who does this activity in the OHINT app. Use it for "
        "employees without an Odoo user.",
    )

    @api.onchange("ohint_employee_id")
    def _onchange_ohint_employee_id(self):
        if self.ohint_employee_id.user_id:
            self.activity_user_id = self.ohint_employee_id.user_id

    def _action_schedule_activities(self):
        # The core call passes a fixed set of values to activity_schedule; a
        # context default is how the employee reaches the created activities
        # (mail.activity is the only model with this field).
        if self.ohint_employee_id:
            self = self.with_context(default_ohint_employee_id=self.ohint_employee_id.id)
        return super(MailActivitySchedule, self)._action_schedule_activities()

    def action_schedule_activities_done_and_schedule(self):
        # "Done & Schedule Next" reopens the dialog: keep the same employee.
        action = super().action_schedule_activities_done_and_schedule()
        if isinstance(action, dict) and self.ohint_employee_id:
            action.setdefault("context", {})["default_ohint_employee_id"] = self.ohint_employee_id.id
        return action
