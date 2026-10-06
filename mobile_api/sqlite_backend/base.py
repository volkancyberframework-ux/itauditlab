"""SQLite writer serialization for the isolated device demo only."""

from django.db.backends.sqlite3.base import DatabaseWrapper as SQLiteDatabaseWrapper


class DatabaseWrapper(SQLiteDatabaseWrapper):
    def _start_transaction_under_autocommit(self):
        # Acquire the writer lock before reading. A deferred transaction cannot
        # safely upgrade its snapshot while an analytics write is in flight.
        self.cursor().execute("BEGIN IMMEDIATE")
