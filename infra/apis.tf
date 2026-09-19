# Enabling a service is itself an API call, so these must exist before the
# resources that depend on them. Terraform infers that ordering from the
# depends_on references elsewhere in the config.
resource "google_project_service" "required" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
    "sts.googleapis.com",
  ])

  service = each.value

  # Leave APIs enabled on destroy: disabling them can break other workloads
  # in a shared project.
  disable_on_destroy = false
}
