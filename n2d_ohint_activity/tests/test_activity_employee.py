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
