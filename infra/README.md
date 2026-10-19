# Deploying to GCP

Step 7 of `../04-V1-Scope.md`: the lean launch stack from Technical Design §12–13, in Toronto (`northamerica-northeast2`).

| Piece | Where |
| --- | --- |
| Cloud Run service (one instance, one worker), Cloud SQL Postgres `db-g1-small`, Secret Manager, Artifact Registry, Workload Identity Federation for GitHub | `terraform/` |
| Tests on every push and pull request | `../.github/workflows/test.yml` |
| Deploy on every push to `main`: test, build, migrate, deploy | `../.github/workflows/deploy.yml` |

Expected fixed cost: about $41 a month (Cloud SQL about $31, Cloud Run about $5, the rest storage and domain), before model fees.

## Before you start

- **A GCP project on your personal account**, with billing on. Keep the work account and work organisation out of it (PRD §10, employment contract).
- **A private GitHub repository** for this code, on your personal account.
- **A Cloudflare Turnstile site** for your domain: you need its site key and secret key.
- **A personal Anthropic API key**, on terms with no training on inputs (Technical Design §7).
- `gcloud` and `terraform` installed.

## First deploy

1. Sign in with your personal Google account and pick the project:

   ```bash
   gcloud auth login && gcloud auth application-default login
   ```

   ```bash
   gcloud config set project YOUR-PROJECT-ID
   ```

2. Fill in the Terraform settings:

   ```bash
   cd infra/terraform && cp terraform.tfvars.example terraform.tfvars
   ```

   The state file will hold the generated database password and app secret. For anything beyond a solo setup, store it in a GCS bucket only you can read (`backend "gcs"` in `versions.tf`).

3. Create the stack. The first apply runs Google's hello image, so the service exists before any deploy:

   ```bash
   terraform init && terraform apply
   ```

4. Add the two secrets Terraform doesn't hold. They start as `replace-me`:

   ```bash
   printf %s "YOUR-ANTHROPIC-KEY" | gcloud secrets versions add posting-checker-anthropic-api-key --data-file=-
   ```

   ```bash
   printf %s "YOUR-TURNSTILE-SECRET" | gcloud secrets versions add posting-checker-turnstile-secret-key --data-file=-
   ```

5. Set `public_url` in `terraform.tfvars` to the `service_url` output (or your domain), then apply again. The app uses it for the origin check.

   ```bash
   terraform apply
   ```

6. In GitHub, under Settings > Secrets and variables > Actions > Variables, add:

   | Variable | Value |
   | --- | --- |
   | `GCP_PROJECT_ID` | your project id |
   | `GCP_REGION` | `northamerica-northeast2` |
   | `GCP_WORKLOAD_IDENTITY_PROVIDER` | `terraform output -raw workload_identity_provider` |
   | `GCP_DEPLOYER_SERVICE_ACCOUNT` | `terraform output -raw deployer_service_account` |
   | `TURNSTILE_SITE_KEY` | the site key from Cloudflare |

   Then create an environment named `production`. Add yourself as a required reviewer if you want to approve each deploy.

7. Push to `main`. The Deploy workflow tests, builds the image, runs the migrations as a Cloud Run job, then deploys.

8. Smoke-test the live site: run one real check, then a second one to see the weekly limit. In the Cloud Run logs, confirm requests show real visitor IPs. If they all show one Google address, adjust `TRUSTED_PROXY_HOPS`.

## Before launch (v1 "done when")

- The release gates in Technical Design §8 pass on the English golden set.
- The lawyer has signed off every rule marked `interpretation` and the wording library. Record it in `backend/rulepacks/CA-ON/rules.yaml` and `wording.yaml` (`reviewed_by`, `reviewed_on`), then update `test_interpretation_rules_are_not_signed_off_yet`.
- The live API tests pass with your key (`RUN_LIVE_LLM=1`, see `backend/README.md`).
- Real Turnstile keys are in place; the test keys in `.env.example` and `frontend/.env` are for local work only.

## Known limits of this setup

- **One instance, one worker.** Checks in progress and the rate limit live in the app's memory, so Cloud Run is capped at one instance. To scale, move the check store to Postgres first.
- **The checker refuses everything until both manual secrets are set.** With `replace-me`, Turnstile fails and the model calls fail.
- **Organisation policies can block public access.** If your project sits in an organisation that forbids `allUsers`, the public invoker binding fails.
- **Postgres version mismatch.** Cloud SQL runs Postgres 17 by default; local development runs 18. Switch `postgres_version` when Cloud SQL offers 18.
- **Deletion protection is on** for the database and the service. Turn it off in Terraform before `terraform destroy`.
- **Langfuse isn't wired in yet** (Technical Design §12). Add it before you rely on traces for the golden-set runs.
