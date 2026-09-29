from datetime import date, timedelta

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestActivityEmployee(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.no_user = cls.env["hr.employee"].create({"name": "Field Rep (no user)"})
        cls.user = cls.env["res.users"].create({"name": "Linked Rep", "login": "linked.rep.ohint"})
        cls.with_user = cls.env["hr.employee"].create({"name": "Linked Rep", "user_id": cls.user.id})
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.call = cls.env.ref("mail.mail_activity_data_call")

    def test_employee_without_user_keeps_the_scheduler_as_user(self):
        act = self.partner.activity_schedule(activity_type_id=self.call.id, ohint_employee_id=self.no_user.id)
        self.assertEqual(act.ohint_employee_id, self.no_user)
        self.assertEqual(act.user_id, self.env.user)

    def test_employee_with_user_fills_assigned_to(self):
        act = self.partner.activity_schedule(activity_type_id=self.call.id, ohint_employee_id=self.with_user.id)
        self.assertEqual(act.user_id, self.user)

    def test_the_employee_wins_over_another_user(self):
        act = self.partner.activity_schedule(
            activity_type_id=self.call.id, ohint_employee_id=self.with_user.id, user_id=self.env.user.id)
        self.assertEqual(act.user_id, self.user)

    def test_the_automatic_follow_up_keeps_the_employee(self):
        nxt_type = self.env["mail.activity.type"].create({"name": "Follow up", "delay_count": 2})
        trig = self.env["mail.activity.type"].create(
            {"name": "Visit", "chaining_type": "trigger", "triggered_next_type_id": nxt_type.id})
        act = self.partner.activity_schedule(
            activity_type_id=trig.id, ohint_employee_id=self.no_user.id,
            date_deadline=date.today() + timedelta(days=1))
        act.action_feedback(feedback="done")
        nxt = self.env["mail.activity"].search(
            [("res_model", "=", "res.partner"), ("res_id", "=", self.partner.id),
             ("activity_type_id", "=", nxt_type.id)])
        self.assertEqual(len(nxt), 1)
        self.assertEqual(nxt.ohint_employee_id, self.no_user)

    def test_the_schedule_dialog_assigns_the_employee(self):
        wiz = self.env["mail.activity.schedule"].with_context(
            active_model="res.partner", active_ids=[self.partner.id]).create({
                "res_model": "res.partner", "res_ids": str([self.partner.id]),
                "activity_type_id": self.call.id, "ohint_employee_id": self.no_user.id,
            })
        wiz.action_schedule_activities()
        act = self.partner.activity_ids.filtered(lambda a: a.ohint_employee_id == self.no_user)
        self.assertEqual(len(act), 1)

    def test_the_schedule_dialog_without_employee_is_unchanged(self):
        wiz = self.env["mail.activity.schedule"].with_context(
            active_model="res.partner", active_ids=[self.partner.id]).create({
                "res_model": "res.partner", "res_ids": str([self.partner.id]),
                "activity_type_id": self.call.id,
            })
        wiz.action_schedule_activities()
        self.assertFalse(self.partner.activity_ids.ohint_employee_id)

    def test_integration_reads_and_acts_on_a_private_task_activity(self):
        """A task without a project is private: only its assignee can read
        it. The integration methods still reach its activities."""
        if "project.task" not in self.env:
            self.skipTest("project is not installed")
        worker = self.env["res.users"].create({"name": "Worker", "login": "worker.ohint", "groups_id": [(6, 0, [
            self.env.ref("base.group_user").id, self.env.ref("project.group_project_user").id])]})
        task = self.env["project.task"].with_user(worker).create({"name": "Private to-do", "user_ids": [(6, 0, [worker.id])]})
        act = task.with_user(worker).activity_schedule(activity_type_id=self.call.id, ohint_employee_id=self.no_user.id)
        admin = self.env.ref("base.user_admin")
        A = self.env["mail.activity"].with_user(admin)
        rows = A.ohint_search_read([("ohint_employee_id", "=", self.no_user.id)], ["id", "res_model"])
        self.assertIn(act.id, [r["id"] for r in rows])
        self.assertEqual(A.ohint_search_count([("id", "=", act.id)]), 1)
        new_ids = A.ohint_schedule("project.task", task.id, {"activity_type_id": self.call.id, "ohint_employee_id": self.no_user.id})
        self.assertEqual(len(new_ids), 1)
        att = A.ohint_create_attachment("project.task", task.id, "photo.txt", "aGk=")
        A.browse(act.id).ohint_feedback(feedback="done", attachment_ids=[att])
        self.assertFalse(self.env["mail.activity"].search([("id", "=", act.id)]))

    def test_only_the_integration_account_may_call(self):
        plain = self.env["res.users"].create({"name": "Plain", "login": "plain.ohint"})
        from odoo.exceptions import AccessError
        with self.assertRaises(AccessError):
            self.env["mail.activity"].with_user(plain).ohint_search_read([], ["id"])

    def test_the_app_can_only_edit_date_summary_and_note(self):
        act = self.partner.activity_schedule(activity_type_id=self.call.id, ohint_employee_id=self.no_user.id)
        from odoo.exceptions import AccessError
        with self.assertRaises(AccessError):
            act.with_user(self.env.ref("base.user_admin")).ohint_write({"user_id": self.user.id})
