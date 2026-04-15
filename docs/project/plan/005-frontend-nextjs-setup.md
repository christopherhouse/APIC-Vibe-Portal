# 005 - Phase 1 MVP: Next.js Frontend Project Setup

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Frontend: Next.js SPA
- [Product Charter](../apic_product_charter.md) — Portal UI in scope
- [Product Spec](../apic_portal_spec.md) — UI feature requirements

## Overview
Scaffold the Next.js frontend application with App Router, TypeScript, Material UI (MUI), and a component library foundation. This establishes the UI project that all subsequent frontend tasks build upon.

## Dependencies
- **001** — Repository scaffolding (monorepo workspace structure)

## Implementation Details

### 1. Project Initialization
- Use `create-next-app` within `src/frontend/` with the following options:
  - TypeScript: Yes
  - App Router: Yes
  - Tailwind CSS: No
  - ESLint: Yes (extend root config)
  - Import alias: `@/`
- Install Material UI (MUI) packages: `@mui/material`, `@mui/icons-material`, `@emotion/react`, `@emotion/styled`
- Ensure the project integrates with the root npm workspace.

### 2. Core Configuration
- **TypeScript**: Extend `tsconfig.base.json` from root; enable strict mode
- **ESLint**: Extend root ESLint config; add Next.js specific rules (`next/core-web-vitals`)
- **Prettier**: Use root Prettier config
- **Material UI Theme**: Configure a custom MUI theme with design tokens (colors, spacing, typography) aligned to portal branding. Set up `ThemeProvider` and `CssBaseline` in the root layout.
- **Next.js Config**: Enable standalone output for Docker builds, configure image optimization

### 3. Application Shell
Create the base application layout structure:
```
src/frontend/
├── app/
│   ├── layout.tsx          # Root layout (HTML shell, providers, navigation)
│   ├── page.tsx            # Homepage / Landing
│   ├── loading.tsx         # Global loading state
│   ├── error.tsx           # Global error boundary
│   ├── not-found.tsx       # 404 page
│   └── globals.css         # Global resets + base styles (MUI CssBaseline handles most resets)
├── components/
│   ├── ui/                 # Reusable primitives (Button, Input, Card, etc.)
│   ├── layout/             # Header, Footer, Sidebar, Navigation
│   └── shared/             # Cross-cutting components
├── lib/
│   ├── api-client.ts       # BFF API client (fetch wrapper)
│   ├── theme.ts            # MUI custom theme (colors, typography, spacing, component overrides)
│   └── utils.ts            # Utility functions
├── hooks/                  # Custom React hooks
├── types/                  # TypeScript type definitions
└── __tests__/              # Test setup and utilities
```

### 4. Component Library Foundation
Leverage Material UI's pre-built components and create thin wrapper components where needed for portal-specific patterns:
- `Button` — Use MUI `Button` with portal theme variants (contained, outlined, text); add loading state via MUI `LoadingButton` from `@mui/lab`
- `TextField` — Use MUI `TextField` with label, error state, helper text
- `Card` — Use MUI `Card`, `CardHeader`, `CardContent`, `CardActions` for content cards
- `Badge`/`Chip` — Use MUI `Chip` for status indicators (e.g., API lifecycle state) with color-coded variants
- `Skeleton` — Use MUI `Skeleton` for loading placeholders

Install `@mui/lab` for advanced components (LoadingButton, etc.).

### 5. Layout Components
Use MUI layout and navigation components:
- **Header**: MUI `AppBar` + `Toolbar` with app logo, search bar placeholder, user avatar placeholder
- **Sidebar/Navigation**: MUI `Drawer` (collapsible) with `List`, `ListItem`, `ListItemIcon` for route links
- **Footer**: Basic footer with MUI `Container` and `Typography`

### 6. API Client Setup
Create a typed fetch wrapper in `lib/api-client.ts`:
- Base URL from environment variable (`NEXT_PUBLIC_BFF_URL`)
- Typed request/response handling
- Error handling with custom error types
- Auth token injection placeholder (for Entra ID integration later)

### 7. Testing Setup
- Configure Jest with React Testing Library
- Add test utilities (custom render with providers)
- Write tests for each base UI component
- Ensure `npm test` runs from workspace root

## Testing & Acceptance Criteria
- [ ] `npm run dev` starts the Next.js development server without errors
- [ ] `npm run build` produces a successful production build
- [ ] `npm run lint` passes with zero warnings
- [ ] TypeScript compiles with `--noEmit` and zero errors
- [ ] All base UI component tests pass
- [ ] Application renders the shell layout (header, navigation, content area, footer)
- [ ] API client module exports typed fetch functions
- [ ] `localhost:3000` shows the landing page with layout

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
| 2026-04-15 | ✅ Complete | Copilot | Scaffolded Next.js 16.2.3 with MUI v9, app shell, 5 portal UI components (26 tests passing), typed BFF API client, Jest+RTL testing, ESLint 9 flat config. Build, lint, and tests all pass. |

### Technical Decisions
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-15 | **Adopted Material UI (MUI) as the UI component library and styling solution**, replacing the original plan of Tailwind CSS + custom components | MUI provides a comprehensive set of pre-built, accessible React components with a robust theming system, reducing the need to build and maintain custom primitives. It includes layout components (AppBar, Drawer, Container), data display (Table, DataGrid, Chip), form controls (TextField, Select, Autocomplete), and feedback (Skeleton, Alert, Snackbar) that directly map to portal requirements. Emotion is used as the default styling engine. This pivot is expected to accelerate frontend development across all phases. |
| 2026-04-15 | **Used MUI Button native `loading` prop** instead of `@mui/lab` LoadingButton | MUI v9 promotes the loading prop directly on Button; LoadingButton from lab is deprecated. |
| 2026-04-15 | **Used ESLint directly** instead of `next lint` | Next.js 16 removed the built-in `next lint` CLI command. Lint script uses `eslint .` with an ESLint 9 flat config including `@next/eslint-plugin-next` rules. |
| 2026-04-15 | **Used `@mui/material-nextjs` AppRouterCacheProvider** | Required for proper Emotion SSR/streaming in Next.js App Router to prevent FOUC. |
| 2026-04-15 | **Manual scaffold** instead of `create-next-app` | `create-next-app` was unresponsive in the sandboxed environment; project was manually scaffolded with identical structure and configuration. |
| 2026-04-15 | **Added Playwright e2e testing from the start** (not deferred to task 021) | Per review feedback, e2e tests should be added alongside each feature, not deferred to a single integration testing task. Playwright is configured in `src/frontend/playwright.config.ts` with Chromium, Firefox, and WebKit projects. CI runs e2e tests on every PR. All future frontend tasks must include corresponding e2e tests. |

### Deviations from Plan
- **Manual scaffold instead of `create-next-app`**: The `create-next-app` CLI was unresponsive in the sandboxed environment, so the project was manually scaffolded with the same structure and configuration that `create-next-app` would produce.
- **`@mui/lab` LoadingButton replaced with native MUI Button loading prop**: MUI v9 deprecated `@mui/lab/LoadingButton`; the native `loading` prop on `@mui/material/Button` is used instead.
- **`next lint` replaced with `eslint .`**: Next.js 16 removed the `next lint` CLI command; ESLint is run directly with a flat config.

### Validation Results
| Check | Result |
|-------|--------|
| `npm run dev` starts dev server | ✅ Ready in 303ms on http://localhost:3000 |
| `npm run build` production build | ✅ Compiled successfully (Next.js 16.2.3 Turbopack) |
| `npm run lint` passes | ✅ Zero errors, zero warnings |
| TypeScript compiles (`--noEmit`) | ✅ No type errors |
| All UI component tests pass | ✅ 5 suites, 26 tests, 0 failures |
| App renders shell layout | ✅ AppBar header, Drawer sidebar, footer, content area |
| API client module exports typed functions | ✅ GET, POST, PUT, PATCH, DELETE with typed responses |
| localhost:3000 serves landing page | ✅ HTML response with "APIC Vibe Portal" content |
| Playwright e2e tests pass | ✅ 3 suites, 11 tests, 0 failures (app-shell, navigation, not-found) |
| E2E CI job configured | ✅ `e2e-frontend` job in `.github/workflows/ci.yml` |


## Coding Agent Prompt

```text
**Task**: Implement plan step 005 — Next.js Frontend Project Setup.

Read the full task specification at `docs/project/plan/005-frontend-nextjs-setup.md`.

Reference the architecture at `docs/project/apic_architecture.md` (Frontend: Next.js SPA) and the repo structure from `docs/project/plan/001-sprint-zero-repo-scaffolding.md`.

Scaffold a Next.js 16 application in `src/frontend/` using `create-next-app` with App Router and TypeScript 6.0 (do NOT use Tailwind CSS). Install Material UI (MUI) packages: `@mui/material`, `@mui/icons-material`, `@mui/lab`, `@emotion/react`, `@emotion/styled`. Configure a custom MUI theme with `ThemeProvider` and `CssBaseline` in the root layout. Create the application shell (root layout with `AppBar`, `Drawer` sidebar, footer), wrap/extend MUI components for portal-specific patterns (Button, TextField, Card, Chip, Skeleton) with tests, a typed BFF API client, and configure testing with Jest + React Testing Library.

Ensure the project integrates with the root npm workspace. Verify the dev server starts, the build succeeds, linting passes, and all tests pass.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/005-frontend-nextjs-setup.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
