# Private by default: only principals with an explicit IAM grant can pull.
resource "google_artifact_registry_repository" "etl" {
  location      = var.region
  repository_id = "du-etl"
  description   = "Container images for the DU chapters ETL"
  format        = "DOCKER"

  # Keep storage near zero: expire untagged images after a week.
  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s"
    }
  }

  depends_on = [google_project_service.required]
}
