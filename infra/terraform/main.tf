# The lean launch stack (Technical Design §12–13): Cloud Run, Cloud SQL, Secret Manager and
# Artifact Registry, with GitHub Actions deploying through Workload Identity Federation (no keys).
# No Redis, load balancer or Cloud Armor yet; the free-check limits live in Postgres and the app.

locals {
  name = "posting-checker"

  # Plain settings shared by the service and the migration job
  plain_env = {
    PROJECT_NAME                   = "CheckON"
    FRONTEND_HOST                  = var.public_url != "" ? var.public_url : "https://${local.name}.invalid"
    FIRST_SUPERUSER                = var.first_superuser_email
    TRUSTED_PROXY_HOPS             = "1"
    FREE_CHECKS_PER_WEEK           = tostring(var.free_checks_per_week)
    FREE_CHECK_DAILY_SPEND_CAP_USD = var.free_check_daily_spend_cap_usd
    CONTACT_EMAIL                  = var.contact_email
    SMTP_HOST                      = var.smtp_host
    SMTP_PORT                      = tostring(var.smtp_port)
    SMTP_USER                      = var.smtp_user
    EMAILS_FROM_EMAIL              = var.emails_from
  }

  # Settings read from Secret Manager
  secret_env = {
    DATABASE_URL             = google_secret_manager_secret.generated["database-url"].secret_id
    SECRET_KEY               = google_secret_manager_secret.generated["secret-key"].secret_id
    FIRST_SUPERUSER_PASSWORD = google_secret_manager_secret.generated["first-superuser-password"].secret_id
    ANTHROPIC_API_KEY        = google_secret_manager_secret.manual["anthropic-api-key"].secret_id
    SMTP_PASSWORD            = google_secret_manager_secret.manual["smtp-password"].secret_id
  }
}

# APIs

resource "google_project_service" "apis" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
    "sts.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# Images

resource "google_artifact_registry_repository" "images" {
  repository_id = local.name
  location      = var.region
  format        = "DOCKER"
  description   = "Images of the posting checker, pushed by GitHub Actions"
  depends_on    = [google_project_service.apis]
}

# Database: Cloud SQL Postgres, db-g1-small, reached from Cloud Run through the built-in connector

resource "google_sql_database_instance" "db" {
  name                = "${local.name}-db"
  region              = var.region
  database_version    = var.postgres_version
  deletion_protection = true

  settings {
    tier                        = "db-g1-small"
    edition                     = "ENTERPRISE"
    availability_type           = "ZONAL"
    disk_type                   = "PD_SSD"
    disk_size                   = 10
    disk_autoresize             = true
    deletion_protection_enabled = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }

    ip_configuration {
      # Public IP with no authorised networks: only the Cloud SQL connector can reach it.
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "app" {
  name     = "app"
  instance = google_sql_database_instance.db.name
}

resource "random_password" "db" {
  length  = 32
  special = false # it goes into a URL
}

resource "google_sql_user" "app" {
  name     = "app"
  instance = google_sql_database_instance.db.name
  password = random_password.db.result
}

# Secrets. Generated ones are written here; the API keys are added by hand so they never sit in state.

resource "random_password" "secret_key" {
  length  = 48
  special = false
}

resource "random_password" "first_superuser" {
  length  = 24
  special = false
}

locals {
  generated_secrets = {
    "database-url"             = "postgresql+psycopg://app:${random_password.db.result}@localhost/app?host=/cloudsql/${google_sql_database_instance.db.connection_name}"
    "secret-key"               = random_password.secret_key.result
    "first-superuser-password" = random_password.first_superuser.result
  }
}

resource "google_secret_manager_secret" "generated" {
  for_each  = toset(keys(local.generated_secrets))
  secret_id = "${local.name}-${each.value}"
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "generated" {
  for_each    = google_secret_manager_secret.generated
  secret      = each.value.id
  secret_data = local.generated_secrets[each.key]
}

resource "google_secret_manager_secret" "manual" {
  for_each  = toset(["anthropic-api-key", "smtp-password"])
  secret_id = "${local.name}-${each.value}"
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
  depends_on = [google_project_service.apis]
}

# A placeholder version so the first deploy can start; the real value is added as a new version
# (infra/README.md, step 3) and Terraform leaves it alone.
resource "google_secret_manager_secret_version" "manual_placeholder" {
  for_each    = google_secret_manager_secret.manual
  secret      = each.value.id
  secret_data = "replace-me"
  lifecycle {
    ignore_changes = [secret_data]
  }
}

# Identities

resource "google_service_account" "runtime" {
  account_id   = "${local.name}-run"
  display_name = "Posting checker: Cloud Run service and migration job"
}

resource "google_project_iam_member" "runtime_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_reads" {
  for_each  = merge(google_secret_manager_secret.generated, google_secret_manager_secret.manual)
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_service_account" "deployer" {
  account_id   = "${local.name}-deploy"
  display_name = "Posting checker: GitHub Actions deploys"
}

resource "google_project_iam_member" "deployer_run" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_artifact_registry_repository_iam_member" "deployer_push" {
  repository = google_artifact_registry_repository.images.name
  location   = var.region
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_service_account_iam_member" "deployer_acts_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

# GitHub Actions sign-in without a key: only the main branch of this one repository.

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  depends_on                = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  attribute_condition = "assertion.repository == '${var.github_repository}' && assertion.ref == 'refs/heads/main'"
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_deploys" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

# The app: one instance, one worker, because checks in progress live in memory (infra/README.md).

resource "google_cloud_run_v2_service" "app" {
  name     = local.name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.db.connection_name]
      }
    }

    containers {
      # No command override: the image's CMD (backend/Dockerfile) already runs one worker on
      # port 8000, and an override would break the placeholder image on the first apply.
      image = var.image

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      dynamic "env" {
        for_each = local.plain_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image, client, client_version]
  }

  depends_on = [
    google_secret_manager_secret_version.generated,
    google_secret_manager_secret_version.manual_placeholder,
    google_secret_manager_secret_iam_member.runtime_reads,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.app.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Migrations: the same image runs the template's prestart script (alembic upgrade, first superuser).

resource "google_cloud_run_v2_job" "migrate" {
  name     = "${local.name}-migrate"
  location = var.region

  template {
    template {
      service_account = google_service_account.runtime.email
      max_retries     = 0
      timeout         = "600s"

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.db.connection_name]
        }
      }

      containers {
        image   = var.image
        command = ["bash"]
        args    = ["scripts/prestart.sh"]

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }

        dynamic "env" {
          for_each = local.plain_env
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = local.secret_env
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image, client, client_version]
  }

  depends_on = [
    google_secret_manager_secret_version.generated,
    google_secret_manager_secret_version.manual_placeholder,
    google_secret_manager_secret_iam_member.runtime_reads,
  ]
}
