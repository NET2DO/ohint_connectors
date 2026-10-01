from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _action_done(self, feedback=False, attachment_ids=None):
        # Log before super: Odoo deletes most activities once they are done.
        self.env["ohint.activity.done"]._log_done(self.filtered("active"), feedback)
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)
