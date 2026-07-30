# ohint_connectors — branch `16.0`

Odoo addons for OHINT integrations, backported to **Odoo 16.0** for the `n2d16`
fleet (`odoo:16.0`, ~98 databases, `dbfilter = ^%h$` so database name == hostname).

Other branches: `main` = 19.0, `18` = 18.0.

## What is on this branch

| Module | Version | Notes |
|---|---|---|
| `n2d_geofence_site` | 16.0.1.0.0 | Additive overlay on `hr_attendance_geolocation` |
| `n2d_ohint_notify`  | 16.0.1.0.0 | Byte-identical to 19.0 apart from the manifest version |

## What is deliberately NOT on this branch

**`hr_attendance_geolocation` is not shipped here.** On `n2d16` that module is
already installed in ~30 live customer databases, served from `/mnt/ohint`
(repo `hintegration/ohint`, branch `feature/16.0/attendance_history`).
Shipping a second copy under a different `addons_path` entry would create a
duplicate module name, and Odoo resolves duplicates by path order — which would
silently swap the code serving those live databases. It stays owned by
`hintegration/ohint`; this branch only adds on top of it.

`n2d_sfa_identity`, `n2d_sfa_visit`, `n2d_ohint_connect` and `n2d_ohint_pos` are
not ported yet — see "Pending" below.

## Design: why `n2d_geofence_site` is an overlay

The `hr_attendance_geolocation` build on `n2d16` already provides
`company.location`, `employee.visit`, `hr.employee.site_ids` / `traceable` /
`traceable_type`, and the `hr.attendance` geo fields — including the m2m relation
table `employee_site_rel(employee, site)`, which matches what this module expects.

Three things are missing or wrong for the OHINT middleware:

| Middleware expects | Fleet databases have | Fixed by |
|---|---|---|
| `employee.visit.employee_id` | missing | added by this module |
| `employee.visit.check_in` | missing | added by this module |
| `company.location.longitude` | `langitude` (typo) | added + backfilled by `post_init_hook` |

Without `employee_id` and `check_in`, a GPS waypoint can never be written at all
(`internal/odoo/hr.go` sets both on create and reads back `order: "check_in asc"`).
This is the same defect that was fixed on the Odoo 15 build for future-foam.

Everything else this module declares already exists with a matching definition,
so installing it adds three columns and changes no existing data. The
`post_init_hook` copies `langitude` → `longitude` only where the new column is
still NULL, so it is safe to re-run on every upgrade.

`n2d_geofence_site` (rather than a patch to the base module) is also what
`internal/odoo/diagnose.go` looks for: it verifies `company.location` via
`ir.module.module` state for module name `n2d_geofence_site`, so a tenant without
this module installed reports the geofence add-on as missing even when the model
exists.

## Middleware limits on Odoo 16

Two middleware paths are **not** version-portable and no addon can fix them:

- `hr.version` (`internal/odoo/attendance_reminder.go`) is Odoo 19 only. Odoo 16
  keeps the working schedule on `hr.contract` / `hr.employee.resource_calendar_id`.
  Checkout reminders and schedule-end resolution fail on a v16 tenant until the
  connector branches on version.
- `pos.order.sync_from_ui` (`internal/odoo/pos.go`) is Odoo 18+. Odoo 16 uses
  `create_from_ui` with a different payload and no `uuid` fields. POS is not
  usable on v16 without connector work — porting `n2d_ohint_pos` alone is not enough.

`groups_id` vs `group_ids` is already handled by `groupsFieldCandidates()`.

## Pending

- `n2d_sfa_identity`, `n2d_sfa_visit` — Odoo 15 copies exist at
  `hintegration/odoo-custom-addons` branch `15.1`; port is mostly a manifest bump.
- `n2d_ohint_connect` — the hard one. Odoo 16 has none of
  `request.session.finalize()` (17+), the `/odoo` backend route (18+), or
  `models.Constraint` (19). Needs a v16 session-establishment path and
  `_sql_constraints`.
- `n2d_ohint_pos` — blocked on the connector's `create_from_ui` branch above.
