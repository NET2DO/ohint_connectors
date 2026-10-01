def post_init_hook(env):
    env["ohint.activity.done"]._backfill_from_chatter()
