# Understanding API Governance

API Governance in the APIC Vibe Portal AI measures and tracks the quality, compliance, and operational readiness of each API in your catalog. This guide explains what the scores mean and how to use them.

## What Is API Governance?

Governance is the practice of ensuring APIs meet organizational standards for:

- **Documentation completeness** — Does the API have a clear description, contact info, and external docs?
- **Versioning discipline** — Are versions properly labeled and lifecycles managed?
- **Security standards** — Are authentication requirements documented?
- **Operational readiness** — Are deployment environments registered?

Poor governance means developers struggle to discover, understand, and safely adopt an API.

## The Governance Dashboard

Navigate to **Governance** in the left sidebar to access the dashboard at `/governance`.

### Summary KPIs

At the top of the page, four KPI cards show the overall health of your API catalog:

| Card                | Description                                      |
| ------------------- | ------------------------------------------------ |
| **Overall Score**   | Weighted average across all APIs (0–100)         |
| **Compliant APIs**  | Count of APIs with score ≥ 75                    |
| **Critical Issues** | Count of APIs with one or more critical failures |
| **Trend**           | Score change vs. the previous period             |

### Score Distribution Chart

The donut chart shows how APIs are distributed across score categories:

| Category              | Score Range |
| --------------------- | ----------- |
| **Excellent**         | 90–100      |
| **Good**              | 75–89       |
| **Needs Improvement** | 50–74       |
| **Non-Compliant**     | 0–49        |

### API Scores Table

The table lists all APIs with their:

- **Governance score** (0–100)
- **Category** label
- **Critical failures** count
- **Last checked** date

Click any row to view the **Compliance Detail** for that API.

## Compliance Detail Page

The compliance detail page (reached by clicking an API row in the governance dashboard) shows:

### Check Results

Each governance check is listed with:

| Column             | Description                    |
| ------------------ | ------------------------------ |
| **Check name**     | What is being validated        |
| **Status**         | ✅ Passed or ❌ Failed         |
| **Severity**       | Critical / High / Medium / Low |
| **Message**        | What was found                 |
| **Recommendation** | How to fix the issue           |

### Severity Levels

| Level        | Meaning                                                              |
| ------------ | -------------------------------------------------------------------- |
| **Critical** | Blocks adoption — must be fixed before the API is used in production |
| **High**     | Significantly impacts developer experience                           |
| **Medium**   | Best-practice improvement recommended                                |
| **Low**      | Minor improvement                                                    |

## Interpreting Your Score

| Score  | Recommendation                                                |
| ------ | ------------------------------------------------------------- |
| 90–100 | ✅ Excellent — safe to adopt                                  |
| 75–89  | ✅ Good — minor improvements possible                         |
| 50–74  | ⚠️ Needs improvement — review recommendations before adopting |
| 0–49   | ❌ Non-compliant — do not use in production until fixed       |

## How to Improve an API's Score

1. Navigate to the **Compliance Detail** page for the API
2. Focus on **Critical** and **High** severity failures first
3. Follow the **Recommendation** text for each failed check
4. Work with the API owner to make the changes in Azure API Center
5. Trigger a re-evaluation (scores refresh automatically on a schedule, or contact your admin for an on-demand check)

## Using AI to Understand Governance Issues

On the Governance Dashboard or Compliance Detail page, use the **AI Assistant** to ask:

```
Why did the Payments API fail the "has-description" check?
What does it mean to have a critical governance failure?
How do I fix the missing contact information check?
```

## Who Can View Governance Data?

- **All authenticated users** can view governance scores and compliance details
- **Portal.Admin / Portal.Maintainer** roles have access to trigger re-evaluations (when supported)

## Related Guides

- **[Getting Started](getting-started.md)**
- **[Using the AI Chat](using-ai-chat.md)**
- **[Comparing APIs](comparing-apis.md)**
