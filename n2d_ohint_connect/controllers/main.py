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
            return request.render(
                "web.http_error",
                {"status_code": "403", "status_message": "This sign-in link is not valid."},
                status=403,
            )

        user = request.env["res.users"].sudo().browse(uid)

        # Single-use, enforced by the unique index rather than a prior read: two
        # concurrent redemptions of one ticket must not both succeed.
        try:
            with request.env.cr.savepoint():
                request.env["ohint.connect.ticket"].sudo().create(
                    {"jti": jti, "user_id": user.id, "operator": operator, "remote_addr": remote}
                )
        except IntegrityError:
            _logger.warning(
                "OHINT Connect REPLAY blocked jti=%s db=%s operator=%s remote=%s",
                jti, request.db, operator, remote,
            )
            return request.render(
                "web.http_error",
                {"status_code": "403", "status_message": "This sign-in link has already been used."},
                status=403,
            )

        # Establish the session without a password. finalize() is Odoo's own
        # post-MFA path: it stamps db/login/uid/context and the session token.
        request.session.logout(keep_db=True)
        request.session["pre_login"] = user.login
        request.session["pre_uid"] = user.id
        request.session.finalize(request.env)

        _logger.info(
            "OHINT Connect OK db=%s user=%s(%s) operator=%s remote=%s",
            request.db, user.login, user.id, operator, remote,
        )
        return request.redirect("/odoo")

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
