# Build steps implemented

1. Define scope: hospitals and their branches are customers; patient-identifying data is outside scope.
2. Create Supabase authentication, application profiles, four roles, location assignments, and row-level security.
3. Create customer, branch, fixed-duration contract, contract service, usage, invoice, and payment tables.
4. Create a movement-ledger inventory model so available, quarantined, consumed, expired, and disposed quantities are calculated rather than manually typed totals.
5. Add warehouse receipts, hospital transfers, delivery slips, hospital consumption, lot tracking, expiry alerts, low-stock alerts, estimated runs, and estimated working days.
6. Add kit definitions, unique kit IDs, run balances, component requirements, issue reporting, action history, and resolution verification.
7. Add detailed downtime, monthly aggregation, lost runs, affected services, backdated-entry reasons, admin notifications, and approval records.
8. Add hospital-focused customer pages with contracts, quarterly results, current inventory, usage, deliveries, downtime, and invoices.
9. Add management dashboards, CSV exports, and a Gemini section that receives aggregate operational data only.
10. Add friendly missing-secret handling, setup documentation, automated checks, and Streamlit Cloud deployment files.

The catalogue numbers supplied during requirements gathering remain unchanged. Mannose and WFI catalogue numbers are intentionally `NULL` and can be added later from Administration.
