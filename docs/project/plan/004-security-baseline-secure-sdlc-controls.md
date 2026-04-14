# 004 - Sprint Zero: Security Baseline & Secure SDLC Controls

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Security: Entra ID, RBAC, security trimming, threat model
- [Product Charter](../apic_product_charter.md) — Security and compliance requirements
- [Product Spec](../apic_portal_spec.md) — Security features

## Overview
Establish the security baseline and Secure SDLC controls that must be in place before implementing feature-heavy work. This includes threat modeling, CI security gates, secrets management, and global API protections.

## Dependencies
- **001** — Repository scaffolding (CI/CD pipeline foundation)
- **002** — Azure infrastructure (Key Vault, security resources)
- **003** — CI/CD pipeline (security gate integration points)

## Implementation Details

### 1. Threat Model Baseline
Document threat models for key attack surfaces:
```
docs/security/
├── threat-model-overview.md
├── frontend-threat-model.md
├── bff-threat-model.md
└── agent-data-threat-model.md
```

For each surface, document:
- **Assets**: What data/resources are being protected
- **Threat actors**: Who might attack (external attackers, malicious insiders)
- **Attack vectors**: XSS, CSRF, SQL injection, API abuse, unauthorized access, data leakage
- **Mitigations**: Controls already in place or planned (auth, input validation, rate limiting, etc.)
- **Residual risks**: Accepted risks with justification

Key threat scenarios to address:
- Frontend: XSS via API data, CSRF, token theft, sensitive data in client-side storage
- BFF: API abuse, injection attacks, unauthorized data access, token validation bypass
- Agent/Data paths: Prompt injection, data poisoning, unauthorized agent invocation, PII leakage in logs

### 2. CI Security Gates
Integrate automated security scanning into the CI/CD pipeline:

**SAST (Static Application Security Testing)**
- Tool: GitHub CodeQL or Semgrep
- Scan: TypeScript, JavaScript code for security issues
- Action: Block PR merge on high/critical findings

**Dependency Scanning**
- Tool: GitHub Dependabot or npm audit
- Scan: npm dependencies for known vulnerabilities
- Action: Auto-create PRs for security updates, block on critical CVEs

**Container Scanning**
- Tool: Trivy or Microsoft Defender for Containers
- Scan: Docker images for vulnerabilities and misconfigurations
- Action: Block deployment on high/critical vulnerabilities

**Secret Scanning**
- Tool: GitHub Secret Scanning or GitGuardian
- Scan: Commits for leaked secrets (API keys, tokens, passwords)
- Action: Block commits, alert security team

**SBOM & Provenance**
- Generate Software Bill of Materials (SBOM) for each release
- Use SLSA framework for supply chain security
- Store SBOM artifacts in container registry

Configuration:
```
.github/workflows/
├── security-sast.yml
├── security-dependencies.yml
├── security-container-scan.yml
└── security-secrets.yml
```

### 3. Secrets Management & Rotation
**Azure Key Vault Integration**
- Provision Azure Key Vault in infrastructure (task 002)
- Store all secrets in Key Vault: database connection strings, API keys, service principal credentials
- Use Managed Identity for Key Vault access from Container Apps
- Document secret rotation policy (90-day rotation for service principals, 1-year for certificates)

**Development Secrets**
- Use `.env.local` for local development (excluded from git)
- Provide `.env.example` template with placeholder values
- Document how to access development secrets from Key Vault

**Secret Rotation Automation**
- Create script to rotate service principal credentials
- Create script to rotate API keys for external services
- Document manual rotation process for secrets that can't be automated

```
scripts/security/
├── rotate-service-principal.sh
├── rotate-api-keys.sh
└── README.md
```

### 4. Global API Abuse Protections
**Rate Limiting**
- Implement rate limiting middleware in BFF
- Defaults: 100 requests/minute per user, 1000 requests/minute per IP
- Use Azure API Management for global rate limiting (if deployed) or implement in-memory/Redis-based limiter
- Return `429 Too Many Requests` with `Retry-After` header

**Bot Mitigation**
- Implement basic bot detection heuristics (User-Agent analysis, request patterns)
- Consider Azure Front Door WAF for advanced bot protection (document as optional enhancement)
- Block common bot signatures

**Input Validation & Sanitization**
- Document input validation rules for all BFF endpoints
- Sanitize HTML/Markdown in user-generated content
- Validate API Center query parameters to prevent injection

```
src/bff/src/middleware/
├── rate-limit.ts
├── rate-limit.test.ts
├── bot-detection.ts
├── bot-detection.test.ts
├── input-validation.ts
└── input-validation.test.ts
```

### 5. Security Policy & Reporting
Create security policy documentation:
```
SECURITY.md                    # Root-level security policy
docs/security/
├── security-policy.md         # Detailed security policy
├── vulnerability-disclosure.md # How to report security issues
└── incident-response.md       # Security incident response plan
```

Include:
- Supported versions for security updates
- How to report vulnerabilities (security@example.com or GitHub Security Advisories)
- Expected response times (acknowledge within 48 hours, fix critical within 7 days)
- Coordinated disclosure policy

### 6. Secure Development Guidelines
Document secure coding practices:
```
docs/security/
└── secure-coding-guidelines.md
```

Topics:
- Authentication and authorization best practices
- Input validation and output encoding
- Sensitive data handling (no PII in logs, encrypt at rest/in transit)
- API security (authentication, rate limiting, CORS)
- Dependency management (audit regularly, pin versions)
- Error handling (no stack traces in production, log securely)

## Testing & Acceptance Criteria
- [ ] Threat models exist for frontend, BFF, and agent/data paths
- [ ] SAST, dependency scanning, container scanning, and secret scanning are integrated into CI/CD
- [ ] Security gates block PRs/deployments on high/critical findings
- [ ] Azure Key Vault is provisioned and integrated with BFF
- [ ] Secret rotation scripts exist and are documented
- [ ] Rate limiting middleware is implemented and tested
- [ ] Bot detection middleware is implemented and tested
- [ ] Input validation rules are documented and implemented
- [ ] SECURITY.md and security policy documentation exist
- [ ] Secure coding guidelines are documented
- [ ] All security middleware has unit tests with >80% coverage
- [ ] CI pipeline successfully runs all security scans on a test commit

## Implementation Notes
<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History
| Date | Status | Author | Notes |
|------|--------|--------|-------|
| — | 🔲 Not Started | — | Task created |

### Technical Decisions
_No technical decisions recorded yet._

### Deviations from Plan
_No deviations from the original plan._

### Validation Results
_No validation results yet._


## Coding Agent Prompt

```text
**Task**: Implement plan step 004 — Security Baseline & Secure SDLC Controls.

Read the full task specification at `docs/project/plan/004-security-baseline-secure-sdlc-controls.md`.

Reference the architecture at `docs/project/apic_architecture.md` (Security section), and the infrastructure setup in `docs/project/plan/002-sprint-zero-azure-infra-bicep.md` and CI/CD pipeline in `docs/project/plan/003-sprint-zero-cicd-pipeline.md`.

Create threat model documents for frontend, BFF, and agent/data paths. Integrate security scanning tools (SAST, dependency scanning, container scanning, secret scanning) into the CI/CD pipeline. Implement secrets management integration with Azure Key Vault. Create rate limiting, bot detection, and input validation middleware for the BFF. Document security policies, vulnerability disclosure process, and secure coding guidelines.

Write unit tests for all security middleware. Verify the CI pipeline successfully runs all security scans.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/004-security-baseline-secure-sdlc-controls.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
