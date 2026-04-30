/**
 * API client for the admin backup endpoints.
 *
 * All endpoints require the `Portal.Admin` role.
 */

import { apiClient } from './api-client';

const ADMIN_BACKUPS_BASE = '/api/admin/backups';

export interface BackupCounts {
  apis: number;
  versions: number;
  definitions: number;
  deployments: number;
  environments: number;
}

export interface BackupSummary {
  backupId: string;
  sourceServiceName: string;
  timestamp: string;
  blobName: string;
  sizeBytes: number;
  sizeFormatted: string;
  counts: BackupCounts;
  retentionTiers: string[];
  status: string;
  durationMs: number;
}

export interface BackupListResponse {
  items: BackupSummary[];
  count: number;
}

export interface BackupDownloadResponse {
  backupId: string;
  downloadUrl: string;
  expiresAt: string;
}

/** List recent backups, newest first. */
export async function fetchBackups(limit = 50): Promise<BackupListResponse> {
  return apiClient.get<BackupListResponse>(`${ADMIN_BACKUPS_BASE}?limit=${limit}`);
}

/** Retrieve metadata for a single backup. */
export async function fetchBackup(backupId: string): Promise<BackupSummary> {
  return apiClient.get<BackupSummary>(`${ADMIN_BACKUPS_BASE}/${encodeURIComponent(backupId)}`);
}

/** Request a short-lived SAS download URL for a backup ZIP. */
export async function fetchBackupDownload(backupId: string): Promise<BackupDownloadResponse> {
  return apiClient.get<BackupDownloadResponse>(
    `${ADMIN_BACKUPS_BASE}/${encodeURIComponent(backupId)}/download`
  );
}
