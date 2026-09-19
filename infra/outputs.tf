output "image_repository" {
  description = "Docker repository to push the ETL image to."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.etl.repository_id}"
}

output "job_name" {
  value = google_cloud_run_v2_job.etl.name
}

output "run_job_manually" {
  description = "Trigger a run without waiting for the schedule."
  value       = "gcloud run jobs execute ${google_cloud_run_v2_job.etl.name} --region ${var.region}"
}

output "sql_connection_name" {
  value = local.sql_connection_name
}

output "workload_identity_provider" {
  description = "Value for the GitHub Actions auth step."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "cicd_service_account" {
  value = google_service_account.cicd.email
}
