# Disqualifiers

Hard stops — if any of these match, mark the lead `qualified: false` regardless
of score. The qualification skill re-reads this file fresh on every run.

## Competitor companies

Do not prospect into direct competitors. Current list:

- (Add competitor domains here, e.g. `competitor.com`)

## Blacklisted domains / companies

Customers or partners we have an agreement not to prospect:

- (Add blacklisted domains here)

## Geography mandates

The following geographies are excluded from prospecting (compliance/legal):

- China (PRC)
- Russia
- Iran, North Korea, Syria (OFAC-sanctioned)

## Company stage

- Pre-revenue / pre-product companies (no product in market yet)
- Companies that raised their last round more than 4 years ago with no subsequent
  funding or acquisition signal

## Contact type

- Personal email addresses only (gmail, hotmail, yahoo, etc.) — no work email
  discoverable after enrichment
- Bot/catch-all emails (info@, hello@, contact@) unless it's the only option and
  the company score is ≥ 75

## Existing customers

Do not create a new outreach lead for a company that already has an open or
closed-won deal in HubSpot. Check by domain before scoring.

## Recent opt-out

Any contact or domain that has previously unsubscribed or asked to be removed
from outreach. This list should be maintained in HubSpot and checked at ingest
time by `hubspot_upsert.py`.
