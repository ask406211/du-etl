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
      # Cloud SQL requires at least one connectivity mode, and the Cloud SQL
      # Auth Proxy (which Cloud Run's built-in connector uses) dials the
      # public endpoint. Security comes from authorized_networks being empty:
      # every connection must be IAM-authenticated through the proxy, so a
      # password alone reaches nothing.
      #
      # Private IP would remove the public endpoint entirely, but requires a
      # VPC plus service-networking peering. Noted in the README as
      # follow-up work.
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
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
