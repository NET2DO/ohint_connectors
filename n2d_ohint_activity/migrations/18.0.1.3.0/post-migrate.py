from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # The done log is new in 1.3.0: rebuild past Done rows from the chatter.
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ohint.activity.done"]._backfill_from_chatter()
