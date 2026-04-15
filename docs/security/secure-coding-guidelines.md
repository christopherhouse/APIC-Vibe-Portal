# Secure Coding Guidelines — APIC Vibe Portal AI

## Overview

These guidelines define secure coding practices for all contributors to the APIC Vibe Portal AI project. They apply to the frontend (TypeScript/Next.js), BFF (Python/FastAPI), and infrastructure (Bicep/GitHub Actions).

---

## Authentication & Authorization

### Do

- Use **Entra ID (Azure AD)** for all user authentication.
- Validate JWT tokens on **every** BFF endpoint (signature, expiration, issuer, audience).
- Implement **security trimming** — filter query results by user permissions.
- Use **Managed Identity** for all service-to-service authentication.
- Apply the **principle of least privilege** for RBAC roles.

### Don't

- Never implement custom authentication schemes.
- Never trust client-provided user IDs for authorization decisions.
- Never store authentication tokens in `localStorage` or `sessionStorage`.
- Never skip token validation for "internal" endpoints.

---

## Input Validation & Output Encoding

### Do

- Validate **all** user input using Pydantic models (BFF) or Zod schemas (frontend).
- Use **parameterized queries** for all database operations (Cosmos DB).
- Sanitize HTML/Markdown content before rendering with `DOMPurify` or similar.
- Validate Content-Type headers on all incoming requests.
- Limit request body sizes.

### Don't

- Never construct queries from raw user input (SQL injection, NoSQL injection).
- Never use `dangerouslySetInnerHTML` without sanitization.
- Never trust `Content-Type` headers without validation.
- Never pass unsanitized user input to AI agents or system prompts.

---

## Sensitive Data Handling

### Do

- Store **all secrets** in Azure Key Vault.
- Use `.env.local` for local development secrets (gitignored).
- Encrypt sensitive data at rest (Azure-managed encryption).
- Use HTTPS/TLS 1.2+ for all communications.
- Clear sensitive state from memory when no longer needed.

### Don't

- **Never** hardcode secrets, API keys, or passwords in code.
- **Never** log tokens, passwords, API keys, or PII.
- **Never** include secrets in system prompts or AI agent configurations.
- **Never** commit `.env` files to source control.
- **Never** return stack traces or internal error details in production responses.

---

## API Security

### Do

- Implement rate limiting on all public endpoints.
- Return `429 Too Many Requests` with `Retry-After` headers.
- Use structured error responses (no implementation details in production).
- Implement request timeouts on all outgoing service calls.
- Validate all path parameters and query strings.

### Don't

- **Never** add CORS middleware to the BFF (Azure Container Apps handles CORS).
- **Never** expose internal service endpoints publicly.
- **Never** return unbounded result sets (always paginate).
- **Never** log full request/response bodies in production.

---

## Dependency Management

### Do

- Run `npm audit` and dependency scanning in CI on every PR.
- Pin dependency versions via lock files (`package-lock.json`, `uv.lock`).
- Review dependency changes carefully in pull requests.
- Update dependencies regularly (weekly Dependabot PRs).
- Prefer well-maintained, widely-used packages.

### Don't

- **Never** disable security audit checks to make CI pass.
- **Never** use deprecated or unmaintained packages.
- **Never** bypass lock files (no `--no-lock`, `--force` for dependency installs).
- **Never** add dependencies without checking for known vulnerabilities.

---

## Error Handling & Logging

### Do

- Return generic error messages to clients in production.
- Log errors with structured fields (correlation ID, timestamp, error type).
- Use different log levels for development vs. production.
- Include request correlation IDs in all log entries.
- Implement global exception handlers in the BFF.

### Don't

- **Never** expose stack traces, file paths, or internal IPs to clients.
- **Never** log PII (email addresses, usernames, IP addresses in error details).
- **Never** catch and silently ignore exceptions.
- **Never** use `console.log` for production logging (use structured logger).

---

## Container Security

### Do

- Use **multi-stage Docker builds** (separate build and production stages).
- Run containers as **non-root users**.
- Use **minimal base images** (alpine, slim variants).
- Pin base image versions (not `:latest`).
- Scan container images with **Trivy** before deployment.
- Include **health check endpoints** in all containers.

### Don't

- **Never** install unnecessary tools in production images (curl, wget, etc.).
- **Never** run containers as root.
- **Never** embed secrets in Docker images or Dockerfiles.
- **Never** use `:latest` tags for base images.

---

## Infrastructure as Code (Bicep)

### Do

- Enable **diagnostic settings** on all Azure resources.
- Configure **network restrictions** (firewalls, private endpoints) where possible.
- Use **Managed Identity** instead of connection strings.
- Enable **encryption at rest** for all data stores.
- Use **OIDC** for CI/CD authentication (no stored secrets).

### Don't

- **Never** hardcode secrets in Bicep parameters.
- **Never** deploy Container Apps via Bicep (use deployment scripts).
- **Never** disable Azure security features to "simplify" deployments.

---

## AI & Agent Security

### Do

- Sanitize user input before passing to AI models or agents.
- Use system prompts with clear instruction boundaries.
- Implement token count limits on user inputs.
- Apply security trimming **before** data reaches agents.
- Monitor agent responses for unexpected data leakage.

### Don't

- **Never** include secrets or credentials in system prompts.
- **Never** allow agents unrestricted access to all data.
- **Never** log full AI prompts or responses (PII risk).
- **Never** trust AI-generated content without validation.

---

## Code Review Checklist

When reviewing PRs, check for:

- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all user-facing endpoints
- [ ] Authentication required on all non-public endpoints
- [ ] Authorization checks (RBAC, security trimming) where appropriate
- [ ] No PII in log statements
- [ ] Error responses don't leak implementation details
- [ ] Dependencies are pinned and audited
- [ ] Docker containers run as non-root
- [ ] Tests cover security-relevant logic
