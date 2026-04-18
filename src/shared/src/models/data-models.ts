/**
 * Persistence data models for Cosmos DB documents.
 *
 * These interfaces define the storage-layer schema used by the BFF's
 * repository layer.  They include fields for schema versioning, soft-delete,
 * and partition keys that are not exposed in the frontend-facing DTOs.
 *
 * @see docs/architecture/storage-strategy.md
 * @see docs/architecture/schema-versioning.md
 */

// ---------------------------------------------------------------------------
// Common persistence fields
// ---------------------------------------------------------------------------

/** Fields present on every persisted document. */
export interface PersistenceMetadata {
  /** Document schema version for lazy migration. */
  schemaVersion: number;
  /** Soft-delete flag. */
  isDeleted: boolean;
  /** ISO-8601 timestamp when the document was soft-deleted, or null. */
  deletedAt: string | null;
}

// ---------------------------------------------------------------------------
// Chat Session (container: chat-sessions, partition key: /userId)
// ---------------------------------------------------------------------------

/** A single message stored within a chat session document. */
export interface ChatMessageDocument {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

/** Cosmos DB document for a chat session. */
export interface ChatSessionDocument extends PersistenceMetadata {
  id: string;
  userId: string;
  title: string;
  messages: ChatMessageDocument[];
  createdAt: string;
  updatedAt: string;
  model?: string;
  tokensUsed?: number;
}

// ---------------------------------------------------------------------------
// Governance Snapshot (container: governance-snapshots, partition key: /apiId)
// ---------------------------------------------------------------------------

/** A single finding within a governance snapshot. */
export interface GovernanceFindingDocument {
  ruleId: string;
  ruleName: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  passed: boolean;
  message: string;
}

/** Cosmos DB document for a governance snapshot. */
export interface GovernanceSnapshotDocument extends PersistenceMetadata {
  id: string;
  apiId: string;
  timestamp: string;
  findings: GovernanceFindingDocument[];
  complianceScore: number;
  agentId: string;
}

// ---------------------------------------------------------------------------
// Analytics Event (container: analytics-events, partition key: /eventType)
// ---------------------------------------------------------------------------

/** Cosmos DB document for an analytics event. */
export interface AnalyticsEventDocument extends PersistenceMetadata {
  id: string;
  eventType: string;
  timestamp: string;
  userId: string;
  apiId: string;
  metadata: Record<string, unknown>;
}
