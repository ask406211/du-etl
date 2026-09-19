# A Job, not a Service: this container runs to completion and exits.
# A Cloud Run Service would have to listen on a port and stay up, which is
# the wrong shape for batch work and bills for idle time.
resource "google_cloud_run_v2_job" "etl" {
  name     = "du-etl"
  location = var.region

  # The provider defaults this to true as a guard for production services.
  # This job holds no state and is rebuilt from source on every deploy, so
  # blocking replacement would only get in the way of `terraform destroy`.
  deletion_protection = false

  template {
    # Do not retry the whole task: the run is idempotent, but a genuine
    # failure should surface rather than be masked by a retry.
    task_count = 1

    template {
      service_account = google_service_account.job.email
      timeout         = "600s"
      max_retries     = 1

      containers {
        image = var.image

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "DU_FEATURE_SERVICE_URL"
          value = "https://services2.arcgis.com/5I7u4SJE1vUr79JC/arcgis/rest/services/UniversityChapters_Public/FeatureServer/0/query"
        }

        env {
          name  = "TARGET_STATES"
          value = var.target_states
        }

        env {
          name  = "LOG_LEVEL"
          value = "INFO"
        }

        # Injected at start-up from Secret Manager, never baked into the image.
        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = "latest"
            }
          }
        }

        dynamic "volume_mounts" {
          for_each = var.create_database ? [1] : []
          content {
            name       = "cloudsql"
            mount_path = "/cloudsql"
          }
        }
      }

      dynamic "volumes" {
        for_each = var.create_database ? [1] : []
        content {
          name = "cloudsql"
          cloud_sql_instance {
            instances = [local.sql_connection_name]
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.required,
    google_secret_manager_secret_iam_member.job_reads_db_url,
    # The container references version "latest", which does not resolve
    # until a version exists. Terraform cannot infer this from the
    # secret_id reference alone, so without this the job and the secret
    # version are created in parallel and the job fails on a fresh deploy.
    google_secret_manager_secret_version.database_url,
  ]
}
