from django.db.migrations.operations.models import CreateModel


class EnsureCreateModel(CreateModel):
    """Reconcile legacy tables without dropping or recreating existing data."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.name)
        connection = schema_editor.connection
        if model._meta.db_table in connection.introspection.table_names():
            with connection.cursor() as cursor:
                columns = {
                    column.name
                    for column in connection.introspection.get_table_description(
                        cursor, model._meta.db_table
                    )
                }
            expected = {field.column for field in model._meta.local_fields}
            missing = expected - columns
            if missing:
                raise RuntimeError(
                    f"Existing table {model._meta.db_table} has missing columns: {sorted(missing)}; reconcile it before deployment."
                )
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # These tables can predate this migration. Preserve their contents on rollback.
        pass
