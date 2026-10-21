output "service_url" {
  description = "Set public_url to this (or your domain) and apply again."
  value       = google_cloud_run_v2_service.app.uri
}

output "lb_ip" {
  description = "Point the domain's A record, and www, at this address."
  value       = one(google_compute_global_address.web[*].address)
}

output "artifact_repository" {
  description = "Docker repository the deploy workflow pushes to."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "workload_identity_provider" {
  description = "GitHub variable GCP_WORKLOAD_IDENTITY_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_service_account" {
  description = "GitHub variable GCP_DEPLOYER_SERVICE_ACCOUNT."
  value       = google_service_account.deployer.email
}

output "manual_secrets" {
  description = "Secrets to fill by hand before going live (infra/README.md, step 3)."
  value       = [for secret in google_secret_manager_secret.manual : secret.secret_id]
}
