# Deploying to GCP

Step 7 of `../04-V1-Scope.md`: the lean launch stack from Technical Design §12–13, in Toronto (`northamerica-northeast2`).

| Piece | Where |
| --- | --- |
| Cloud Run service (one instance, one worker), Cloud SQL Postgres `db-g1-small`, Secret Manager, Artifact Registry, Workload Identity Federation for GitHub | `terraform/` |
| Paid plans: Stripe Checkout, customer portal, webhook, extra-check meter | [Stripe](#stripe-paid-plans) |
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

## Stripe (paid plans)

Starter ($79/month, 50 checks) and Agency ($249/month, 300 checks) are Stripe Billing subscriptions bought on Stripe Checkout. Checks past the plan go to a Stripe meter and cost $1 each on the next invoice. Card details stay with Stripe: Checkout and the customer portal are Stripe's pages.

| What | Where |
| --- | --- |
| `STRIPE_SECRET_KEY` | Secret Manager `posting-checker-stripe-secret-key`; local `.env` |
| `STRIPE_WEBHOOK_SECRET` | Secret Manager `posting-checker-stripe-webhook-secret`; local `.env` (from `stripe listen`) |
| `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_AGENCY`, `STRIPE_PRICE_EXTRA_CHECK` | `stripe_price_*` in `terraform.tfvars`; local `.env` |
| `STRIPE_AUTOMATIC_TAX` | `stripe_automatic_tax` in `terraform.tfvars`; local `.env`. Off until you're registered for HST |
| Webhook | `POST /api/v1/stripe/webhook` |

Until the key and all three prices are set, Checkout stays off and the Subscribe buttons open the contact form instead, so deploying this before Stripe is ready is safe.

Never paste a Stripe key into a chat or a file you commit. The commands below read it without showing it; run them in a Terminal tab.

### 1. Create the account

Do this yourself, with your own details or CheckON's, never ShyftLabs'.

1. Sign up at https://dashboard.stripe.com/register with your personal email. Country: Canada.
2. **Settings › Business › Public details:** business name `CheckON`, website `https://checkon.ca`, support email `info@checkon.ca`, terms of service `https://checkon.ca/terms`, privacy policy `https://checkon.ca/privacy`. Checkout refuses to open without the terms URL, because the app asks customers to accept the terms.
3. **Statement descriptor** (same page): `CHECKON.CA`, shortened descriptor `CHECKON`. This is what customers see on their card statement.
4. **Activate payments:** business type (sole proprietor unless you've incorporated; ask your accountant), identity verification and the bank account for payouts. Test mode works before this is done.
5. Optional: **Settings › Branding** with the CheckON icon and the teal `#00897b`, for Checkout, the portal and receipts.

### 2. Work in test mode first

Turn on **Test mode** at the top of the Dashboard (or create a sandbox). Do steps 3 to 6 there, run the [local end-to-end check](#7-local-end-to-end-check), then repeat steps 3 to 6 in live mode for [production](#8-production). Products, meters, the portal and webhooks don't carry over between modes.

### 3. Meter and prices, in CAD

1. **Billing › Meters › Create meter:** meter name `CheckON extra checks`, event name `checkon_extra_check`, aggregation **Sum**. Leave the payload keys at their defaults (`stripe_customer_id`, `value`).
2. **Product catalog › Create product** `CheckON Starter`: **Recurring**, **Monthly**, CAD `79.00`. Under tax, pick the product tax code **Software as a service (SaaS) – business use** (`txcd_10103001`) and **Exclusive** tax behaviour (tax is added on top of the price). Save, then copy the price id (`price_…`).
3. Product `CheckON Agency`: the same, CAD `249.00`. Copy its price id.
4. Product `CheckON extra checks`, description `Checks past your plan's monthly allowance`: **Recurring › More pricing options › Usage-based › Per unit**, CAD `1.00`, meter **CheckON extra checks**, billing period **Monthly**, same tax code and behaviour. Copy its price id.

All three must be CAD and monthly: each subscription holds a plan price and the extra-check price, and Stripe needs them on the same interval.

### 4. Customer portal

**Settings › Billing › Customer portal:**

- **Payment methods:** on. **Invoice history:** on. **Billing information:** name, email, billing address and tax ID on.
- **Cancellations:** on, **at the end of the billing period** (not immediately: an immediate cancellation drops the extra checks not yet billed, and the terms promise the plan runs to the end of the paid period). Cancellation reasons: your choice.
- **Subscriptions › Customers can switch plans:** off. Stripe's portal can't switch a subscription that has a usage-based price, so the app's own **Switch to Agency/Starter** button does it. **Update quantities:** off.
- **Business information:** headline `Manage your CheckON plan`, default redirect link `https://checkon.ca/`. The terms and privacy links come from step 1.
- Save, and in test mode activate the test link.

### 5. Emails and failed payments

- **Settings › Billing › Subscriptions and emails:** turn on **Send emails about successful payments** (receipts) and **Send emails when card payments fail**. A renewal reminder is optional.
- **Manage failed payments:** Smart Retries on, and when all retries fail, **cancel the subscription**. The terms say the plan then ends and the account goes back to the free check. While Stripe retries, the subscription is `past_due` and the app keeps the checks working, with a banner asking for a new card.
- **Settings › Billing › Invoice template:** invoice prefix `CHECKON`, and your business name and mailing address in the footer. Add your GST/HST number there once you have one.

### 6. Tax (HST)

Whether and when to register for GST/HST is a question for your accountant. The small-supplier threshold is $30,000 of taxable sales in one calendar quarter or over the last four quarters together; past it you must register, and below it registering is optional.

- **Until you're registered:** keep `stripe_automatic_tax = false` (`STRIPE_AUTOMATIC_TAX=false` locally). No tax is added, and customers pay the listed prices. The pricing page says "plus tax where it applies".
- **Once registered:** **Settings › Tax**, set the origin address (your Ontario business address) and add the Canada GST/HST registration with your number. Then set `stripe_automatic_tax = true` and apply. Checkout then adds HST for Ontario customers (13%) and the right GST/HST for other provinces, based on the billing address it already collects. Provinces with their own PST need separate registrations; Stripe Tax's dashboard shows when you near a threshold. Stripe Tax charges a fee per transaction; check its current price first.

Checkout also lets business customers add their tax number, which Stripe prints on their invoices.

### 7. Local end-to-end check

In test mode, from the folder you run the app in (the one with `.env`):

1. **Secret key.** Developers › API keys › reveal the test **Secret key** (`sk_test_…`), then:

   ```bash
   sed -i '' '/^STRIPE_SECRET_KEY=/d' .env && read -rs "K?Stripe test secret key: " && printf 'STRIPE_SECRET_KEY=%s\n' "$K" >> .env; unset K
   ```

2. **Price ids** from step 3 (they're not secret): set `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_AGENCY` and `STRIPE_PRICE_EXTRA_CHECK` in `.env`.
3. **Stripe CLI**, to forward webhooks to your machine:

   ```bash
   brew install stripe/stripe-cli/stripe
   ```

   ```bash
   stripe login
   ```

4. **Webhook secret.** The CLI's signing secret stays the same between runs, so store it once:

   ```bash
   sed -i '' '/^STRIPE_WEBHOOK_SECRET=/d' .env && printf 'STRIPE_WEBHOOK_SECRET=%s\n' "$(stripe listen --print-secret)" >> .env
   ```

5. **Forward the events** (leave it running in its own Terminal tab):

   ```bash
   stripe listen --events checkout.session.completed,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted,invoice.paid,invoice.payment_failed --forward-to localhost:8000/api/v1/stripe/webhook
   ```

6. Restart the backend (`cd backend && uv run fastapi dev`) and rebuild the frontend (`cd frontend && bun run build`).
7. Open http://localhost:8000/check#pricing, click **Subscribe** on Starter and pay with Stripe's test card `4242 4242 4242 4242`, any future date, any CVC and any postal code. Use an email you can read, or read the backend log: in development it prints the set-password link (`Set-password link for …`) and each sign-in code (`Sign-in code for …`).
8. Check each piece:
   - The `stripe listen` tab shows the six events with `[200]`.
   - The set-password link opens `/reset-password`; set a password, then log in at `/login` with the emailed code.
   - The account page shows **Starter**, `0 of 50 checks this period`. Run a check (this uses your Anthropic key) and it becomes `1 of 50`, with the check in **Past checks**.
   - **Manage billing** opens Stripe's portal with the card, invoices and Cancel. **Switch to Agency** changes the plan and charges the difference.
   - To see an extra check without running 50, set `PLAN_CHECKS_STARTER=1` in `.env` and restart: the second check shows `Plus 1 extra check`, and the meter shows it under Billing › Meters (Stripe updates it within a few minutes).
   - Cancel in the portal: the account page shows `Ends <date>`, and the plan keeps working until then.

A failed renewal needs time to pass, which Stripe simulates with test clocks (Billing › Test clocks, and Stripe's "Test clocks" guide). The backend tests cover what the app does with it: the subscription turns `past_due`, checks keep working, and the account page shows **Payment failed**.

### 8. Production

1. **Apply this change once** so the two Stripe secrets exist in Secret Manager (they start as `replace-me`, and Checkout stays off):

   ```bash
   cd infra/terraform && GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token --account=msoltani2001@gmail.com)" terraform apply
   ```

2. **Live objects:** switch the Dashboard to live mode and redo steps 3 to 5 (Stripe can copy test products to live mode: open the product › **Copy to live mode**; create the meter again in live mode and point the live extra-check price at it).
3. **Webhook endpoint:** Developers › Webhooks › **Add destination**: events from your account, the newest API version offered, the six events from step 7.5, endpoint URL `https://checkon.ca/api/v1/stripe/webhook`. Then reveal its **signing secret**.
4. **Secrets**, in a Terminal tab:

   ```bash
   read -rs "K?Stripe live secret key: " && printf %s "$K" | gcloud secrets versions add posting-checker-stripe-secret-key --data-file=- --project=compliance-512120 --account=msoltani2001@gmail.com; unset K
   ```

   ```bash
   read -rs "K?Stripe webhook signing secret: " && printf %s "$K" | gcloud secrets versions add posting-checker-stripe-webhook-secret --data-file=- --project=compliance-512120 --account=msoltani2001@gmail.com; unset K
   ```

5. **Prices:** add the three live price ids to `terraform.tfvars` (`stripe_price_starter`, `stripe_price_agency`, `stripe_price_extra_check`) and apply again. The new revision reads the latest secret versions, and Checkout turns on.
6. **Smoke test with a real card:** subscribe to Starter yourself, confirm the webhook deliveries show `200` (Developers › Webhooks › the endpoint), sign in, run one check, open **Manage billing**, cancel, then refund yourself (Payments › the charge › **Refund**).

The app reads the secrets when an instance starts. After you add a new secret version, the next deploy or apply picks it up.

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
