from odoo import models

_APPROVED = "validate"
_REFUSED = "refuse"


class HrLeave(models.Model):
    _inherit = "hr.leave"

    def write(self, vals):
        res = super().write(vals)
        new_state = vals.get("state")
        if new_state in (_APPROVED, _REFUSED):
            dispatcher = self.env["ohint.notify"]
            msg_key = "hr_leave.approved" if new_state == _APPROVED else "hr_leave.refused"
            for leave in self:
                if not leave.employee_id:
                    continue
                dispatcher._dispatch(
                    leave.employee_id,
                    "hr_leave",
                    msg_key,
                    args={"type": leave.holiday_status_id.name or ""},
                    data={"route": "/notifications/leave/%s" % leave.id},
                    dedupe_key="hr_leave:%s:%s" % (leave.id, new_state),
                )
        return res
