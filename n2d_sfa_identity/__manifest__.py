{
    "name": "N2D SFA Identity & Attribution",
    "summary": "Field-salesperson (hr.employee) attribution on sales documents. "
               "Field reps are not Odoo users (SPEC-017A-SEC); this carries "
               "salesperson_employee_id on sale.order / stock.picking / account.move / "
               "account.payment, propagates it order->picking->invoice->payment, and adds "
               "employee Orders/Deliveries/Invoices/Collections smart buttons.",
    "version": "18.0.1.1.0",
    "license": "LGPL-3",
    "author": "N2D",
    "category": "Sales",
    "depends": ["hr", "sale", "stock", "account"],
    "data": [
        "views/sale_order_views.xml",
        "views/stock_picking_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
        "views/hr_employee_views.xml",
    ],
    "installable": True,
    "application": False,
}
