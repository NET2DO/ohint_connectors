import base64
import binascii
import hmac
import json
import logging
import time
from hashlib import sha256

from psycopg2 import IntegrityError

from odoo import SUPERUSER_ID, http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Ticket format: "v1.<b64url(payload_json)>.<b64url(hmac_sha256)>"
TICKET_VERSION = "v1"

# A ticket is redeemed within a redirect or two of being minted. Anything
# longer is a stolen ticket, not a slow browser.
MAX_TTL_SECONDS = 120

SECRET_PARAM = "ohint_connect.secret"


def _b64url_decode(segment):
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


class OhintConnect(http.Controller):
    """One-click sign-in from the OHINT console.

    Every failure path returns the same generic message to the browser; the
    reason is logged instead. Telling an attacker whether a ticket was expired,
    replayed, or badly signed hands them a probing oracle.
    """

    @http.route(
        "/ohint/connect",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        sitemap=False,
    )
    def connect(self, token=None, **kwargs):
        remote = request.httprequest.remote_addr
        try:
            uid, operator, jti = self._verify(token)
        except _TicketError as err:
            _logger.warning(
                "OHINT Connect REJECTED (%s) db=%s remote=%s", err, request.db, remote
            )
            return self._refuse("This sign-in link is not valid or has expired.")

        user = request.env["res.users"].sudo().browse(uid)

        # Single-use, enforced by the unique index rather than a prior read: two
        # concurrent redemptions of one ticket must not both succeed.
        try:
            with request.env.cr.savepoint():
                request.env["ohint.connect.ticket"].sudo().create(
                    {"jti": jti, "user_id": user.id, "operator": operator, "remote_addr": remote}
                )
                # The ORM defers the INSERT to the next flush. Without forcing it
                # here the unique violation would surface after the redirect has
                # already been handed to the browser — i.e. too late to refuse.
                # cr.flush() rather than env.flush_all(): the latter is 16.0+.
                request.env.cr.flush()
        except IntegrityError:
            _logger.warning(
                "OHINT Connect REPLAY blocked jti=%s db=%s operator=%s remote=%s",
                jti, request.db, operator, remote,
            )
            return self._refuse("This sign-in link has already been used.")

        # Establish the session without a password (Odoo 15 approach).
        request.session.logout(keep_db=True)
        request.session.uid = user.id
        request.session.login = user.login
        request.session.db = request.db
        request.session.context = dict(
            request.env(user=user.id)["res.users"].context_get()
        )

        _logger.info(
            "OHINT Connect OK db=%s user=%s(%s) operator=%s remote=%s",
            request.db, user.login, user.id, operator, remote,
        )
        return request.redirect("/web")

    def _refuse(self, message):
        """Plain 403.

        Deliberately not a QWeb template: this path must work even when the
        database's assets or views are in a bad state, which is exactly when a
        rescue sign-in is most likely to be attempted.
        """
        html = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Sign-in link rejected</title></head>"
            "<body style=\"font-family:system-ui,sans-serif;max-width:32rem;"
            "margin:4rem auto;padding:0 1rem;color:#222\">"
            "<h1 style='font-size:1.25rem'>Sign-in link rejected</h1>"
            f"<p>{message}</p>"
            "<p style='color:#666;font-size:.9rem'>Connect links are valid once "
            "and for a short time. Generate a new one from the OHINT console.</p>"
            "</body></html>"
        )
        response = request.make_response(
            html,
            headers=[("Content-Type", "text/html; charset=utf-8"), ("Cache-Control", "no-store")],
        )
        response.status_code = 403
        return response

    def _verify(self, token):
        """Return (uid, operator, jti) or raise _TicketError."""
        if not token:
            raise _TicketError("no token")

        parts = token.split(".")
        if len(parts) != 3 or parts[0] != TICKET_VERSION:
            raise _TicketError("malformed token")
        _version, payload_b64, sig_b64 = parts

        secret = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param(SECRET_PARAM)
        )
        if not secret:
            # Never fall back to an unsigned path — an unconfigured database
            # must be closed, not open.
            raise _TicketError("connect secret not configured")

        expected = hmac.new(
            secret.encode(), f"{TICKET_VERSION}.{payload_b64}".encode(), sha256
        ).digest()
        try:
            provided = _b64url_decode(sig_b64)
        except (binascii.Error, ValueError):
            raise _TicketError("undecodable signature")
        if not hmac.compare_digest(expected, provided):
            raise _TicketError("bad signature")

        try:
            payload = json.loads(_b64url_decode(payload_b64))
        except (binascii.Error, ValueError):
            raise _TicketError("undecodable payload")

        # Bind to THIS database, or a ticket minted for tenant A would open
        # tenant B for anyone who can reach both hosts.
        if payload.get("db") != request.db:
            raise _TicketError("database mismatch")

        exp = payload.get("exp")
        if not isinstance(exp, int):
            raise _TicketError("no expiry")
        now = int(time.time())
        if exp < now:
            raise _TicketError("expired")
        if exp - now > MAX_TTL_SECONDS:
            # A far-future expiry means the middleware was compromised or
            # misconfigured; refuse rather than honour a long-lived skeleton key.
            raise _TicketError("expiry too far out")

        jti = payload.get("jti")
        if not jti or not isinstance(jti, str):
            raise _TicketError("no jti")

        uid = payload.get("uid")
        if not isinstance(uid, int) or uid <= 0:
            raise _TicketError("no uid")
        if uid == SUPERUSER_ID:
            # OdooBot is the unrestricted internal identity; nobody signs in as it.
            raise _TicketError("superuser refused")

        user = request.env["res.users"].sudo().browse(uid).exists()
        if not user:
            raise _TicketError("unknown user")
        if not user.active:
            raise _TicketError("inactive user")
        if user.share:
            # Portal/public accounts are customers of the customer; the console
            # has no business wearing them.
            raise _TicketError("non-internal user refused")
        if payload.get("login") != user.login:
            raise _TicketError("login/uid mismatch")

        return uid, payload.get("op") or "unknown", jti


class _TicketError(Exception):
    pass
