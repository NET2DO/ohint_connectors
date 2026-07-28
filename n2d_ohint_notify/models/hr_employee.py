from odoo import models

# Field → the notification kind its change represents.
_ASSIGNMENT_FIELDS = ("department_id", "job_id", "parent_id", "work_location_id")
_PROFILE_FIELDS = ("job_title", "work_email", "mobile_phone", "work_phone")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def write(self, vals):
        res = super().write(vals)
        # Skip app-originated writes (the middleware integration user).
        integ = self.env["ohint.notify"].integration_uid()
        if integ and str(self.env.uid) == str(integ):
            return res

        assignment = any(f in vals for f in _ASSIGNMENT_FIELDS)
        profile = any(f in vals for f in _PROFILE_FIELDS)
        if not (assignment or profile):
            return res

        # An assignment change is the more significant event; prefer it.
        msg_key = "back_office.assignment_changed" if assignment else "back_office.profile_updated"
        dispatcher = self.env["ohint.notify"]
        for emp in self:
            dispatcher._dispatch(
                emp,
                "back_office",
                msg_key,
                data={"route": "/notifications/profile/%s" % emp.id},
                dedupe_key="back_office:employee:%s:%s:%s" % (emp.id, msg_key, emp.write_date),
            )
        return res
