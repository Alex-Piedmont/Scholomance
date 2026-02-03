# Project Instructions

## Scraper Development

**CRITICAL: When you encounter an error or display issue while working on a scraper, you MUST read `scraper_errors.md` FIRST before investigating.** The same or similar issue has likely already been solved for another scraper. Check the log for known solutions before spending time debugging.

- Error/solution log: `scraper_errors.md`
- Scraper approval tracking: `SCRAPER_PLAN.md`
- Frontend section rendering is driven by `raw_data` field names mapped in `web/src/components/Detail/parseRawData.ts`
- Database: PostgreSQL `tech_transfer`, technologies table with JSONB `raw_data` column
- API server: port 8001; Frontend: port 5173
