# parseRawData observed shapes (AU-6 snapshot)

From the AU-2 audit run on 2026-04-23 across 525 sampled records.

| Field | Observed shapes | Notes |
|---|---|---|
| `inventors` | `array_of_strings` (most), `newline_string` (some Flintbox legacy), `comma_string` (rare) | Dual output: `inventors[]` + `inventorsText` |
| `key_points` | `array_of_strings` (newer Flintbox), `newline_string` | Dual output |
| `applications` | `array_of_strings`, `plain_string`, `newline_string` | Dual output exists pre-AU-6 |
| `advantages` | `array_of_strings`, `plain_string` (JHU), `newline_string` | Dual output exists pre-AU-6 |
| `publications` | `array_of_objects` (`{text,url}`), `html_string`, `plain_string` | Dual output exists pre-AU-6 |
| `contacts` | `array_of_objects` (`{name,email,phone}`) | `contactsList` only |
| `researchers` | `array_of_objects`, `newline_string` (legacy) | Dual handling pre-AU-6 |
| `documents` | `array_of_objects` (`{name,url,size?}`) | Array-only |
| `supporting_documents` | `array_of_objects` | Array-only |
| `flintbox_tags` | `array_of_strings`, rarely `newline_string` | Dual output added in AU-6 |
| `client_departments` | `array_of_strings`, rarely `newline_string` | Dual output added in AU-6 |
| `technology_validation` | `array_of_strings`, rarely `newline_string` | Dual output added in AU-6 |
| `development_stage` | `plain_string` (JHU), `array_of_strings` (UPenn, WayneState: 18 records audited) | `developmentStage` (joined) + `developmentStageList` added in AU-6 |
| `related_portfolio` | `array_of_objects` (`{title,url}`) | Array-only |
| `licensing_contact` | `object` | Already handled |
| `contact` (singular) | `object` | Already handled |

## AU-6 contract

- **Additive only.** No existing field names or shapes changed.
- Every field that can be string-or-array exposes both `<field>` (array if array, undefined otherwise) and `<field>Text` (string if string, or joined if array fallback).
- `development_stage` uses `stringOrList` (always produces a string + optional list) because the UI renders it inline rather than as a list section.
- `stripHtml` untouched — renderers keep deciding how to strip.
