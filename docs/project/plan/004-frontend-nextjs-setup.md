# 004 - Phase 1 MVP: Next.js Frontend Project Setup

## References
- [Architecture Document](../apic_architecture.md) — Frontend: Next.js SPA
- [Product Charter](../apic_product_charter.md) — Portal UI in scope
- [Product Spec](../apic_portal_spec.md) — UI feature requirements

## Overview
Scaffold the Next.js frontend application with App Router, TypeScript, Tailwind CSS, and a component library foundation. This establishes the UI project that all subsequent frontend tasks build upon.

## Dependencies
- **001** — Repository scaffolding (monorepo workspace structure)

## Implementation Details

### 1. Project Initialization
- Use `create-next-app` within `src/frontend/` with the following options:
  - TypeScript: Yes
  - App Router: Yes
  - Tailwind CSS: Yes
  - ESLint: Yes (extend root config)
  - Import alias: `@/`
- Ensure the project integrates with the root npm workspace.

### 2. Core Configuration
- **TypeScript**: Extend `tsconfig.base.json` from root; enable strict mode
- **ESLint**: Extend root ESLint config; add Next.js specific rules (`next/core-web-vitals`)
- **Prettier**: Use root Prettier config
- **Tailwind**: Configure with design tokens (colors, spacing, typography) aligned to portal branding
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
│   └── globals.css         # Tailwind imports + base styles
├── components/
│   ├── ui/                 # Reusable primitives (Button, Input, Card, etc.)
│   ├── layout/             # Header, Footer, Sidebar, Navigation
│   └── shared/             # Cross-cutting components
├── lib/
│   ├── api-client.ts       # BFF API client (fetch wrapper)
│   └── utils.ts            # Utility functions
├── hooks/                  # Custom React hooks
├── types/                  # TypeScript type definitions
└── __tests__/              # Test setup and utilities
```

### 4. Component Library Foundation
Create base UI components using Tailwind CSS:
- `Button` — Primary, secondary, ghost variants; loading state
- `Input` — Text input with label, error state, helper text
- `Card` — Content card with header, body, footer slots
- `Badge` — Status indicators (e.g., API lifecycle state)
- `Skeleton` — Loading placeholder component

### 5. Layout Components
- **Header**: App logo, search bar placeholder, user avatar placeholder
- **Sidebar/Navigation**: Collapsible navigation with route links
- **Footer**: Basic footer with links

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

## Coding Agent Prompt

> **Task**: Implement plan step 004 — Next.js Frontend Project Setup.
>
> Read the full task specification at `docs/project/plan/004-frontend-nextjs-setup.md`.
>
> Reference the architecture at `docs/project/apic_architecture.md` (Frontend: Next.js SPA) and the repo structure from `docs/project/plan/001-sprint-zero-repo-scaffolding.md`.
>
> Scaffold a Next.js 14+ application in `src/frontend/` using `create-next-app` with App Router, TypeScript, and Tailwind CSS. Create the application shell (root layout, header, sidebar, footer), base UI components (Button, Input, Card, Badge, Skeleton) with tests, a typed BFF API client, and configure testing with Jest + React Testing Library.
>
> Ensure the project integrates with the root npm workspace. Verify the dev server starts, the build succeeds, linting passes, and all tests pass.
