locals {
  # When create_database is false, supply an existing instance's details
  # through the secret instead. See README.
  sql_connection_name = var.create_database ? google_sql_database_instance.main[0].connection_name : ""
}

resource "google_sql_database_instance" "main" {
  count = var.create_database ? 1 : 0

  name             = "du-etl-pg"
  database_version = "POSTGRES_16"
  region           = var.region

  # Demo settings: allows `terraform destroy` to actually work. For a real
  # production database this must be true.
  deletion_protection = false

  settings {
    tier      = var.db_tier
    edition   = "ENTERPRISE"
    disk_size = 10
    disk_type = "PD_HDD"

    backup_configuration {
      enabled = false # cost control for this exercise
    }

    ip_configuration {
      # No public IP. The Cloud Run job reaches the instance over a unix
      # socket provided by the built-in Cloud SQL connector, so there is
      # nothing exposed to the internet and no VPC connector to pay for.
      ipv4_enabled    = false
      private_network = null
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_sql_database" "du" {
  count    = var.create_database ? 1 : 0
  name     = "du"
  instance = google_sql_database_instance.main[0].name
}

resource "random_password" "db" {
  count  = var.create_database ? 1 : 0
  length = 32
  # No special characters: the password is embedded in a URL, and escaping
  # is a needless source of bugs.
  special = false
}

resource "google_sql_user" "app" {
  count    = var.create_database ? 1 : 0
  name     = "du_app"
  instance = google_sql_database_instance.main[0].name
  password = random_password.db[0].result
}
