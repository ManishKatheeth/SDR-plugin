# De-Duplication Policy

Defines the order of operations for deciding whether to create, update, or skip
a lead during HubSpot ingest. Edit this file when your de-dupe strategy changes.
The crm-mapping skill re-reads it fresh on every ingest run.

## De-dupe order of operations

1. **Email match (contact level).**
   Search HubSpot for an existing contact with the same email address.
   - Found → status = `updated`. Patch the contact with any new/changed fields.
     Do not overwrite `lifecyclestage` if it's past `lead`.
   - Not found → proceed to step 2.

2. **Domain match (company level).**
   Search HubSpot for a company with the same domain.
   - Found → check if any existing contact at that company shares the same full
     name (firstname + lastname). If yes → `updated`. If no → `upserted` (create
     new contact, associate with existing company).
   - Not found → `upserted` (create both new contact and new company).

3. **Opt-out check.**
   Before any write, check whether the contact email or company domain appears
   in the HubSpot `hs_email_optout` flag or a suppression list.
   - Opted out → status = `skipped`, reason = `opted out`.
   - Never create or update a contact who has opted out.

## Edge cases

- **Duplicate emails in the same ingest batch:** if two leads in the same run
  share the same email, process the one with the higher score first; mark the
  second `skipped` with reason `duplicate in batch`.
- **Company domain mismatch:** if the lead's domain doesn't match the domain of a
  company found by name, create a new company rather than associating with the
  wrong one.
- **Missing email:** if no email is available, match on company domain + full
  name only. If still ambiguous, create new and flag for manual review.
- **Existing deal:** if the contact or company has an open or closed-won deal,
  status = `skipped`, reason = `existing deal`.
