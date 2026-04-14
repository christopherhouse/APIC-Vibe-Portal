# 027 - Phase 3: Analytics Dashboard

## References
- [Architecture Document](../apic_architecture.md) — Frontend: Next.js SPA; data visualization
- [Product Charter](../apic_product_charter.md) — Phase 3: Analytics; increased portal adoption as success metric
- [Product Spec](../apic_portal_spec.md) — Analytics dashboard requirements

## Overview
Build the analytics dashboard that provides portal administrators and API owners with insights into portal usage, API popularity, search effectiveness, and user engagement patterns.

## Dependencies
- **004** — Frontend project setup
- **026** — Analytics data collection (data source)
- **016** — Entra ID authentication (admin role for dashboard access)

## Implementation Details

### 1. Dashboard Page Structure
```
app/analytics/
├── page.tsx                    # Analytics overview dashboard
├── loading.tsx
├── search/
│   └── page.tsx                # Search analytics deep-dive
├── apis/
│   └── page.tsx                # API popularity analytics
├── users/
│   └── page.tsx                # User engagement analytics
└── components/
    ├── AnalyticsOverview.tsx           # KPI summary cards
    ├── TimeRangeSelector.tsx           # Date range picker
    ├── UsageTrendChart.tsx             # Portal usage over time
    ├── PopularApisChart.tsx            # Most viewed APIs
    ├── SearchQueryCloud.tsx            # Search term word cloud/list
    ├── SearchEffectivenessChart.tsx    # Search click-through rates
    ├── UserEngagementChart.tsx         # Active users over time
    ├── FeatureUsageChart.tsx           # Feature adoption (search, chat, compare)
    ├── ApiTrafficTable.tsx             # API views/downloads table
    └── ExportButton.tsx               # Export analytics data
```

### 2. Analytics Overview (main dashboard)
KPI Cards:
- **Total Users**: Unique users in selected time range (with trend)
- **Page Views**: Total page views (with trend)
- **Search Queries**: Total searches performed (with trend)
- **Chat Interactions**: Total AI chat messages (with trend)
- **Average Session Duration**: Mean time on portal

Charts:
- **Usage Trend**: Line chart of daily active users over time
- **Feature Adoption**: Stacked area chart showing catalog/search/chat/compare usage
- **Top 10 APIs**: Horizontal bar chart of most viewed APIs
- **Search Terms**: Top search queries list with frequency

### 3. Search Analytics (`/analytics/search`)
- **Query Volume**: Searches per day/week trend line
- **Top Queries**: Most frequent search terms with result counts
- **Zero Result Queries**: Searches that returned no results (opportunities for improvement)
- **Click-Through Rate**: Percentage of searches leading to API views
- **Search Mode Distribution**: Keyword vs. Semantic vs. Hybrid usage
- **Average Results Clicked**: Mean number of results viewed per search

### 4. API Popularity Analytics (`/analytics/apis`)
- **Most Viewed APIs**: Ranked list with view counts and trends
- **Most Downloaded Specs**: APIs with most specification downloads
- **Most Discussed (Chat)**: APIs most frequently referenced in chat
- **API Discovery Path**: How users find APIs (catalog browse vs. search vs. chat)
- **New API Awareness**: Time from API creation to first user view

### 5. User Engagement Analytics (`/analytics/users`)
- **Active Users**: Daily/weekly/monthly active user counts
- **Session Duration Distribution**: Histogram of session lengths
- **Pages Per Session**: Average pages viewed per visit
- **Return Rate**: Percentage of returning vs. new users
- **Feature Adoption**: Which features different user segments use
- **User Journey Flows**: Common navigation paths (Sankey diagram optional)

### 6. Time Range Selection
- Predefined ranges: Last 7 days, 30 days, 90 days, Year
- Custom date range picker
- All charts update based on selected range
- Comparison to previous period (optional)

### 7. Data Export
- Export chart data as CSV
- Export dashboard summary as PDF (optional)
- Scheduled email reports (future enhancement placeholder)

### 8. Access Control
- Dashboard requires `Portal.Admin` or `API.Owner` role
- API owners see analytics scoped to their APIs
- Admins see organization-wide analytics

## Testing & Acceptance Criteria
- [ ] Analytics overview page displays KPI cards with correct data
- [ ] Usage trend chart renders accurately for selected time range
- [ ] Top APIs chart shows most viewed APIs in correct order
- [ ] Search analytics page shows query volume and top terms
- [ ] Zero result queries are identified and listed
- [ ] User engagement page shows active user trends
- [ ] Time range selector updates all charts
- [ ] CSV export downloads correct data
- [ ] Dashboard is admin/API-owner only (403 for regular users)
- [ ] Charts handle empty/sparse data gracefully
- [ ] All components have unit tests
- [ ] Dashboard loads within 3 seconds

## Coding Agent Prompt

> **Task**: Implement plan step 027 — Analytics Dashboard.
>
> Read the full task specification at `docs/project/plan/027-analytics-dashboard.md`.
>
> Reference `docs/project/plan/026-analytics-data-collection.md` for the analytics data source and endpoints, `docs/project/plan/004-frontend-nextjs-setup.md` for the frontend structure, and `docs/project/plan/016-entra-id-authentication.md` for admin role gating.
>
> Build the analytics dashboard with: overview page (KPI cards, usage trends, top APIs), search analytics deep-dive (query volume, zero-result queries, click-through rates), API popularity analytics, user engagement analytics, time range selection, and CSV export. Use a charting library consistent with the governance dashboard (task 023). Gate access to admin/API-owner roles.
>
> Write unit tests for all components. Verify the build succeeds, linting passes, and all tests pass.
