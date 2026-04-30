# APIC Vibe Portal AI - Product Spec

(See full spec provided in chat)

## API Center Backup & Restore

### Backup Feature (Task 034)

Automated backup of the entire Azure API Center resource, enabling disaster recovery and environment cloning.

#### Capabilities

- **Full catalog export**: All APIs, versions, definitions (including raw specs), deployments, environments, and custom metadata schemas are captured in a self-contained ZIP archive
- **Scheduled execution**: Container Apps Job runs hourly via cron (`0 * * * *`)
- **GFS retention policy**: Configurable retention for hourly (default 24), daily (default 30), monthly (default 12), and annual (default 3) backups
- **Backup metadata**: Each backup is tracked in Cosmos DB with timestamp, size, entity counts, retention tier, and status
- **Admin UI**: Admin-only `/admin/backup` page to browse backup history — displays date/time, size, API count, entity count, retention tiers, and status; supports download via time-limited SAS URL
- **Blob storage**: Backups stored in a dedicated Azure Blob Storage container with lifecycle management (Cool tier at 30 days, Archive at 90 days)
- **Manifest**: Each ZIP includes a `manifest.json` with version, source details, and entity counts to support future restore operations

#### Restore (Future)

Restore capability will be implemented in a subsequent task, rehydrating a new API Center instance from a backup ZIP archive.
