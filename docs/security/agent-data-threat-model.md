# Agent & Data Path Threat Model — APIC Vibe Portal AI

## Component Overview
The agent and data paths encompass Azure OpenAI, Foundry Agent Service (multi-agent orchestration), Azure AI Search, Azure API Center, and Azure Cosmos DB. The BFF mediates all interactions; no direct client-to-service communication exists.

## Assets
| Asset | Description | Sensitivity |
|-------|-------------|-------------|
| AI model access | Azure OpenAI endpoints and API keys | Critical |
| Agent configurations | Foundry Agent definitions and tools | High |
| Search index | AI Search index with API metadata | Medium |
| API Center data | Full API catalog metadata | Medium |
| Cosmos DB data | Chat sessions, governance snapshots, analytics | Medium–High |
| User prompts | Natural language queries from users | Medium |
| AI responses | Generated content from agents/OpenAI | Medium |

## Threat Analysis

### T-AD-01: Prompt Injection
- **Attack vector**: User crafts input that manipulates AI agent behavior to bypass instructions, extract system prompts, or perform unauthorized actions.
- **Impact**: Data leakage, unauthorized agent actions, misleading responses.
- **Likelihood**: High
- **Mitigations**:
  - Sanitize user input before passing to agents.
  - Use system prompts with clear instruction boundaries.
  - Implement output filtering for sensitive data.
  - Monitor for anomalous agent behavior patterns.
  - Never include secrets or credentials in system prompts.
  - Use Foundry Agent guardrails where available.
- **Residual risk**: Medium — Prompt injection remains an evolving threat with no complete solution.

### T-AD-02: Data Poisoning
- **Attack vector**: Malicious data injected into the AI Search index or API Center that corrupts AI responses.
- **Impact**: Incorrect governance advice, misleading search results, reputational damage.
- **Likelihood**: Low
- **Mitigations**:
  - Restrict write access to API Center and Search index via RBAC.
  - Validate data at ingestion time.
  - Audit trail for data modifications.
  - Periodic data integrity checks.
- **Residual risk**: Low — Write access is tightly controlled.

### T-AD-03: Unauthorized Agent Invocation
- **Attack vector**: Attacker bypasses authorization to invoke Foundry Agents directly or triggers agent capabilities beyond their authorized scope.
- **Impact**: Unauthorized data access, resource consumption, cost escalation.
- **Likelihood**: Medium
- **Mitigations**:
  - All agent invocations go through BFF (no direct client access).
  - BFF validates user authorization before agent calls.
  - Rate limiting on agent invocations.
  - Foundry Agent authentication via Managed Identity.
  - Scoped agent permissions (each agent only accesses required resources).
- **Residual risk**: Low — BFF mediation provides strong access control.

### T-AD-04: PII Leakage in Logs
- **Attack vector**: Personally identifiable information from user prompts or agent responses is logged to Application Insights or other log sinks.
- **Impact**: Privacy violation, regulatory non-compliance.
- **Likelihood**: Medium
- **Mitigations**:
  - Never log full user prompts or AI responses.
  - Implement log sanitization to redact PII patterns (emails, names).
  - Configure Application Insights to exclude sensitive telemetry fields.
  - Use structured logging with explicit field allowlists.
  - Regular log audit for PII presence.
- **Residual risk**: Medium — PII detection is imperfect; some leakage may occur in edge cases.

### T-AD-05: Data Exfiltration via AI Responses
- **Attack vector**: AI agent includes sensitive data (from search index, API Center, or Cosmos DB) in responses to unauthorized users.
- **Impact**: Unauthorized data access, security trimming bypass.
- **Likelihood**: Medium
- **Mitigations**:
  - Security trimming applied before data reaches agents (Task 020).
  - Agent system prompts restrict data sharing scope.
  - BFF validates response content before returning to client.
  - Separate agent permissions per data classification level.
- **Residual risk**: Medium — AI responses are inherently difficult to fully control.

### T-AD-06: Cosmos DB Data Breach
- **Attack vector**: Attacker gains unauthorized access to Cosmos DB and exfiltrates chat sessions, governance data, or analytics.
- **Impact**: Data breach, privacy violation, loss of intellectual property.
- **Likelihood**: Low
- **Mitigations**:
  - Cosmos DB firewall restricts access to Container Apps VNet.
  - Managed Identity authentication (no connection strings in code).
  - Encryption at rest (Azure-managed keys).
  - RBAC at the database/container level.
  - Audit logging enabled.
- **Residual risk**: Low — Azure-managed security controls are robust.

### T-AD-07: AI Search Index Tampering
- **Attack vector**: Attacker modifies or deletes search index entries to disrupt search functionality.
- **Impact**: Search unavailability, corrupted results, denial of service.
- **Likelihood**: Low
- **Mitigations**:
  - Restrict index write access to indexer pipeline only.
  - Use Managed Identity with minimal permissions.
  - Index backup and recovery procedures.
  - Monitor for unexpected index modifications.
- **Residual risk**: Low

### T-AD-08: Model Denial of Service
- **Attack vector**: Attacker sends expensive queries to Azure OpenAI (long prompts, high token counts) to exhaust quota or increase costs.
- **Impact**: Service unavailability, cost escalation.
- **Likelihood**: Medium
- **Mitigations**:
  - Rate limiting on AI-related endpoints (more restrictive than general APIs).
  - Token count limits on user inputs.
  - Azure OpenAI quota and throttling configuration.
  - Cost alerts and budget limits.
  - Request timeout configuration.
- **Residual risk**: Medium — Some cost escalation risk remains with legitimate-looking queries.

## Security Controls Summary
| Control | Status |
|---------|--------|
| Input sanitization before agent calls | This task (middleware) |
| Rate limiting on AI endpoints | This task |
| Managed Identity for all Azure services | Infrastructure (Task 002) |
| Security trimming | Planned (Task 020) |
| PII-free logging | Planned (Task 019) |
| RBAC on data stores | Infrastructure (Task 002) |
| Azure OpenAI quota management | Planned (Task 017) |
| Agent guardrails | Planned (Task 022) |
