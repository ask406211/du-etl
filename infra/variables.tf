variable "project_id" {
  type        = string
  description = "GCP project ID (not the display name)."
}

variable "region" {
  type        = string
  description = "Region for all regional resources."
  default     = "us-central1"
}

variable "image" {
  type        = string
  description = <<-EOT
    Full image reference for the ETL container, e.g.
    us-central1-docker.pkg.dev/PROJECT/du-etl/du-etl:abc123.
    The image must be pushed before the first apply: Cloud Run validates
    that it exists at deploy time.
  EOT
}

variable "target_states" {
  type        = string
  description = "Comma-separated states to extract."
  default     = "CA"
}

variable "schedule" {
  type        = string
  description = "Cron schedule for the daily run."
  default     = "0 6 * * *"
}

variable "create_database" {
  type        = bool
  description = <<-EOT
    Create a Cloud SQL instance. Set false to point the job at an existing
    database instead. Cloud SQL has no free tier and is the only resource
    here that costs money at rest, so it is deliberately optional.
  EOT
  default     = true
}

variable "db_tier" {
  type        = string
  description = "Cloud SQL machine type. db-f1-micro is the cheapest."
  default     = "db-f1-micro"
}

variable "github_repository" {
  type        = string
  description = "owner/repo, used to scope the CI identity federation."
}
