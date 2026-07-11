# Valify Customer Feedback Portal

Read-only dashboard for Valify's account team: browse and filter public customer
feedback about KYC and onboarding friction, scraped and classified by the
Customer Feedback Monitor pipeline in the repo root.

This is Phase 10 of that project. See `../docs/HANDOFF.md` for full project
context, decisions, and current phase status.

## Stack

- Vite + React
- Tailwind CSS (utility classes) plus a custom design token layer
  (`src/styles/tokens.css`) for brand colors, spacing, and typography
- No backend: reads a single JSON file, `data/feedback.json`, produced daily
  by the repo's GitHub Actions pipeline

## Running locally

```bash
cd dashboard
npm install
npm run dev
```

Opens on `http://localhost:5173` (Vite's default). In development, the app
reads `public/sample-data.json`, mock data covering 5 clients, 18 reviews,
mixed Arabic and English, mixed sentiment and scope values. This exists so the
UI can be built and tested without needing the real Google Sheet or GitHub
Actions pipeline running.

## Data source

Controlled by `src/config.js` and the `VITE_DATA_URL` environment variable:

- Not set (local development): falls back to `/sample-data.json`.
- Set in production (Vercel): should point at `/api/data`, which `vercel.json`
  rewrites to the raw GitHub URL of `data/feedback.json`. Routing through a
  same-origin rewrite avoids CORS issues and keeps the raw GitHub URL out of
  the frontend bundle.

## Deploying (Vercel)

Deployment is done by connecting the Vercel web UI to this repo, not from the
CLI. Steps:

1. In the Vercel dashboard, import the `omaaradel/valify-customer-feedback`
   repository as a new project.
2. Set the project's root directory to `dashboard/`.
3. Framework preset: Vite.
4. Build command and output directory: leave at Vite defaults
   (`npm run build`, `dist`).
5. Add an environment variable: `VITE_DATA_URL` = `/api/data`.
6. Deploy.

If the repo is private, `raw.githubusercontent.com` will return 404 for
unauthenticated requests to `data/feedback.json`. Either make the repo public,
or add a GitHub token to the rewrite's request headers in `vercel.json` as a
Vercel environment variable (never hardcode a token in this file or anywhere
in source). This decision is left for Omar; see `docs/HANDOFF.md` for the
current status.

## Project structure

```
dashboard/
  public/
    sample-data.json          dev mock data
    valify-logo-white.png     white silhouette logo for the dark header
  src/
    main.jsx                  entry point
    App.jsx                   root component, data fetching
    config.js                 data source URL, feature flags
    hooks/
      useFilteredData.js      filter logic, memoized
    components/
      layout/                 Header, PageContainer
      summary/                SummaryCards, StatCard, ScopeSplitBar
      filters/                FilterBar, FilterPillGroup
      reviews/                ReviewList, ReviewCard, ClientAvatar, Badge, EmptyState
    styles/
      tokens.css              CSS custom properties: colors, spacing, typography
```
