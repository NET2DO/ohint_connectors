# n2d_ohint_pos — Catalog Sync (Odoo → Branches)

Reports product/pricelist/tax/payment-method writes to the OHINT middleware
catalog webhook (SPEC-041 §Webhook extension), so connected POS branches pull
price/catalog changes within minutes instead of waiting on their next
heartbeat-triggered check.

## What triggers a sync event

| Model | When | Reported as |
|-------|------|--------------|
| `product.template` | create/write | `product.template: [ids]` |
| `product.pricelist` | create/write | `product.pricelist: [ids]` |
| `product.pricelist.item` | create/write | the **parent** pricelist's id under `product.pricelist` — a rule edit doesn't touch the pricelist header, but it's exactly what POS branches need to see |
| `account.tax` | create/write | `account.tax: [ids]` |
| `pos.payment.method` | create/write | `pos.payment.method: [ids]` |

Multiple writes across different models in the **same transaction** batch
into a single webhook call (e.g. a bulk price update touching 50 products
fires one POST with 50 ids, not 50). The POST fires **after the transaction
commits** (`cr.postcommit`), so a rolled-back change never notifies. A webhook
failure is logged and swallowed — it never surfaces to the Odoo user or blocks
their write.

## Configuration

Reuses `n2d_ohint_notify`'s already-configured `ohint.webhook_url` /
`ohint.webhook_secret` / `ohint.tenant_id` system parameters (Settings →
Technical → System Parameters) — no separate setup. If those aren't set,
catalog sync silently no-ops.

## Wire format

```json
POST /webhooks/odoo/notify
X-OHINT-Timestamp: 1785240312
X-OHINT-Signature: sha256=<hmac-sha256 of the raw body, hex>

{"tenant_id":"...","event":"catalog.changed","models":{"product.template":[17,21],"product.pricelist":[2]}}
```

Signed exactly like `n2d_ohint_notify`'s events and the SPEC-017
sale-order-confirmed webhook. Verified end-to-end against a live Odoo 19
instance (docker19ee/demo19): install, single/batched writes, and the
pricelist-item → parent-pricelist mapping all confirmed working, with the
HMAC signature cross-checked byte-for-byte against the Go verification code
in `internal/notification/handler.go`.

## Not yet handled

- **Deletes**: `unlink()` isn't reported. The middleware's `DeltaResponse`
  already reserves a `deletes` field per model for this, but nothing
  populates it yet on the Go side either — a deleted product just stops
  appearing in future deltas rather than being explicitly retracted.
- **product.product** (variants): only `product.template` is tracked, matching
  the middleware's `catalogKeyToModel` (`internal/pos/catalog.go`), which only
  pulls templates for the `products` catalog key today.
