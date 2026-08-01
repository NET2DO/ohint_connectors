{
    "name": "N2D OHINT POS Catalog Sync (Odoo → Branches)",
    "summary": "Reports product/pricelist/tax/payment-method/service-man-partner "
               "writes to the OHINT middleware catalog webhook (SPEC-041 "
               "§Webhook extension) so connected POS branches pull catalog "
               "changes within minutes instead of waiting on their next "
               "heartbeat-triggered check. HMAC-signed, POSTed to "
               "/webhooks/odoo/notify with event=catalog.changed after the "
               "transaction commits. Also adds res.partner.is_service_man, "
               "the eligibility flag for delivery/collection contractors. "
               "Amendment B: emits event=stock.changed on stock.quant writes so "
               "branches see warehouse on-hand changes, which the catalog path "
               "cannot carry (a quant write never touches product.template).",
    "version": "19.0.1.2.0",
    "license": "LGPL-3",
    "author": "N2D",
    "category": "Point of Sale",
    # stock is explicit, not left to point_of_sale's transitive chain: this
    # addon inherits stock.quant directly and must not load without it.
    "depends": ["point_of_sale", "stock", "account", "n2d_ohint_notify"],
    "data": ["views/res_partner_views.xml"],
    "installable": True,
    "application": False,
}
