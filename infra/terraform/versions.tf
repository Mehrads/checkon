terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # State holds the generated passwords, so it lives in a private, versioned bucket (infra/README.md). Create
  # yours first, then run `terraform init -backend-config="bucket=YOUR-PROJECT-ID-tfstate"`.
  backend "gcs" {
    prefix = "posting-checker"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
