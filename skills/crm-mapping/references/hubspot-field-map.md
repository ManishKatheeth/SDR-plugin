# HubSpot Field Map

Maps lead JSON fields to HubSpot contact and company properties.
Edit this file when your HubSpot schema changes. The crm-mapping skill re-reads
it fresh on every ingest run.

## Contact properties

| Lead field | HubSpot property | Type | Transform |
|---|---|---|---|
| `contact.email` | `email` | string | lowercase, strip whitespace |
| `contact.name` (first word) | `firstname` | string | title-case |
| `contact.name` (remaining) | `lastname` | string | title-case |
| `contact.title` | `jobtitle` | string | as-is |
| `contact.linkedin_url` | `hs_linkedin_bio` | string | as-is |
| `score` | `lead_score` | number | integer |
| `reason` | `lead_qualification_reason` | string | as-is |
| *(default)* | `lifecyclestage` | enum | always set to `lead` |
| *(default)* | `hs_lead_status` | enum | always set to `new` |
| *(default)* | `lead_source` | string | always set to `sdr-plugin` |

## Company properties

| Lead field | HubSpot property | Type | Transform |
|---|---|---|---|
| `company` | `name` | string | title-case |
| `domain` | `domain` | string | lowercase, strip `www.` prefix |
| `industry` | `industry` | enum | map to nearest HubSpot industry enum |
| `employee_count` | `numberofemployees` | number | integer |
| `funding_stage` | `hs_funding_stage` | string | title-case (custom property) |
| `country` | `country` | string | ISO 3166-1 alpha-2 code |
| `recent_funding` | `recent_funding_round` | bool | true/false (custom property) |

## Custom properties (must exist in your HubSpot portal)

Create these in HubSpot Settings → Properties before running ingest:

- Contact: `lead_score` (number)
- Contact: `lead_qualification_reason` (single-line text)
- Company: `hs_funding_stage` (single-line text)
- Company: `recent_funding_round` (checkbox / boolean)

## Industry enum mapping

| Lead industry value | HubSpot industry enum |
|---|---|
| SaaS / Cloud software | COMPUTER_SOFTWARE |
| MarTech | MARKETING_AND_ADVERTISING |
| SalesTech | COMPUTER_SOFTWARE |
| FinTech | FINANCIAL_SERVICES |
| Other B2B software | INFORMATION_TECHNOLOGY_AND_SERVICES |
