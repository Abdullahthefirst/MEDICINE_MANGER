# Medicine Manager

A Streamlit and Supabase application for managing hospital customers, fixed-duration contracts, consumable inventory, deliveries, usage, kit components, downtime, invoices, and quarterly management reporting.

The application treats every hospital branch as its own customer with one location. It stores only operational patient counts when useful; it does not require patient names, diagnoses, or clinical records.

## Included features

- Email/password login using Supabase Auth.
- Roles: administrator, management viewer, hospital staff, and warehouse staff.
- Per-user warehouse or hospital location assignment with database row-level security.
- Hospital customers and branch-specific fixed-duration contracts.
- Contract services, usage, invoices, payments, balances, and quarterly summaries.
- Inventory receipts, transfers, consumption, quarantine, release, expiry, and disposal.
- Dynamic balances calculated from an append-only movement ledger.
- Lot numbers, manufacturer catalogue numbers, origin, delivery slips, expiry alerts, reorder alerts, estimated runs, and estimated working days.
- Unique kit IDs, two/four-run kit tracking, component requirements, component issues, resolution actions, and verified status history.
- Detailed downtime plus monthly totals, affected services, lost runs, corrective/preventive actions, backdated-entry requests, and administrator alerts.
- Optional Gemini operational analysis using aggregate application data only.
- CSV exports for the main management datasets.

## 1. Create the Supabase database

Create a new Supabase project. Open **SQL Editor**, paste all of `supabase/full_schema.sql`, and run it once.

If you already installed the earlier step-by-step database from this project discussion, run only `supabase/app_setup.sql` to add the latest application views, atomic inventory function, catalogue field, kit-status refresh, and backdate alerts.

Do not run `full_schema.sql` over an unrelated production database: its policy-installation section replaces policies on the Medicine Manager tables.

## 2. Create the first administrator

In Supabase, open **Authentication > Users** and create an email/password user. Copy its UUID. In SQL Editor run:

```sql
insert into public.profiles (id, full_name, role)
values ('PASTE-AUTH-USER-UUID', 'Administrator', 'admin');
```

Sign in as this administrator. Additional Auth users are created in Supabase Authentication, then registered on **Administration > Users & locations** using the same UUID. Assign hospital and warehouse staff to their permitted stock location on that tab.

## 3. Configure local secrets

From the project folder:

```bash
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_PUBLISHABLE_OR_ANON_KEY"

# Optional organization-wide configuration
GEMINI_API_KEY = ""
GEMINI_MODEL = "gemini-2.5-flash"
```

Use the publishable/anon key, never the Supabase service-role key. Row-level security is designed to work with the signed-in user's access token.

The previous `KeyError: SUPABASE_URL` is now handled by a configuration screen, but the app still needs both Supabase values to connect.

## 4. Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## 5. Deploy to Streamlit Community Cloud

1. Push this project folder to a private GitHub repository. Do not commit `.streamlit/secrets.toml`.
2. Create a Streamlit Community Cloud app with `app.py` as the entry point.
3. In the app's **Settings > Secrets**, paste the TOML values shown above.
4. Deploy, sign in with the administrator account, register the remaining profiles, and assign staff locations.

## Normal operating order

1. Administration: confirm customers, stock locations, user assignments, items, catalogue numbers, kit definitions, and contract services.
2. Customer Management: create the fixed-duration customer contract.
3. Data Entry: receive stock into the warehouse, dispatch it to a hospital, record customer usage, then record consumable usage.
4. Kit Issues and Downtime: record each event and its detailed resolution history.
5. Finance: create a draft invoice, add unbilled usage, issue it, then record payments.
6. Overview and Customer Management: review current and quarterly results, expiry risks, open issues, and downtime.

## Catalogue-number notes

These manufacturer catalogue numbers are seeded exactly as supplied: `12759`, `15115`, `14225`, `12144`, `1785`, `11665`, and `2132`. The `manufacturer_cat_number` field is nullable and not unique because the supplied data uses `12759` for both Dual and Quad cassette records. Mannose and WFI are seeded without guessed numbers; an administrator can add them later without a schema change.

## Testing

```bash
python -m compileall -q .
pytest -q
```

The project includes no real secrets or patient records.
