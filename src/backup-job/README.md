# Backup Job

Azure Container Apps Job that produces hourly snapshot backups of an Azure
API Center service into a self-contained ZIP archive in Azure Blob Storage.

See [`docs/project/plan/034-api-center-backup.md`](../../docs/project/plan/034-api-center-backup.md)
for the full specification.

## Local development

```pwsh
cd src/backup-job
uv sync
cp .env.example .env
# Fill in API_CENTER_ENDPOINT, BACKUP_STORAGE_ACCOUNT_URL, COSMOS_ENDPOINT...
uv run python main.py
```

## Tests

```pwsh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
