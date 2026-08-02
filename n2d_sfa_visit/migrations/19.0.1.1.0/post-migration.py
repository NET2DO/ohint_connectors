def migrate(cr, version):
    """SPEC-017A-SEC: drop the legacy user_id/sales_team record rules.

    They were created with noupdate=1, so removing them from the XML does not
    delete them on -u; do it explicitly here.
    """
    for name in ("sfa_visit_rule_own_salesman", "sfa_visit_rule_all_manager"):
        cr.execute(
            "DELETE FROM ir_rule WHERE id IN "
            "(SELECT res_id FROM ir_model_data "
            " WHERE module='n2d_sfa_visit' AND name=%s AND model='ir.rule')",
            (name,),
        )
        cr.execute(
            "DELETE FROM ir_model_data "
            "WHERE module='n2d_sfa_visit' AND name=%s",
            (name,),
        )
