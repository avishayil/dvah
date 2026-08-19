# DVAH Web UI

A dark, IDE-style front-end for the Damn Vulnerable Agent Harness: browse labs, patch
the vulnerable code in an in-browser editor, run the suite in a sandbox, visualize the
security trace, and get help when stuck (tiered hints, guided walkthrough, optional AI
tutor).

## Stack
Next.js (App Router, TS) · Tailwind · Radix/shadcn-style UI · Monaco · TanStack Query.

## Develop
```bash
npm install
cp .env.example .env.local          # point NEXT_PUBLIC_API_BASE at the DVAH API
# in another shell, start the backend:  uv run uvicorn dvah.webapi.app:app --port 8000
npm run dev                         # http://localhost:3000
```

## Test
```bash
npm test        # Vitest component tests (CI)
npm run e2e     # Playwright browser flow — MANUAL ONLY, excluded from CI; needs API + dev server
```

## Screens
- `/` — lab catalog (scannable board, learn/ctf toggle, invariant reference).
- `/labs/[id]` — workspace: briefing · Monaco editor · run panel + invariant board · trace graph · help drawer.
- `/mutate` — chaos engine: toggle hidden invariant defeats and diagnose which broke.

The API contract lives in `lib/api.ts` / `lib/types.ts`.
