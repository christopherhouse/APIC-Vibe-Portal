# Incident Response Plan — APIC Vibe Portal AI

## Purpose

This document defines the process for responding to security incidents affecting the APIC Vibe Portal AI.

## Severity Levels

| Level             | Description                                              | Examples                                          | Response Time        |
| ----------------- | -------------------------------------------------------- | ------------------------------------------------- | -------------------- |
| **P1 — Critical** | Active exploitation, data breach, full system compromise | Leaked credentials, unauthorized data access, RCE | Immediate (< 1 hour) |
| **P2 — High**     | Exploitable vulnerability, partial system compromise     | Authentication bypass, privilege escalation       | < 4 hours            |
| **P3 — Medium**   | Potential vulnerability, no active exploitation          | Misconfiguration, missing security headers        | < 24 hours           |
| **P4 — Low**      | Minor security issue, minimal impact                     | Informational disclosure, cosmetic issues         | < 1 week             |

## Incident Response Phases

### 1. Detection & Identification

**Sources of detection:**

- CI/CD security scan alerts (CodeQL, Trivy, Dependabot)
- Azure Security Center / Microsoft Defender alerts
- Application Insights anomaly detection
- External vulnerability reports (see [vulnerability-disclosure.md](vulnerability-disclosure.md))
- Manual code review findings

**Actions:**

- Log the incident with timestamp, source, and initial assessment.
- Assign a severity level.
- Notify the incident response team.

### 2. Containment

**Immediate containment (P1/P2):**

- Rotate compromised credentials immediately.
- Disable compromised user accounts.
- Apply network restrictions (Container Apps ingress rules).
- Scale down or pause affected services if necessary.

**Short-term containment:**

- Deploy hotfix or configuration change.
- Enable enhanced logging/monitoring.
- Block malicious IPs via Azure Front Door / Container Apps.

### 3. Eradication

- Identify root cause.
- Remove malicious code, compromised dependencies, or backdoors.
- Patch the vulnerability.
- Verify the fix in a staging environment.

### 4. Recovery

- Deploy the fix to production.
- Restore any affected data from backups.
- Re-enable disabled accounts after verification.
- Increase monitoring for 48 hours post-recovery.

### 5. Post-Incident Review

Within **5 business days** of resolution:

- Document the full incident timeline.
- Identify what went well and what could be improved.
- Create action items for preventive measures.
- Update threat models if new attack vectors were identified.
- Share findings with the team (redacting sensitive details).

## Communication

### Internal Communication

- Use a dedicated incident channel for real-time coordination.
- Keep stakeholders updated with hourly briefings (P1/P2).
- Document all actions in the incident log.

### External Communication

- Affected users are notified within **72 hours** of a confirmed data breach.
- A public post-mortem is published for significant incidents.
- Coordinate with Microsoft's security team for Azure service issues.

## Key Contacts

| Role                | Responsibility                           |
| ------------------- | ---------------------------------------- |
| Incident Commander  | Overall coordination and decision-making |
| Security Lead       | Technical investigation and remediation  |
| Infrastructure Lead | Azure service-level response             |
| Communications Lead | Internal/external communications         |

## Tools & Resources

- **Azure Security Center**: Threat detection and security posture.
- **Application Insights**: Application-level monitoring and alerting.
- **Key Vault audit logs**: Secret access tracking.
- **GitHub Security Advisories**: Vulnerability disclosure coordination.
- **Container Apps logs**: Request-level monitoring.

## Runbooks

### Compromised Secret

1. Identify which secret was compromised.
2. Rotate the secret immediately (`scripts/security/rotate-*.sh`).
3. Check Key Vault audit logs for unauthorized access.
4. Review application logs for exploitation attempts.
5. Notify affected users if their data was accessed.

### Unauthorized Data Access

1. Identify the scope of accessed data.
2. Revoke the attacker's access (disable account, rotate tokens).
3. Review security trimming and RBAC configuration.
4. Determine if data was exfiltrated.
5. Notify affected data owners.

### Dependency Vulnerability

1. Assess the severity and exploitability.
2. Check if the vulnerable code path is used.
3. Apply the fix (update dependency, apply workaround).
4. Deploy to all environments.
5. Monitor for exploitation attempts.
