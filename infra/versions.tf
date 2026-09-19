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

  # State is local by default so a reviewer can run this with no prior setup.
  # For team use, create a versioned bucket and uncomment:
  #
  # backend "gcs" {
  #   bucket = "YOUR-BUCKET"
  #   prefix = "du-etl"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
