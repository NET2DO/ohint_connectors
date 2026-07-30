from . import models

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    _backfill_longitude(cr)
    _backfill_visit_columns(cr)


def _backfill_longitude(cr):
    """Backfill company.location.longitude from the legacy `langitude` column.

    The `hr_attendance_geolocation` build deployed across the n2d16 fleet spells
    the column `langitude` (a typo carried since the Odoo 13 original). The OHINT
    middleware reads `longitude`, so this module adds that field — but adding a
    field leaves it NULL on every row that already exists, which would silently
    hand the app sites with no longitude.

    Copy the legacy value once, only where the new column is still empty, so the
    hook stays safe to re-run on every module upgrade. The legacy column is left
    in place: the base module still declares it, and dropping it here would break
    that module's own views.
    """
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'company_location' AND column_name = 'langitude'
        """
    )
    if not cr.fetchone():
        # Fresh database, or a build without the typo — nothing to migrate.
        return

    cr.execute(
        """
        UPDATE company_location
           SET longitude = langitude
         WHERE longitude IS NULL
           AND langitude IS NOT NULL
        """
    )
    if cr.rowcount:
        _logger.info(
            "n2d_geofence_site: backfilled longitude from langitude on %s "
            "company.location row(s)",
            cr.rowcount,
        )


def _backfill_visit_columns(cr):
    """Derive employee_id / check_in for waypoints recorded before those existed.

    Both columns are added by this module, so every visit already in the database
    starts out NULL on them — which would leave a customer's whole waypoint
    history invisible to the app (it reads visits ordered by check_in). Both
    values are recoverable from the attendance the visit already points at, and
    from the visit's own `date`.

    Only NULLs are filled, so nothing recorded by the app is ever overwritten and
    the hook stays safe to re-run on upgrade.
    """
    cr.execute(
        """
        UPDATE employee_visit v
           SET employee_id = a.employee_id
          FROM hr_attendance a
         WHERE v.attend_id = a.id
           AND v.employee_id IS NULL
        """
    )
    filled_emp = cr.rowcount

    cr.execute(
        """
        UPDATE employee_visit
           SET check_in = date
         WHERE check_in IS NULL
           AND date IS NOT NULL
        """
    )
    if filled_emp or cr.rowcount:
        _logger.info(
            "n2d_geofence_site: backfilled employee_id on %s and check_in on %s "
            "employee.visit row(s)",
            filled_emp, cr.rowcount,
        )
