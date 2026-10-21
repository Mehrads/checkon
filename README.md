# Ontario Job Posting Checker

Checks a job posting against Ontario's 2026 job posting rules and suggests a compliant rewrite. Product and design docs: `01-PRD.md`, `02-Technical-Design.md`, `03-Research-and-Interview-Guide.md`, `04-V1-Scope.md`.

Built on the [Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template) (MIT): FastAPI, SQLModel, Postgres, React with Vite and TypeScript. The compliance core is in `backend/app/compliance/`; see `backend/README.md`.

## Run it locally

1. Copy the settings and add a personal Claude API key:

   ```bash
   cp .env.example .env
   ```

   Then set `ANTHROPIC_API_KEY` in `.env`, and replace the `changethis` values.

2. Start Postgres and apply the migrations:

   ```bash
   docker compose up -d db
   ```

   ```bash
   cd backend && uv run alembic upgrade head
   ```

3. Build the frontend once; the backend serves it:

   ```bash
   bun install && cd frontend && bun run build
   ```

4. Start the backend and open http://localhost:8000:

   ```bash
   cd backend && uv run fastapi dev
   ```

For frontend work with hot reload, run `bun run dev` in `frontend/` and open http://localhost:5173. After changing the API, regenerate the client with `bash scripts/generate-client.sh`.

## Free check limits

- **No CAPTCHA:** v1 has no bot check (decided 2026-10-20). The quota, rate limit and spend cap bound what a script can cost; the worst case is free checks pausing for the rest of the day.
- **Quota:** `FREE_CHECKS_PER_WEEK` per visitor cookie and per IP, stored in Postgres as HMACs. Rejected inputs don't use a check.
- **Spend cap:** `FREE_CHECK_DAILY_SPEND_CAP_USD`, measured from the token counts the API reports.
- **Behind a proxy (Cloud Run):** start the server with `--forwarded-allow-ips` set, or every visitor shares the proxy's IP.

## Deploy

The GCP setup (Terraform, GitHub Actions and the runbook) is in `infra/README.md`.

## Tests

```bash
cd backend && uv run pytest
```

The compliance tests (`backend/tests/compliance/`) need nothing else. The template's tests (`tests/api`, `tests/crud`) need Postgres running and migrated.
