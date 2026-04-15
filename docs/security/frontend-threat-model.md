# Frontend Threat Model — APIC Vibe Portal AI

## Component Overview

The frontend is a Next.js 16 single-page application (SPA) using the App Router, rendered in the browser. It communicates with the BFF via REST APIs and handles user authentication via Entra ID (MSAL.js).

## Assets

| Asset                  | Description                           | Sensitivity                   |
| ---------------------- | ------------------------------------- | ----------------------------- |
| Authentication tokens  | Entra ID access/refresh tokens        | High                          |
| User session state     | Current user identity and preferences | Medium                        |
| API catalog data       | API metadata displayed to users       | Low–Medium (security trimmed) |
| Chat conversation data | AI chat messages and responses        | Medium                        |
| Search queries         | User search inputs                    | Low                           |

## Threat Analysis

### T-FE-01: Cross-Site Scripting (XSS) via API Data

- **Attack vector**: Malicious content injected into API metadata (names, descriptions) rendered in the frontend without proper encoding.
- **Impact**: Session hijacking, token theft, defacement.
- **Likelihood**: Medium
- **Mitigations**:
  - React's default JSX escaping prevents most XSS.
  - Use `DOMPurify` or equivalent for any `dangerouslySetInnerHTML` usage.
  - Content Security Policy (CSP) headers to restrict script sources.
  - Never render raw HTML from API responses without sanitization.
- **Residual risk**: Low — React's built-in protections are strong.

### T-FE-02: Cross-Site Request Forgery (CSRF)

- **Attack vector**: Attacker tricks authenticated user into making unwanted requests to the BFF.
- **Impact**: Unauthorized actions on behalf of the user.
- **Likelihood**: Low (SPA + bearer token auth)
- **Mitigations**:
  - Bearer token authentication (not cookies) for BFF API calls.
  - SameSite cookie attributes for any session cookies.
  - Origin/Referer validation in BFF.
- **Residual risk**: Low — Bearer tokens in Authorization header are not automatically sent by browsers.

### T-FE-03: Token Theft / Session Hijacking

- **Attack vector**: Attacker extracts authentication tokens from browser storage or network traffic.
- **Impact**: Full impersonation of the victim user.
- **Likelihood**: Medium
- **Mitigations**:
  - Store tokens in memory (not localStorage/sessionStorage) where possible.
  - Use MSAL.js token caching with secure defaults.
  - Short-lived access tokens with silent refresh.
  - Enforce HTTPS for all communications.
  - Implement token revocation on sign-out.
- **Residual risk**: Medium — Browser-based token storage has inherent risks.

### T-FE-04: Sensitive Data in Client-Side Storage

- **Attack vector**: Sensitive data stored in localStorage, sessionStorage, or IndexedDB accessible to XSS or browser extensions.
- **Impact**: Data leakage, privacy violation.
- **Likelihood**: Medium
- **Mitigations**:
  - Minimize data stored client-side.
  - Never store PII or secrets in browser storage.
  - Clear sensitive state on logout.
  - Document what data is permissible to store client-side.
- **Residual risk**: Low — With proper practices, minimal data is at risk.

### T-FE-05: Dependency Supply Chain Attack

- **Attack vector**: Compromised npm package introduces malicious code.
- **Impact**: Arbitrary code execution in user browsers.
- **Likelihood**: Low–Medium
- **Mitigations**:
  - Use `npm audit` in CI pipeline.
  - Dependabot for automated vulnerability alerts and updates.
  - Lock file (`package-lock.json`) for reproducible builds.
  - Review dependency changes in PRs.
- **Residual risk**: Low — Automated scanning catches most known vulnerabilities.

### T-FE-06: Open Redirect

- **Attack vector**: Attacker manipulates redirect URLs to send users to malicious sites after authentication.
- **Impact**: Phishing, credential theft.
- **Likelihood**: Low
- **Mitigations**:
  - Validate redirect URIs against an allowlist.
  - Use relative redirects where possible.
  - MSAL.js configuration restricts redirect URIs.
- **Residual risk**: Low

## Security Controls Summary

| Control                         | Status             |
| ------------------------------- | ------------------ |
| React JSX auto-escaping         | Built-in           |
| Content Security Policy headers | Planned (Task 005) |
| MSAL.js for authentication      | Planned (Task 008) |
| npm audit in CI                 | This task          |
| Dependabot alerts               | This task          |
| HTTPS enforcement               | Infrastructure     |
