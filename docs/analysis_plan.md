# Analysis Plan: Email Campaign A/B Test

**Status:** Approved before results were analysed · **Author:** Sowmya Kota · **Stakeholder:** CRM Marketing Manager

> This plan was written and committed **before** comparing outcomes between groups. Fixing metrics, tests and success criteria in advance prevents choosing the analysis that gives the most attractive answer.

## 1. Business question

A retailer emailed 64,000 recent customers as a test. Marketing must decide for the next campaign:

1. Should we send the **Men's** email, the **Women's** email, or neither?
2. Should we send it to **everyone** or only to **specific customer groups**?

## 2. Experiment design (as run)

| Item | Detail |
|---|---|
| Population | 64,000 customers who purchased in the last 12 months |
| Unit of randomisation | Customer |
| Groups | Men's email · Women's email · No email (control), about 1/3 each, randomly assigned |
| Measurement window | 2 weeks after the email |
| Data | One row per customer: profile before the campaign + outcomes after |

## 3. Hypotheses

| ID | Comparison | Question |
|---|---|---|
| H1 | Men's email vs No email | Does the Men's email increase revenue per customer? |
| H2 | Women's email vs No email | Does the Women's email increase revenue per customer? |
| H3 *(secondary)* | Men's vs Women's email | If both work, which works better? |

## 4. Metrics

**Primary (decision metric):** **Revenue per customer**: average `spend` across *all* customers in a group, including those who spent $0.

**Secondary (explains the primary):** **Conversion rate**: share of customers who purchased.

**Diagnostic (where in the funnel the effect happens):**
- Visit rate
- Average spend per buyer (spend among converters only)

Relationship: *Revenue per customer = Conversion rate × Average spend per buyer.*

## 5. Statistical approach

| Metric | Test | Interval |
|---|---|---|
| Revenue per customer | Welch's t-test | Bootstrap 95% CI (10,000 resamples), because spend is mostly zeros and right-skewed |
| Conversion, visit | Two-proportion z-test | 95% CI for the difference |

- Report **absolute lift** (e.g. +$0.50 per customer) and **relative lift** (e.g. +80%).
- **Multiple comparisons:** H1 and H2 both test against the same control, so the Holm–Bonferroni correction is applied at overall α = 0.05.
- H3 and all segment results are **exploratory**: reported with intervals, not used alone to make a decision.

## 6. Validity checks (run before any results)

| Check | Rule | If it fails |
|---|---|---|
| Sample ratio mismatch | Chi-square test of group sizes vs equal thirds | p < 0.001 → stop and investigate randomisation |
| Covariate balance | Standardised mean difference of each pre-campaign feature across groups | Any |SMD| > 0.1 → flag and adjust |
| Data logic | `conversion ≤ visit`; `spend > 0` only when `conversion = 1`; no negatives or missing | Investigate and document |

## 7. Success criteria

An email is a **success** if, for revenue per customer vs control:
1. The Holm-adjusted test is significant at α = 0.05, **and**
2. The 95% confidence interval for the lift is entirely above $0.

**Practical significance:** report incremental revenue **per 1,000 emails sent**. Email cost is not in the data, so the readout states the **break-even cost per email** (the cost at which incremental revenue equals cost) and leaves the cost judgement to the business.

## 8. Segment analysis (exploratory, pre-specified)

Segments chosen in advance, so we don't search every possible split for a good-looking result:

- Past purchase category: Men's only · Women's only · Both
- Recency: 1–3 · 4–6 · 7–9 · 10–12 months since last purchase
- Past 12-month spend (`history_segment`)
- Purchase channel: Phone · Web · Multichannel
- Location: Urban · Suburban · Rural
- New vs existing customer

Rules: report a segment only if each group in it has at least 1,000 customers; segment results inform the targeting recommendation and are labelled as hypotheses to confirm in the next campaign.

## 9. Known limitations

- Data is from 2008; behaviour may differ today. The project demonstrates the method, not current customer behaviour.
- 2-week window only; long-term effects are not measured.
- No unsubscribe, complaint or email cost data, so possible harms of over-emailing cannot be measured.
- No product-level data.

## 10. Deliverables

1. Data quality and validity report
2. Main results: H1–H3 with lifts and confidence intervals
3. Segment analysis and a targeting recommendation with estimated revenue impact
4. One-page readout for leadership
5. "Ask the Experiment": an AI assistant that answers questions only from the computed results, cites its source table, and is evaluated for accuracy
