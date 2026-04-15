# Security Policy

## Reporting Security Vulnerabilities

**Please do NOT report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability in the APIC Vibe Portal, please report it responsibly:

1. **GitHub Security Advisories** (preferred): Use [GitHub Security Advisories](../../security/advisories/new) to report vulnerabilities privately.
2. **Email**: Send details to the repository maintainers via the contact information in the repository.

### What to Include
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline
- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 5 business days
- **Fix for critical issues**: Within 7 days
- **Fix for high issues**: Within 30 days

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest on `main` | ✅ |
| Previous releases | Best effort |

## Security Measures

This project implements the following security controls:

- **Authentication**: Azure Entra ID (Azure AD) with OIDC
- **Authorization**: Role-Based Access Control (RBAC) with security trimming
- **Secrets Management**: Azure Key Vault with Managed Identity
- **CI/CD Security**: SAST (CodeQL), dependency scanning (Dependabot), container scanning (Trivy), secret scanning
- **API Protection**: Rate limiting, bot detection, input validation
- **Infrastructure**: Encryption at rest and in transit, network isolation

For detailed security documentation, see [`docs/security/`](docs/security/).
