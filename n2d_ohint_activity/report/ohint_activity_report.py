from odoo import api, fields, models, tools

STATES = [("overdue", "Overdue"), ("today", "Today"), ("planned", "Planned"), ("done", "Done")]


class OhintActivityReport(models.Model):
    """Every activity, open or done, one row each, computed live by SQL.

    Open (and archived 'keep done') rows come from mail_activity; done rows
    from ohint.activity.done. Ownership follows n2d_ohint_activity: the
    employee is 'Assign to employee' when set, else the employee of the
    assigned user, and the scheduler is only 'Created by'.

    The view is read by SQL, so it is NOT limited by the access rules of the
    related records (a private task's activity is listed). Only the
    Activities Dashboard group can open it, per company.
    """

    _name = "ohint.activity.report"
    _description = "Activities Dashboard"
    _auto = False
    _order = "activity_date desc, id desc"
    _rec_name = "summary"

    activity_id = fields.Integer("Activity ID", readonly=True)
    activity_type_id = fields.Many2one("mail.activity.type", "Activity Type", readonly=True)
    summary = fields.Char(readonly=True)
    scheduler_id = fields.Many2one("res.users", "Created by", readonly=True)
    user_id = fields.Many2one("res.users", "Assigned User", readonly=True)
    employee_id = fields.Many2one("hr.employee", "Employee", readonly=True)
    by_employee_field = fields.Boolean("Via 'Assign to employee'", readonly=True)
    res_model_id = fields.Many2one("ir.model", "Source", readonly=True)
    source_module_id = fields.Many2one("ir.module.module", "Source Module", readonly=True)
    res_model = fields.Char("Related Model", readonly=True)
    res_id = fields.Integer("Related ID", readonly=True)
    res_name = fields.Char("Related Record", readonly=True)
    state = fields.Selection(STATES, "Status", readonly=True)
    date_deadline = fields.Date("Due Date", readonly=True)
    date_done = fields.Date("Done Date", readonly=True)
    activity_date = fields.Date("Date", readonly=True, help="Done date for done activities, due date otherwise.")
    done_by_id = fields.Many2one("res.users", "Marked done by", readonly=True)
    company_id = fields.Many2one("res.company", "Company", readonly=True)
    res_ref = fields.Reference(selection="_selection_res_ref", string="Related Document",
                               compute="_compute_res_ref")

    @api.model
    def _selection_res_ref(self):
        return [(m.model, m.name) for m in self.env["ir.model"].sudo().search([])]

    @api.depends("res_model", "res_id")
    def _compute_res_ref(self):
        for rec in self:
            ok = rec.res_model in self.env and rec.res_id
            rec.res_ref = f"{rec.res_model},{rec.res_id}" if ok else False

    def action_open_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "views": [(False, "form")],
            "target": "current",
        }

    @property
    def _table_query(self):
        return """
            WITH emp_of_user AS (
                SELECT DISTINCT ON (user_id) user_id, id AS employee_id, company_id
                  FROM hr_employee
                 WHERE user_id IS NOT NULL
              ORDER BY user_id, active DESC, id
            ), module_of_model AS (
                SELECT DISTINCT ON (d.res_id) d.res_id AS model_id, m.id AS module_id
                  FROM ir_model_data d
                  JOIN ir_module_module m ON m.name = d.module
                 WHERE d.model = 'ir.model'
              ORDER BY d.res_id, d.id
            ), rows AS (
                SELECT a.id * 2 AS id,
                       a.id AS activity_id,
                       a.activity_type_id,
                       a.summary,
                       CASE WHEN a.create_uid = 1 THEN a.user_id ELSE a.create_uid END AS scheduler_id,
                       a.user_id,
                       COALESCE(a.ohint_employee_id, eu.employee_id) AS employee_id,
                       a.ohint_employee_id IS NOT NULL AS by_employee_field,
                       a.res_model_id,
                       a.res_model,
                       a.res_id,
                       a.res_name,
                       CASE WHEN NOT a.active THEN 'done'
                            WHEN a.date_deadline < CURRENT_DATE THEN 'overdue'
                            WHEN a.date_deadline = CURRENT_DATE THEN 'today'
                            ELSE 'planned' END AS state,
                       a.date_deadline,
                       a.date_done,
                       NULL::integer AS done_by_id,
                       COALESCE(e.company_id, eu.company_id, u.company_id) AS company_id
                  FROM mail_activity a
             LEFT JOIN hr_employee e ON e.id = a.ohint_employee_id
             LEFT JOIN emp_of_user eu ON eu.user_id = a.user_id AND a.ohint_employee_id IS NULL
             LEFT JOIN res_users u ON u.id = a.user_id
                 WHERE a.active
                    OR NOT EXISTS (SELECT 1 FROM ohint_activity_done d WHERE d.activity_id = a.id)
             UNION ALL
                SELECT d.id * 2 + 1,
                       d.activity_id,
                       d.activity_type_id,
                       d.summary,
                       d.scheduler_id,
                       d.user_id,
                       d.employee_id,
                       d.ohint_employee_id IS NOT NULL,
                       d.res_model_id,
                       d.res_model,
                       d.res_id,
                       d.res_name,
                       'done',
                       d.date_deadline,
                       d.date_done,
                       d.done_by_id,
                       d.company_id
                  FROM ohint_activity_done d
            )
            SELECT r.*,
                   CASE WHEN r.state = 'done' THEN r.date_done ELSE r.date_deadline END AS activity_date,
                   mm.module_id AS source_module_id
              FROM rows r
         LEFT JOIN module_of_model mm ON mm.model_id = r.res_model_id
        """
