# Apps Script — Booking handler

The booking form at `/book-trial` is configured to post to a Google Apps Script Web App. The repository source is designed to save each booking to Google Sheets and email hello@tarteelhouse.com.

## Status and scope

This file documents the repository implementation, not verified live behaviour. Booking reliability and backend hardening remain postponed/open. The deployed script version and a real end-to-end booking must be confirmed when that work resumes; do not assume repository changes are live.

## Files
- `Code.gs` — the full Apps Script. Source of truth.

## Setup reference (live deployment status must be confirmed)
1. Open the booking Google Sheet.
2. Extensions → Apps Script.
3. Paste the contents of `Code.gs` into `Code.gs` in the editor.
4. Save. Deploy → New deployment → **Web app**:
   - Execute as: **Me**
   - Who has access: **Anyone**
5. Copy the deployed `/exec` URL into the `action` attribute of the form in
   `/book-trial`.

## Updating the script
1. Edit `apps-script/Code.gs` in this repo.
2. Paste the updated contents into the bound Apps Script editor.
3. Save. Deploy → **Manage deployments** → pencil icon on the existing
   deployment → Version: **New version** → Deploy.
   The form URL does not change.

## Config to confirm before deploying
At the top of `Code.gs`:
- `NOTIFICATION_EMAIL` — where booking notifications are sent. Launch value:
  `hello@tarteelhouse.com`.
- `SUCCESS_REDIRECT` — fallback absolute URL of `/success`.
- `ALLOWED_REDIRECT_HOSTS` — production/staging hostnames allowed for the
  form's `success_redirect` value. `localhost` and `127.0.0.1` are allowed
  automatically for local testing.
- `SHEET_NAME` — tab name inside the spreadsheet. Defaults to `Bookings`.

## What the repository script is designed to do on each submission
1. Ignores the submission silently if the `website_field` honeypot is filled
   (spam bot).
2. Validates the required booking fields before writing to the sheet. Missing
   or invalid required fields return a short error page and are not saved.
3. Ensures the header row on the `Bookings` sheet contains all required
   columns — appends any missing ones to the right without disturbing
   existing data.
4. Appends a new row with the submitted values. The `status` column is set
   to **New lead**; `assigned_teacher`, `follow_up_date`, and
   `internal_notes` are left empty for the founder to fill in.
5. Sends a plain-text email to `NOTIFICATION_EMAIL` with all key booking
   details. `Reply-To` is set to the parent's email, so hitting reply
   responds straight to the parent.
6. Returns a short HTML page that immediately redirects to `/success`.
   The form can pass a `success_redirect` URL for local/staging/production;
   the script only uses it when the hostname is allowed and the path ends in
   `/success`. Otherwise it falls back to `SUCCESS_REDIRECT`.

## Required booking fields
The frontend and backend both require:

- `parent_name`
- `child_name`
- `child_age`
- `quran_level`
- `session_language`
- `country`
- `email`
- `whatsapp`
- `preferred_days`
- `preferred_time`
- `city_region`
- `consent` = `yes`

Optional fields:
- `notes` (also where parents can mention a preferred teacher)

## Sheet structure
Columns, left to right:

| # | Column              | Written by | Purpose                         |
|---|---------------------|------------|---------------------------------|
| 1 | `timestamp`         | Script     | Submission time                 |
| 2 | `source`            | Form       | Hidden field, always `website`  |
| 3 | `parent_name`       | Form       |                                 |
| 4 | `child_name`        | Form       |                                 |
| 5 | `child_age`         | Form       |                                 |
| 6 | `quran_level`       | Form       |                                 |
| 7 | `session_language`  | Form       |                                 |
| 8 | `country`           | Form       |                                 |
| 9 | `email`             | Form       |                                 |
| 10| `whatsapp`          | Form       | Required                        |
| 11| `preferred_days`    | Form       | Comma-separated                 |
| 12| `preferred_time`    | Form       |                                 |
| 13| `city_region`       | Form       | Required                        |
| 14| `notes`             | Form       | Optional; may include teacher preference |
| 15| `consent`           | Form       | `yes` when consent ticked       |
| 16| `status`            | Script/You | Defaults to `New lead`          |
| 17| `assigned_teacher`  | You        | Fill in when matching a teacher |
| 18| `follow_up_date`    | You        | YYYY-MM-DD                      |
| 19| `internal_notes`    | You        | Anything operational            |

If the existing sheet is missing any of the four operational columns, the
script adds them automatically on the next submission. To add them now
without waiting for a test booking, run the `initializeSheet` function
once from the Apps Script editor.

## Suggested Sheet polish (manual, one-time)
- On the `status` column, add a dropdown data validation with values:
  `New lead`, `Contacted`, `Trial scheduled`, `Trial done`, `Enrolled`,
  `Not a fit`, `Lost`. Keeps terminology consistent.
- Freeze row 1 (already done by the script on first run).
- Optional: conditional formatting on `status` so active leads stand out.
