# The connection string is the only secret the job needs. Keeping it whole
# (rather than five separate values) means one thing to rotate.
resource "google_secret_manager_secret" "database_url" {
  secret_id = "du-etl-database-url"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_version" "database_url" {
  count  = var.create_database ? 1 : 0
  secret = google_secret_manager_secret.database_url.id

  # host=/cloudsql/... makes psycopg use the unix socket that Cloud Run
  # mounts, rather than TCP.
  secret_data = format(
    "postgresql://%s:%s@/du?host=/cloudsql/%s",
    google_sql_user.app[0].name,
    random_password.db[0].result,
    local.sql_connection_name,
  )
}
