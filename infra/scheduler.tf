# The daily trigger lives in IaC, as the brief requires, rather than being
# created as a side effect of a gcloud flag.
resource "google_cloud_scheduler_job" "daily" {
  name        = "du-etl-daily"
  description = "Runs the DU chapters ETL once a day"
  schedule    = var.schedule
  time_zone   = "Etc/UTC"
  region      = var.region

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri = format(
      "https://run.googleapis.com/v2/projects/%s/locations/%s/jobs/%s:run",
      var.project_id,
      var.region,
      google_cloud_run_v2_job.etl.name,
    )

    # OAuth (not OIDC) because the target is a Google API.
    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_job_iam_member.scheduler_invokes,
  ]
}
