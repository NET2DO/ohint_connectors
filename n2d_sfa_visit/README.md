# N2D SFA Field Visit (`n2d_sfa_visit`)

Customer-anchored field-sales visits with **server-side geofence proof**.

A `sfa.visit` is a **standalone** record: it is *not* an extension of
`employee.visit` and does **not** require an open `hr.attendance` punch. A
salesperson logs a visit against a customer (`res.partner`); the client captures
the check-in geolocation, and Odoo recomputes the distance to the customer and
the geofence verdict **server-side** so a client cannot fake an on-site result.

## Key fields (`sfa.visit`)

| Field | Notes |
|---|---|
| `partner_id` | **Required** customer. Geofence is measured to its `partner_latitude/longitude`. |
| `user_id` | Salesperson, defaults to current user. |
| `check_in` / `check_out` | Datetime. |
| `check_in_latitude/longitude`, `check_out_*` | `digits="Location"`, captured client-side. |
| `check_in_map` / `check_out_map` | Computed Google Maps URL (reuses `hr_attendance_geolocation` pattern). |
| `purpose` | sales / collection / survey / delivery / other. |
| `outcome` | success / no_contact / rescheduled / refused. |
| `geofence_radius_m` | Config, default **150** m. |
| `distance_m` | **Stored compute** — haversine, metres, server-side. |
| `within_geofence` | **Stored compute** — `distance_m <= geofence_radius_m` (and a valid GPS fix exists). |
| `state` | draft / open / done. |
| `notes`, `signature`, `photo` | Proof. |

## Security

- `sales_team.group_sale_salesman` → read/write/create **own** visits (record rule on `user_id`).
- `sales_team.group_sale_manager` → read/write all visits (team supervision).

## Install on a clean Odoo 19 tenant

1. Mount the addons dir and add it to `addons_path` (already wired in
   `docker/docker-compose.yml` + `docker/odoo.conf`):
   - volume `../addons/extra-salesforce:/mnt/extra-salesforce:ro`
   - `addons_path = ...,/mnt/extra-salesforce`
2. Restart: `docker compose -f docker/docker-compose.yml up -d --force-recreate web`
3. In Odoo: **Apps → Update Apps List**, then install **N2D SFA Field Visit**
   (or CLI: `odoo -d <db> -i n2d_sfa_visit --stop-after-init`).

## Geofence test (acceptance)

1. Create a `res.partner` and set `partner_latitude` / `partner_longitude`
   (e.g. 25.197200 / 55.274200 — Dubai). *(Geo fields come from `base_geolocalize`.)*
2. **No attendance punch is required** — go straight to **Field Sales → Visits → New**.
3. Visit AT that location: set `check_in_latitude/longitude` to the same point →
   `distance_m ≈ 0`, **`within_geofence = True`** (green badge).
4. Visit ~2 km away (e.g. 25.215000 / 55.274200) → `distance_m ≈ 2000`,
   **`within_geofence = False`** (amber badge), because 2000 > 150.
5. Confirm `within_geofence` cannot be set by the client — it is a stored compute
   with no client write path.

## Deviations from the original spec

The spec's "READ FIRST" referenced a Go backend
(`backend/assets/addons/...`, `backend/internal/addons/addons.go`,
`backend/internal/odoo/hr.go`) and a `specs/017A1-.../plan.md`. **None of those
exist in this repository** — this repo is a plain Odoo addons tree. Adaptations:

- Built the addon under `addons/extra-salesforce/n2d_sfa_visit/` (the empty dir
  the user designated) instead of `backend/assets/addons/`.
- The dependency `hr_attendance_geolocation` lives in `addons/extra-addons/`; its
  conventions (Location precision, `check_in_*` geo, `_compute_map`) are reused.
- **Step 5 (register in `addons.go`) is N/A** — there is no Go install registry
  in this repo. Per-tenant enablement is via `addons_path` + Apps, now wired in
  the docker config.
- Added `base_geolocalize` to `depends` (provides `partner_latitude/longitude`)
  and `sales_team` (provides the salesman/manager groups). The spec listed only
  `hr_attendance_geolocation`; both additions are required for the geofence
  compute and the security model to function.
- The app uses its own root menu **"Field Sales"** (standalone application)
  rather than nesting under the `sale` app, to avoid a heavy `sale` dependency.
