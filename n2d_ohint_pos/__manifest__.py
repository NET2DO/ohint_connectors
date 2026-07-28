{
    "name": "N2D OHINT POS Catalog Sync (Odoo → Branches)",
    "summary": "Reports product/pricelist/tax/payment-method writes to the OHINT "
               "middleware catalog webhook (SPEC-041 §Webhook extension) so "
               "connected POS branches pull price/catalog changes within "
               "minutes instead of waiting on their next heartbeat-triggered "
               "check. HMAC-signed, POSTed to /webhooks/odoo/notify with "
               "event=catalog.changed after the transaction commits.",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "author": "N2D",
    "category": "Point of Sale",
    "depends": ["point_of_sale", "account", "n2d_ohint_notify"],
    "data": [],
    "installable": True,
    "application": False,
}
