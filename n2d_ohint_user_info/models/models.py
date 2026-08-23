# -*- coding: utf-8 -*-

from odoo import models, http, fields, api, SUPERUSER_ID, _
import logging
from odoo.http import request, route

_logger = logging.getLogger(__name__)

class User(models.Model):
    _inherit = 'res.users'

    device_id = fields.Char('Device ID')


class UserLogin(http.Controller):

    @route('/web/session/authenticate', type="json", auth='public')
    def authenticate(self, db, login, password):
        request.session.authenticate(db, login, password)
        user = request.env.user
        session_info = request.env["ir.http"].session_info()
        session_info["device_id"] = user.device_id
        return session_info