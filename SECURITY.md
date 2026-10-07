# Security / Credentials

AgriFlow is a local academic analytics application and does not require user accounts.

- Store optional data-provider keys only in `.env`.
- `.env` is excluded from version control.
- Do not commit raw source files if their redistribution terms do not allow it.
- The application does not execute uploaded code.
- Before sharing the project directory, verify that `.env` and `data/raw/` are absent from the archive/repository.
