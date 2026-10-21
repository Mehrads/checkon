variable "project_id" {
  description = "GCP project that hosts the checker."
  type        = string
}

variable "region" {
  description = "Toronto, so customer data stays in Canada (Technical Design §12)."
  type        = string
  default     = "northamerica-northeast2"
}

variable "github_repository" {
  description = "owner/name of the GitHub repository allowed to deploy, for example mehrad/posting-checker."
  type        = string
}

variable "public_url" {
  description = "The site's public URL (FRONTEND_HOST). Leave empty on the first apply, then set it to the service URL or your domain."
  type        = string
  default     = ""
}

variable "extension_ids" {
  description = "Browser extension IDs allowed to call the free check: the unpacked build's fixed ID, then the Chrome Web Store and Edge IDs (extension/README.md)."
  type        = list(string)
  default     = []
}

variable "domain" {
  description = "Public domain, for example checkon.ca. Setting it adds the load balancer in lb.tf (infra/README.md, step 5)."
  type        = string
  default     = ""
}

variable "first_superuser_email" {
  description = "Admin account the template creates on the first migration (accounts arrive in phase 3)."
  type        = string
}

variable "image" {
  description = "Image for the first apply only; GitHub Actions deploys every later image."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "postgres_version" {
  description = "Cloud SQL Postgres version. Local development runs Postgres 18; use it here once Cloud SQL offers it."
  type        = string
  default     = "POSTGRES_17"
}

variable "contact_email" {
  description = "Where contact-form messages are emailed. Leave empty to only save them."
  type        = string
  default     = ""
}

variable "smtp_host" {
  description = "SMTP server for the contact notices, for example smtp.gmail.com or your email provider's."
  type        = string
  default     = ""
}

variable "smtp_port" {
  type    = number
  default = 587
}

variable "smtp_user" {
  type    = string
  default = ""
}

variable "emails_from" {
  description = "Sender address for the contact notices."
  type        = string
  default     = ""
}

variable "free_checks_per_week" {
  type    = number
  default = 1
}

variable "free_check_daily_spend_cap_usd" {
  type    = string
  default = "5"
}

# Stripe (infra/README.md, "Stripe"): price ids from the Stripe Dashboard, live mode in production.
# The secret key and webhook signing secret live in Secret Manager, not here.

variable "stripe_price_starter" {
  description = "Price id of the Starter monthly fee, for example price_1Q…"
  type        = string
  default     = ""
}

variable "stripe_price_agency" {
  description = "Price id of the Agency monthly fee."
  type        = string
  default     = ""
}

variable "stripe_price_extra_check" {
  description = "Price id of the $1 usage-based extra-check price on the checkon_extra_check meter."
  type        = string
  default     = ""
}

variable "stripe_automatic_tax" {
  description = "Have Stripe Tax add HST at Checkout. Turn on only once registered for GST/HST and the registration is added in Stripe."
  type        = bool
  default     = false
}
