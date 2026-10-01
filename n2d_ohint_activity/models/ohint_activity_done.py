import re

from odoo import api, fields, models

# The OHINT middleware ends every done note with "— <employee> via OHINT app".
_APP_TAG = re.compile(r"—\s*([^<\n]+?)\s+via OHINT app")
_ASSIGNED = re.compile(r"originally assigned to\s*(?:<[^>]+>\s*)*([^<]+?)\s*<")


class OhintActivityDone(models.Model):
    """One row per completed activity.

    Odoo deletes a done activity (unless its type keeps done ones) and keeps
    only a chatter message, which does not say which employee it belonged to.
    This log is written at completion so the dashboard can count Done per
    employee, crediting the employee who owned the activity, never the
    scheduler or whoever clicked Done.
    """

    _name = "ohint.activity.done"
    _description = "Completed activity (OHINT dashboard)"
    _order = "date_done desc, id desc"

    activity_id = fields.Integer("Activity ID", index=True)
    activity_type_id = fields.Many2one("mail.activity.type", "Activity Type", ondelete="set null")
    summary = fields.Char()
    res_model_id = fields.Many2one("ir.model", "Document Model", ondelete="cascade")
    res_model = fields.Char("Related Model", index=True)
    res_id = fields.Integer("Related ID", index=True)
    res_name = fields.Char("Related Record")
    user_id = fields.Many2one("res.users", "Assigned User", ondelete="set null")
    ohint_employee_id = fields.Many2one("hr.employee", "Assign to employee", ondelete="set null")
    employee_id = fields.Many2one("hr.employee", "Employee", index=True, ondelete="set null",
                                  help="Who the activity is credited to: the 'Assign to employee', "
                                  "else the employee of the assigned user.")
    scheduler_id = fields.Many2one("res.users", "Scheduled by", ondelete="set null")
    done_by_id = fields.Many2one("res.users", "Marked done by", ondelete="set null")
    date_deadline = fields.Date("Due Date")
    date_done = fields.Date("Done Date", index=True)
    feedback = fields.Text()
    company_id = fields.Many2one("res.company", index=True, ondelete="set null")
    message_id = fields.Many2one("mail.message", ondelete="set null", index=True)
    backfilled = fields.Boolean(help="Rebuilt from the chatter at install; the due date and "
                                "the scheduler are unknown.")

    # -- shared rules (the SQL report applies the same ones) --------------

    @api.model
    def _employee_of_user(self, user):
        if not user:
            return self.env["hr.employee"]
        return self.env["hr.employee"].sudo().with_context(active_test=False).search(
            [("user_id", "=", user.id)], order="active desc, id", limit=1)

    @api.model
    def _scheduler(self, activity):
        # OdooBot/__system__ (id 1) creates automated activities; the assignee
        # is then the closest thing to a scheduler.
        return activity.create_uid if activity.create_uid.id != 1 else activity.user_id

    @api.model
    def _company(self, employee, user):
        return employee.company_id or user.company_id

    # -- capture ----------------------------------------------------------

    @api.model
    def _log_done(self, activities, feedback=False):
        today = fields.Date.context_today(self)
        vals = []
        for act in activities.sudo():
            employee = act.ohint_employee_id or self._employee_of_user(act.user_id)
            vals.append({
                "activity_id": act.id,
                "activity_type_id": act.activity_type_id.id,
                "summary": act.summary,
                "res_model_id": act.res_model_id.id,
                "res_model": act.res_model,
                "res_id": act.res_id,
                "res_name": act.res_name,
                "user_id": act.user_id.id,
                "ohint_employee_id": act.ohint_employee_id.id,
                "employee_id": employee.id,
                "scheduler_id": self._scheduler(act).id,
                "done_by_id": self.env.uid,
                "date_deadline": act.date_deadline,
                "date_done": today,
                "feedback": feedback or False,
                "company_id": self._company(employee, act.user_id).id,
            })
        return self.sudo().create(vals)

    # -- history ----------------------------------------------------------

    @api.model
    def _backfill_from_chatter(self):
        """Rebuild Done rows from the 'activity done' chatter messages posted
        before this log existed. The employee is read from the message: the
        OHINT app tag, else 'originally assigned to <user>', else its author."""
        Message = self.env["mail.message"].sudo()
        subtype = self.env.ref("mail.mt_activities", raise_if_not_found=False)
        if not subtype:
            return 0
        done = set(self.sudo().search([("message_id", "!=", False)]).mapped("message_id").ids)
        msgs = Message.search([("subtype_id", "=", subtype.id), ("mail_activity_type_id", "!=", False),
                               ("model", "!=", False), ("res_id", "!=", 0)], order="id")
        Employee = self.env["hr.employee"].sudo().with_context(active_test=False)
        Users = self.env["res.users"].sudo().with_context(active_test=False)
        Activity = self.env["mail.activity"].sudo().with_context(active_test=False)
        models_by_name = {}
        vals = []
        for msg in msgs:
            if msg.id in done:
                continue
            day = msg.date.date()
            # An activity type that keeps done ones is still in mail.activity
            # (archived); the report shows it from there.
            if Activity.search_count([("active", "=", False), ("res_model", "=", msg.model),
                                      ("res_id", "=", msg.res_id),
                                      ("activity_type_id", "=", msg.mail_activity_type_id.id),
                                      ("date_done", "=", day)]):
                continue
            body = str(msg.body or "")
            author = Users.search([("partner_id", "=", msg.author_id.id)], limit=1) if msg.author_id else Users
            employee = Employee
            user = Users
            m = _APP_TAG.search(body)
            if m:
                found = Employee.search([("name", "=", m.group(1).strip())])
                employee = found if len(found) == 1 else Employee
            if not employee:
                m = _ASSIGNED.search(body)
                if m:
                    found = Users.search([("name", "=", m.group(1).strip())])
                    user = found if len(found) == 1 else Users
                user = user or author
                employee = self._employee_of_user(user)
            if msg.model not in models_by_name:
                models_by_name[msg.model] = self.env["ir.model"]._get_id(msg.model) if msg.model in self.env else False
            if not models_by_name[msg.model]:
                continue
            vals.append({
                "activity_type_id": msg.mail_activity_type_id.id,
                "res_model_id": models_by_name[msg.model],
                "res_model": msg.model,
                "res_id": msg.res_id,
                "res_name": msg.record_name,
                "user_id": (user or employee.user_id).id,
                "employee_id": employee.id,
                "done_by_id": author.id,
                "date_done": day,
                "company_id": self._company(employee, user or author).id,
                "message_id": msg.id,
                "backfilled": True,
            })
        self.sudo().create(vals)
        return len(vals)
