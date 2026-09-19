# One identity per job, granted only what that job needs.
resource "google_service_account" "job" {
  account_id   = "du-etl-job"
  display_name = "DU chapters ETL job runtime"
}

resource "google_project_iam_member" "job_sql_client" {
  count   = var.create_database ? 1 : 0
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.job.email}"
}

# Scoped to this one secret, not the project.
resource "google_secret_manager_secret_iam_member" "job_reads_db_url" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.job.email}"
}

# A separate identity for the scheduler: it may start the job and nothing else.
resource "google_service_account" "scheduler" {
  account_id   = "du-etl-scheduler"
  display_name = "DU chapters ETL scheduler"
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_invokes" {
  location = google_cloud_run_v2_job.etl.location
  name     = google_cloud_run_v2_job.etl.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}
