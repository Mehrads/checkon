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
  description = "Public domain, for example checker.example.com. Setting it adds the load balancer in lb.tf (infra/README.md, step 5)."
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
  description = "SMTP server for sign-in codes, password resets and contact notices: smtp.resend.com (not smtp.gmail.com, which refuses logins from Cloud Run)."
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
  description = "Sender address for the app's emails, on a domain verified with the SMTP provider."
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

variable "signup_open" {
  description = "Let anyone make an account. Off: only an admin adds users (Admin > Users). Each account's checks are paid for by you."
  type        = bool
  default     = false
}

variable "account_checks_per_30_days" {
  description = "Each signed-in account's checks in any 30 days; 0 means no limit."
  type        = number
  default     = 0
}

variable "langfuse_base_url" {
  description = "The Langfuse Cloud region the traces go to; its keys are the langfuse-* secrets."
  type        = string
  default     = "https://us.cloud.langfuse.com"
}

# Our own addresses: they skip the weekly free-check quota so the live check can be tested.
variable "free_check_allowlist_ips" {
  type    = list(string)
  default = []
}
