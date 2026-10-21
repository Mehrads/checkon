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

   The state holds the generated database password and app secret, so it lives in a private GCS bucket, not on disk. Create the bucket before step 3 ([Terraform state](#terraform-state)).

3. Create the stack. The first apply runs Google's hello image, so the service exists before any deploy:

   ```bash
   terraform init && terraform apply
   ```

4. Add the Anthropic key, which Terraform doesn't hold. It starts as `replace-me`:

   ```bash
   printf %s "YOUR-ANTHROPIC-KEY" | gcloud secrets versions add posting-checker-anthropic-api-key --data-file=-
   ```

   Also add the app password for info@checkon.ca ([Email and DNS](#email-and-dns), step 3). `terraform.tfvars.example` already has the Gmail SMTP settings. Admin sign-in emails a 6-digit code after the password, so without working SMTP nobody can sign in to `/stats`. Contact-form messages are still saved in the `contact_message` table either way.

   ```bash
   printf %s "YOUR-APP-PASSWORD" | gcloud secrets versions add posting-checker-smtp-password --data-file=-
   ```

5. Point checkon.ca at the service. Cloud Run's own domain mapping isn't offered in Toronto, so `lb.tf` puts a global HTTPS load balancer in front (about $18 a month, the load balancer line in Technical Design §13). Set `domain = "checkon.ca"` and `public_url = "https://checkon.ca"` in `terraform.tfvars` and apply. It also tells the app to read the visitor's IP one hop further back (`TRUSTED_PROXY_HOPS`), and closes the service's own run.app URL (ingress `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`, so it returns 404): visitors can only arrive through the load balancer and can't fake `X-Forwarded-For`.

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

## Terraform state

State lives in `gs://compliance-512120-tfstate` under `posting-checker/` (`backend "gcs"` in `versions.tf`). The bucket is in Toronto, versioned (each apply keeps the previous state as an older version), with uniform access and public access prevention. Only the project Owner can read it: the Editor and Viewer access GCS adds by default is removed, since the default compute service account is a project Editor. Terraform takes a lock in the same bucket while it runs. Migrated from the local `terraform.tfstate` on 2026-10-21.

The bucket sits outside Terraform, which can't create the bucket that holds its own state. On a new project, create it once before `terraform init`, then put its name in `versions.tf`:

```bash
gcloud storage buckets create gs://YOUR-PROJECT-ID-tfstate --location=northamerica-northeast2 --uniform-bucket-level-access --public-access-prevention
```

```bash
gcloud storage buckets update gs://YOUR-PROJECT-ID-tfstate --versioning
```

```bash
for r in legacyBucketOwner legacyObjectOwner; do gcloud storage buckets remove-iam-policy-binding gs://YOUR-PROJECT-ID-tfstate --member=projectEditor:YOUR-PROJECT-ID --role=roles/storage.$r; done
```

```bash
for r in legacyBucketReader legacyObjectReader; do gcloud storage buckets remove-iam-policy-binding gs://YOUR-PROJECT-ID-tfstate --member=projectViewer:YOUR-PROJECT-ID --role=roles/storage.$r; done
```

To run Terraform as one Google account without changing the gcloud or application-default sign-in, hand it a token for that account:

```bash
GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token --account=YOUR-PERSONAL-ACCOUNT)" terraform plan
```

To restore an earlier state, list the versions with `gcloud storage ls -a gs://compliance-512120-tfstate/posting-checker/`, then copy the one you want over `default.tfstate`.

## Browser extension

The free check also runs in a Chrome and Edge side panel (`extension/`). The API only accepts extensions listed in `extension_ids` in `terraform.tfvars`: the unpacked build's fixed ID (`lfepfedddcabkigmmhbhacdllgljpdbe`), then the Chrome Web Store and Edge IDs once the listings exist. Add an ID and run `terraform apply`; it updates the service's `EXTENSION_IDS` setting in place. Building, loading and publishing are in `extension/README.md`.

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
- **The run.app URL is closed once `domain` is set.** Everything goes through the load balancer, so if it breaks, the site is down. To reach the service directly while you fix it, set `ingress` back to `INGRESS_TRAFFIC_ALL` in `main.tf` and apply.
- **Deletion protection is on** for the database and the service. Turn it off in Terraform before `terraform destroy`. The state bucket isn't in Terraform, so `destroy` leaves it.
- **Langfuse isn't wired in yet** (Technical Design §12). Add it before you rely on traces for the golden-set runs.
