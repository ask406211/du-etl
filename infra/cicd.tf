# Workload Identity Federation: GitHub Actions proves who it is with a
# short-lived OIDC token and exchanges it for a Google credential. No
# long-lived service account JSON key is ever created or stored.
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions"

  depends_on = [google_project_service.required]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  # Without this condition, any GitHub repository in the world could
  # exchange a token here. This pins it to one repo.
  attribute_condition = "assertion.repository == \"${var.github_repository}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "cicd" {
  account_id   = "du-etl-cicd"
  display_name = "GitHub Actions deployer"
}

# Only workflows in the named repository may impersonate the deployer.
resource "google_service_account_iam_member" "cicd_impersonation" {
  service_account_id = google_service_account.cicd.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

# Broad by necessity: this identity runs `terraform apply`, so it manages
# every resource in this configuration. Scoped to this project only.
resource "google_project_iam_member" "cicd_roles" {
  for_each = toset([
    "roles/artifactregistry.writer",
    "roles/cloudscheduler.admin",
    "roles/cloudsql.admin",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/resourcemanager.projectIamAdmin",
    "roles/run.admin",
    "roles/secretmanager.admin",
    "roles/serviceusage.serviceUsageAdmin",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cicd.email}"
}
