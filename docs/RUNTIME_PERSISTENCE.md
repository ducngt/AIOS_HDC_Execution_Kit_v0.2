# Runtime Persistence

The prototype persists Foundation Data, import history, accounts, role assignments, AI Agent/Provider registry, AI run audit and Data records in SQLite.

Default path:

`runtime/aios-prototype.sqlite3`

Override with `AIOS_DB_PATH`. For a Codespace or server, point this variable at a persistent volume/path when required. The database uses WAL mode, foreign keys and a busy timeout. Uploaded source workbooks are parsed in memory and are not stored by the application.
