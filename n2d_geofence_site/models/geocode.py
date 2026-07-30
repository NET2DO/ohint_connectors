"""Safe reverse-geocoding for the base module's stored address fields.

`hr_attendance_geolocation` declares `check_in_address` / `check_out_address` on
both `hr.attendance` and `employee.visit` as STORED computed fields whose compute
calls Nominatim over the public internet, once per record, with no error handling.

That makes any module install or upgrade on a database with attendance history a
hazard: Odoo recomputes the stored field for every row, each row becomes an
outbound HTTPS request, and the first failure raises `GeocoderUnavailable`, which
rolls back the whole install. Nominatim's usage policy is one request per second,
so on a few hundred rows failure is the expected outcome, not the edge case.

The overrides here keep the feature for interactive use and make it impossible
for it to break an install:

* a compute over more than `BULK_THRESHOLD` records is treated as a recompute
  triggered by an install/upgrade — no network call is made at all;
* any geocoder error is swallowed;
* in both cases the value already stored in the column is written back
  unchanged, so no customer's existing addresses are lost.
"""

import logging

_logger = logging.getLogger(__name__)

# Beyond this many records in one compute call, assume a bulk recompute
# (install/upgrade) rather than a user editing a record.
BULK_THRESHOLD = 5

# Nominatim's own guidance is ~1 req/s; keep the per-call wait short so an
# interactive save is never held up for long.
GEOCODE_TIMEOUT = 5

_geolocator = None


def _locator():
    global _geolocator
    if _geolocator is None:
        from geopy.geocoders import Nominatim

        _geolocator = Nominatim(user_agent="OHint")
    return _geolocator


def _stored(records, addr_field):
    """Read the address column straight from the table, bypassing the compute.

    The column is not guaranteed to be there. `hr_attendance_geolocation` is
    deployed at different revisions across the fleet, and the databases running
    an older one have the field in code but no column in the table until that
    module is next upgraded — so probe before selecting, or the failed statement
    aborts the surrounding transaction.
    """
    real_ids = [r.id for r in records if isinstance(r.id, int)]
    if not real_ids:
        return {}
    cr = records.env.cr
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        " WHERE table_name = %s AND column_name = %s",
        (records._table, addr_field),
    )
    if not cr.fetchone():
        return {}
    cr.execute(
        'SELECT id, "%s" FROM "%s" WHERE id IN %%s' % (addr_field, records._table),
        (tuple(real_ids),),
    )
    return dict(cr.fetchall())


def apply(records, lat_field, lon_field, addr_field):
    if addr_field not in records._fields:
        # Older builds of the base module on the fleet don't carry the address
        # field at all; there is then nothing for this compute to write.
        return
    existing = _stored(records, addr_field)
    bulk = len(records) > BULK_THRESHOLD
    if bulk:
        _logger.info(
            "n2d_geofence_site: %s recompute over %s records — keeping stored "
            "values instead of reverse-geocoding each one",
            addr_field, len(records),
        )
    for rec in records:
        current = existing.get(rec.id) if isinstance(rec.id, int) else False
        lat, lon = rec[lat_field], rec[lon_field]
        if bulk or not (lat or lon):
            rec[addr_field] = current
            continue
        try:
            location = _locator().reverse((lat, lon), timeout=GEOCODE_TIMEOUT)
        except Exception as exc:  # noqa: BLE001 — never let geocoding break a write
            _logger.debug("n2d_geofence_site: reverse geocode failed: %s", exc)
            rec[addr_field] = current
            continue
        rec[addr_field] = str(location) if location else current
