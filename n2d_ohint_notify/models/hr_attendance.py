from odoo import models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def write(self, vals):
        res = super().write(vals)
        if not ({"check_in", "check_out"} & set(vals)):
            return res
        # Only notify for genuine back-office corrections. The app's own
        # check-in/out also writes these fields (via the middleware integration
        # user); without a configured integration uid we cannot tell the two
        # apart, so we stay silent to avoid false "attendance corrected" pings.
        integ = self.env["ohint.notify"].integration_uid()
        if not integ or str(self.env.uid) == str(integ):
            return res

        dispatcher = self.env["ohint.notify"]
        for att in self:
            if not att.employee_id:
                continue
            dispatcher._dispatch(
                att.employee_id,
                "back_office",
                "back_office.attendance_edited",
                data={"route": "/notifications/attendance/%s" % att.id},
                dedupe_key="back_office:attendance:%s:%s" % (att.id, att.write_date),
            )
        return res
