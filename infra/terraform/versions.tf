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

  # Keep state in a bucket once more than one person applies changes (see infra/README.md):
  # backend "gcs" {
  #   bucket = "YOUR-PROJECT-tfstate"
  #   prefix = "posting-checker"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
