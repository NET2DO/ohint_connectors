from datetime import date, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestActivityDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_user = cls.env.ref("base.group_user")
        dash = cls.env.ref("n2d_ohint_activity.group_activity_dashboard")
        cls.company = cls.env.company
        cls.scheduler = cls.env["res.users"].create({
            "name": "Sami Scheduler", "login": "sched.dash", "email": "sched.dash@example.com",
            "groups_id": [(6, 0, [group_user.id, cls.env.ref("base.group_partner_manager").id])]})
        cls.viewer = cls.env["res.users"].create({
            "name": "Dash Viewer", "login": "viewer.dash",
            "company_id": cls.company.id, "company_ids": [(6, 0, [cls.company.id])],
            "groups_id": [(6, 0, [group_user.id, dash.id])]})
        cls.field_rep = cls.env["hr.employee"].create({"name": "Rana Field Rep"})
        cls.rep_user = cls.env["res.users"].create({
            "name": "Omar Office", "login": "office.dash", "groups_id": [(6, 0, [group_user.id])]})
        cls.office_emp = cls.env["hr.employee"].create({"name": "Omar Office", "user_id": cls.rep_user.id})
        cls.partner = cls.env["res.partner"].create({"name": "Dashboard Customer"})
        cls.call = cls.env.ref("mail.mail_activity_data_call")
        cls.Report = cls.env["ohint.activity.report"]

    def _schedule(self, **kw):
        kw.setdefault("activity_type_id", self.call.id)
        return self.partner.with_user(self.scheduler).activity_schedule(**kw)

    def _row(self, activity_id, user=None):
        self.env.flush_all()
        self.env.invalidate_all()
        Report = self.Report.with_user(user) if user else self.Report
        return Report.search([("activity_id", "=", activity_id)])

    def test_open_activity_belongs_to_the_employee_not_the_scheduler(self):
        act = self._schedule(ohint_employee_id=self.field_rep.id, summary="Visit")
        row = self._row(act.id)
        self.assertEqual(len(row), 1)
        self.assertEqual(row.employee_id, self.field_rep)
        self.assertEqual(row.scheduler_id, self.scheduler)
        self.assertTrue(row.by_employee_field)
        self.assertEqual(row.res_model_id.model, "res.partner")
        self.assertEqual(row.source_module_id.name, "base")
        self.assertEqual(row.res_ref, self.partner)

    def test_legacy_activity_falls_back_to_the_employee_of_the_assigned_user(self):
        act = self._schedule(user_id=self.rep_user.id)
        row = self._row(act.id)
        self.assertEqual(row.employee_id, self.office_emp)
        self.assertFalse(row.by_employee_field)

    def test_status_follows_the_due_date(self):
        today = fields.Date.today()
        cases = {"overdue": today - timedelta(days=2), "today": today, "planned": today + timedelta(days=3)}
        for state, deadline in cases.items():
            act = self._schedule(ohint_employee_id=self.field_rep.id, date_deadline=deadline)
            self.assertEqual(self._row(act.id).state, state, state)

    def test_done_is_logged_and_credited_to_the_employee(self):
        act = self._schedule(ohint_employee_id=self.field_rep.id, summary="Collect payment")
        act_id = act.id
        admin = self.env.ref("base.user_admin")
        act.with_user(admin).action_feedback(feedback="collected")
        self.assertFalse(self.env["mail.activity"].with_context(active_test=False).search([("id", "=", act_id)]))
        row = self._row(act_id)
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, "done")
        self.assertEqual(row.employee_id, self.field_rep)
        self.assertEqual(row.scheduler_id, self.scheduler)
        self.assertEqual(row.done_by_id, admin)
        self.assertEqual(row.date_done, fields.Date.context_today(row))

    def test_done_message_names_the_employee_not_the_scheduler(self):
        act = self._schedule(ohint_employee_id=self.field_rep.id)
        act.action_feedback(feedback="ok")
        body = str(self.partner.message_ids[:1].body)
        self.assertIn("Rana Field Rep", body)
        self.assertNotIn("originally assigned to", body)

    def test_a_kept_done_activity_is_counted_once(self):
        keep = self.env["mail.activity.type"].create({"name": "Keep", "keep_done": True})
        act = self._schedule(activity_type_id=keep.id, ohint_employee_id=self.field_rep.id)
        act.action_feedback()
        self.assertFalse(act.active)
        row = self._row(act.id)
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, "done")

    def test_another_companys_activities_are_hidden(self):
        other = self.env["res.company"].create({"name": "Other Co"})
        emp = self.env["hr.employee"].create({"name": "Elsewhere", "company_id": other.id})
        act = self._schedule(ohint_employee_id=emp.id)
        self.assertEqual(self._row(act.id).company_id, other)
        self.assertFalse(self._row(act.id, user=self.viewer))
        mine = self._schedule(ohint_employee_id=self.field_rep.id)
        self.assertTrue(self._row(mine.id, user=self.viewer))

    def test_per_employee_counts(self):
        today = fields.Date.today()
        self._schedule(ohint_employee_id=self.field_rep.id, date_deadline=today - timedelta(days=1))
        self._schedule(ohint_employee_id=self.field_rep.id, date_deadline=today)
        self._schedule(ohint_employee_id=self.field_rep.id, date_deadline=today + timedelta(days=5))
        self._schedule(ohint_employee_id=self.field_rep.id).action_feedback()
        self.env.flush_all()
        groups = self.Report.read_group([("employee_id", "=", self.field_rep.id)], ["state"], ["state"])
        counts = {g["state"]: g["state_count"] for g in groups}
        self.assertEqual(counts.get("overdue"), 1)
        self.assertEqual(counts.get("planned"), 1)
        self.assertEqual(counts.get("done"), 1)
        self.assertGreaterEqual(counts.get("today", 0), 1)

    def test_backfill_reads_the_employee_from_the_app_tag(self):
        msg = self.partner.message_post(
            body="<p>Call done</p><div>— Rana Field Rep via OHINT app</div>",
            subtype_xmlid="mail.mt_activities", mail_activity_type_id=self.call.id)
        self.env["ohint.activity.done"].search([("message_id", "=", msg.id)]).unlink()
        n = self.env["ohint.activity.done"]._backfill_from_chatter()
        self.assertGreaterEqual(n, 1)
        log = self.env["ohint.activity.done"].search([("message_id", "=", msg.id)])
        self.assertEqual(log.employee_id, self.field_rep)
        self.assertTrue(log.backfilled)
        # running it again adds nothing for that message
        self.env["ohint.activity.done"]._backfill_from_chatter()
        self.assertEqual(self.env["ohint.activity.done"].search_count([("message_id", "=", msg.id)]), 1)
