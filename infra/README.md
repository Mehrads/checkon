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
- **The checkon.ca domain** at Wix, and the **info@checkon.ca** Google Workspace mailbox (see [Email and DNS](#email-and-dns)).
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

4. Add the Anthropic key, which Terraform doesn't hold. It starts as `replace-me`:

   ```bash
   printf %s "YOUR-ANTHROPIC-KEY" | gcloud secrets versions add posting-checker-anthropic-api-key --data-file=-
   ```

   For contact-form emails, also add the app password for info@checkon.ca ([Email and DNS](#email-and-dns), step 3). `terraform.tfvars.example` already has the Gmail SMTP settings. Without the password, messages are still saved in the `contact_message` table.

   ```bash
   printf %s "YOUR-APP-PASSWORD" | gcloud secrets versions add posting-checker-smtp-password --data-file=-
   ```

5. Point checkon.ca at the service. Cloud Run's own domain mapping isn't offered in Toronto, so `lb.tf` puts a global HTTPS load balancer in front (about $18 a month, the load balancer line in Technical Design §13). Set `domain = "checkon.ca"` and `public_url = "https://checkon.ca"` in `terraform.tfvars` and apply. It also tells the app to read the visitor's IP one hop further back (`TRUSTED_PROXY_HOPS`).

   ```bash
   terraform apply && terraform output -raw lb_ip
   ```

   In Wix, replace the three Wix `A` records on `checkon.ca` with one `A` record to that address, and point the `www` `CNAME` at `checkon.ca` (both start on Wix's parking page). Leave the `MX` and `TXT` records alone; they carry the email. Google issues the certificate once both names resolve to the load balancer, usually within an hour; until then HTTPS on checkon.ca fails to connect. `www.checkon.ca` redirects to `checkon.ca`, and plain HTTP redirects to HTTPS.

6. In GitHub, under Settings > Secrets and variables > Actions > Variables, add:

   | Variable | Value |
   | --- | --- |
   | `GCP_PROJECT_ID` | your project id |
   | `GCP_REGION` | `northamerica-northeast2` |
   | `GCP_WORKLOAD_IDENTITY_PROVIDER` | `terraform output -raw workload_identity_provider` |
   | `GCP_DEPLOYER_SERVICE_ACCOUNT` | `terraform output -raw deployer_service_account` |
   | `CONTACT_EMAIL` | `info@checkon.ca` |
   | `UMAMI_WEBSITE_ID` | optional: the website id from Umami Cloud, for visit counts |

   Then create an environment named `production`. Add yourself as a required reviewer if you want to approve each deploy.

7. Push to `main`. The Deploy workflow tests, builds the image, runs the migrations as a Cloud Run job, then deploys.

8. Smoke-test the live site: run one real check, then a second one to see the weekly limit. In the Cloud Run logs, confirm requests show real visitor IPs. If they all show one Google address, adjust `TRUSTED_PROXY_HOPS`.

## Email and DNS

checkon.ca is registered at Wix (Domains > checkon.ca > Manage DNS Records). The mailboxes are Google Workspace Starter, bought through Wix.

| Record | State |
| --- | --- |
| `MX` to Google, SPF `TXT` (`include:_spf.google.com`), Google site verification `TXT` | In place |
| DMARC: `TXT` on `_dmarc.checkon.ca`, `v=DMARC1; p=none; rua=mailto:info@checkon.ca` | Added 2026-10-19. Monitor-only: nothing is blocked, daily reports go to info@checkon.ca |
| DKIM: `TXT` on `google._domainkey.checkon.ca` | Added 2026-10-19. Turn it on in Google Admin, step 1 below |
| Website: `A` on `checkon.ca`, `CNAME` on `www` | Still Wix parking, replaced in [First deploy](#first-deploy) step 5 |

1. **DKIM.** The record is in Wix and resolves. In Google Admin, signed in as info@checkon.ca: Apps > Google Workspace > Gmail > Authenticate email, then click Start authentication. If you ever generate a new key there, replace the `TXT` value in Wix to match.
2. **2-Step Verification** for info@checkon.ca (myaccount.google.com > Security). Gmail only gives app passwords once it is on.
3. **App password** for info@checkon.ca (myaccount.google.com > Security > App passwords, name it `checkon-contact-form`). Store it with the `posting-checker-smtp-password` command in [First deploy](#first-deploy) step 4. Don't paste it anywhere else.
4. **Tighten DMARC** once a few weeks of reports show only Google sending for checkon.ca: change `p=none` to `p=quarantine`.

Check any record from a terminal. This asks Google's public DNS over HTTPS, so a local resolver can't hide the answer (plain `dig` on this Mac returned empty answers for records that exist):

```bash
curl -s "https://dns.google/resolve?name=_dmarc.checkon.ca&type=TXT"
```

## Before launch (v1 "done when")

- The release gates in Technical Design §8 pass on the English golden set.
- The lawyer has signed off every rule marked `interpretation` and the wording library. Record it in `backend/rulepacks/CA-ON/rules.yaml` and `wording.yaml` (`reviewed_by`, `reviewed_on`), then update `test_interpretation_rules_are_not_signed_off_yet`.
- The live API tests pass with your key (`RUN_LIVE_LLM=1`, see `backend/README.md`).

## Known limits of this setup

- **No CAPTCHA.** Turnstile was dropped on 2026-10-20. A script can use up the day's spend cap, which pauses free checks until midnight Toronto time; add a bot check if the logs show that happening.
- **One instance, one worker.** Checks in progress and the rate limit live in the app's memory, so Cloud Run is capped at one instance. To scale, move the check store to Postgres first.
- **The checker refuses everything until the Anthropic key is set.** With `replace-me`, the model calls fail.
- **Organisation policies can block public access.** If your project sits in an organisation that forbids `allUsers`, the public invoker binding fails.
- **Postgres version mismatch.** Cloud SQL runs Postgres 17 by default; local development runs 18. Switch `postgres_version` when Cloud SQL offers 18.
- **Deletion protection is on** for the database and the service. Turn it off in Terraform before `terraform destroy`.
- **Langfuse isn't wired in yet** (Technical Design §12). Add it before you rely on traces for the golden-set runs.
