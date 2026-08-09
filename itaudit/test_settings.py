from .settings import *  # noqa: F403


# Migration 0013 intentionally records fields that already existed in the
# production database. Build a fresh test schema from current models instead.
MIGRATION_MODULES = {"core": None}
