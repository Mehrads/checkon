# Deploying to Google Cloud

An optional, lean production setup in Toronto (`northamerica-northeast2`): one Cloud Run service, one Cloud SQL Postgres, Secret Manager, Artifact Registry, and GitHub Actions deploying through Workload Identity Federation, so no keys live in GitHub. You can run CheckON anywhere that runs a container and Postgres; this is just the setup it was built and run on.

| Piece | Where |
| --- | --- |
| Cloud Run service (one instance, one worker), Cloud SQL Postgres `db-g1-small`, Secret Manager, Artifact Registry, Workload Identity Federation for GitHub | `terraform/main.tf` |
| Optional HTTPS load balancer for your own domain (Cloud Run domain mapping isn't offered in Toronto) | `terraform/lb.tf` |
| Tests on every push and pull request | `../.github/workflows/test.yml` |
| Deploy on every push to `main`: test, build, migrate, deploy. Skipped until `GCP_PROJECT_ID` is set | `../.github/workflows/deploy.yml` |

**What it cost to run:** about US$50 a month before the load balancer (Cloud SQL about $31, Cloud Run with one warm instance about $18, storage a little), plus about $18 a month for the load balancer once you add a domain, plus model fees for every check. Model fees are capped for anonymous visitors by `FREE_CHECK_DAILY_SPEND_CAP_USD`; signed-in accounts aren't capped unless you set `ACCOUNT_CHECKS_PER_30_DAYS`.

## Before you start

- A Google Cloud project with billing on.
- A GitHub repository with this code (a fork is fine).
- An Anthropic API key. Prefer terms with no training on inputs: postings people paste can name real employers.
- An SMTP sender for sign-in codes and password resets. Gmail's SMTP refuses logins from Cloud Run; a transactional sender such as Resend works.
- `gcloud` and `terraform` (1.9 or later) installed.

## Terraform state

The state holds the generated database password and app secret, so keep it in a private, versioned bucket, not on disk. Terraform can't create the bucket that holds its own state, so create it once:

```bash
gcloud storage buckets create gs://YOUR-PROJECT-ID-tfstate --location=northamerica-northeast2 --uniform-bucket-level-access --public-access-prevention
```

```bash
gcloud storage buckets update gs://YOUR-PROJECT-ID-tfstate --versioning
```

The default compute service account is a project Editor, and GCS gives Editors and Viewers access to new buckets. To keep the state readable by the project Owner only, remove those grants:

```bash
for r in legacyBucketOwner legacyObjectOwner; do gcloud storage buckets remove-iam-policy-binding gs://YOUR-PROJECT-ID-tfstate --member=projectEditor:YOUR-PROJECT-ID --role=roles/storage.$r; done
```

```bash
for r in legacyBucketReader legacyObjectReader; do gcloud storage buckets remove-iam-policy-binding gs://YOUR-PROJECT-ID-tfstate --member=projectViewer:YOUR-PROJECT-ID --role=roles/storage.$r; done
```

## First deploy

1. Sign in and pick the project:

   ```bash
   gcloud auth login && gcloud auth application-default login
   ```

   ```bash
   gcloud config set project YOUR-PROJECT-ID
   ```

2. Fill in the settings:

   ```bash
   cd infra/terraform && cp terraform.tfvars.example terraform.tfvars
   ```

3. Create the stack. The first apply runs Google's hello image, so the service exists before any deploy:

   ```bash
   terraform init -backend-config="bucket=YOUR-PROJECT-ID-tfstate" && terraform apply
   ```

4. Add the secrets Terraform doesn't hold. They start as `replace-me`. Type them in a terminal so they stay out of your shell history:

   ```bash
   read -rs "K?Anthropic API key: " && printf %s "$K" | gcloud secrets versions add posting-checker-anthropic-api-key --data-file=-; unset K
   ```

   ```bash
   read -rs "K?SMTP password: " && printf %s "$K" | gcloud secrets versions add posting-checker-smtp-password --data-file=-; unset K
   ```

   Signing in emails a 6-digit code after the password, so without working email nobody can sign in, admins included. The first admin is `first_superuser_email`; its generated password is in the `posting-checker-first-superuser-password` secret.

5. Optional, your own domain: set `domain` and `public_url` in `terraform.tfvars` and apply. That adds the load balancer, a Google-managed certificate for the domain and `www`, and closes the service's own run.app URL so visitors can only arrive through the load balancer (and can't fake `X-Forwarded-For`). Point an `A` record for the domain at the load balancer's address and a `CNAME` for `www` at the domain. The certificate is issued once both resolve, usually within an hour.

   ```bash
   terraform apply && terraform output -raw lb_ip
   ```

6. In GitHub, under Settings > Secrets and variables > Actions > Variables, add:

   | Variable | Value |
   | --- | --- |
   | `GCP_PROJECT_ID` | your project id |
   | `GCP_REGION` | `northamerica-northeast2` |
   | `GCP_WORKLOAD_IDENTITY_PROVIDER` | `terraform output -raw workload_identity_provider` |
   | `GCP_DEPLOYER_SERVICE_ACCOUNT` | `terraform output -raw deployer_service_account` |
   | `SITE_URL` | your public address, e.g. `https://checker.example.com` (the `public_url` you set) |
   | `CONTACT_EMAIL` | optional: shown on the contact form |
   | `UMAMI_WEBSITE_ID` | optional: an Umami website id, for cookieless visit counts |

   Then create an environment named `production`. Add yourself as a required reviewer if you want to approve each deploy.

7. Push to `main`. The Deploy workflow tests, builds the image, runs the migrations as a Cloud Run job, then deploys.

8. Smoke-test: run one check, then a second to see the weekly free-check limit. In the Cloud Run logs, confirm requests show real visitor IPs. If they all show one Google address, adjust `TRUSTED_PROXY_HOPS`.

## Accounts

Signed-in users get every feature: company profiles and client workspaces, pay range suggestions, careers page audits, the posting archive and check history. You pay the model fees for their checks, so two settings in `terraform.tfvars` keep that in hand:

- `signup_open` (default `false`): whether anyone can make an account. While it's off, add users yourself under Admin > Users.
- `account_checks_per_30_days` (default `0`, no limit): each account's checks in any 30 days.

## Browser extension

The API only accepts browser extensions listed in `extension_ids`. The unpacked build has a fixed ID (`extension/unpacked-extension-id.txt`); add your store listing's ID once you publish one, then apply. Building and loading are in `../extension/README.md`.

## Tracing (optional)

Each model call can be traced to [Langfuse](https://langfuse.com): route, status, rule verdicts, and per call the model, tokens, cost and latency. **Never posting text or the model's answers** (`backend/app/core/tracing.py`; a test fails if a posting's words reach an exported span). Tracing stays off while either key is `replace-me`. To turn it on, create a Langfuse project and API keys, then:

```bash
read -rs "K?Langfuse public key: " && printf %s "$K" | gcloud secrets versions add posting-checker-langfuse-public-key --data-file=-; unset K
```

```bash
read -rs "K?Langfuse secret key: " && printf %s "$K" | gcloud secrets versions add posting-checker-langfuse-secret-key --data-file=-; unset K
```

Cloud Run reads secrets when an instance starts, so redeploy (or push to `main`) afterwards. `langfuse_base_url` picks the region.

## Known limits of this setup

- **No CAPTCHA.** A script can use up the day's free-check spend cap, which pauses free checks until midnight Toronto time. Add a bot check if your logs show that happening.
- **One instance, one worker.** Checks in progress and the rate limits live in the app's memory, so Cloud Run is capped at one instance. To scale out, move the check store to Postgres first.
- **Nothing works until the Anthropic key is set.** With `replace-me`, every model call fails.
- **Organisation policies can block public access.** If your project sits in an organisation that forbids `allUsers`, the public invoker binding fails.
- **The run.app URL is closed once `domain` is set.** If the load balancer breaks, the site is down. To reach the service directly while you fix it, set `ingress` back to `INGRESS_TRAFFIC_ALL` in `main.tf` and apply.
- **Deletion protection is on** for the database and the service.

## Shutting it down

Turn deletion protection off in `main.tf` (the Cloud SQL instance and the Cloud Run service), apply, then `terraform destroy`. The state bucket isn't in Terraform, so delete it yourself. Or delete the whole project, which stops everything at once and can be undone for 30 days:

```bash
gcloud projects delete YOUR-PROJECT-ID
```

Remember the costs outside Google Cloud: your domain, mailbox and SMTP sender, and the Anthropic key.
