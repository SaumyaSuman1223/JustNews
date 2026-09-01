# Google Cloud, always-free tier.
#
# Region is us-east1 and that is not a preference: Cloud Run's always-free
# allowance only applies in a handful of US regions, and us-east1 is the one
# closest to Europe. Supabase must be created in the same region so database
# round trips stay near 1 ms; readers elsewhere are served from Vercel's edge
# cache instead (ADR 0003, ADR 0005).

terraform {
  required_version = ">= 1.9"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  backend "gcs" {
    # bucket and prefix supplied by -backend-config, so this file carries no
    # environment-specific values.
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  services = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "iamcredentials.googleapis.com",
  ]
}

resource "google_project_service" "enabled" {
  for_each                   = toset(local.services)
  service                    = each.value
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "justnews"
  format        = "DOCKER"
  description   = "Container images for the API and ingestion job"

  docker_config {
    immutable_tags = true # a deployed tag can never be repointed underneath us
  }

  depends_on = [google_project_service.enabled]
}

resource "google_service_account" "runtime" {
  account_id   = "justnews-${var.environment}"
  display_name = "JustNews ${var.environment} runtime"
}

# --- secrets ------------------------------------------------------------
# Values are set out of band (gcloud or the console). Terraform manages the
# secret's existence and who may read it, never its contents.

resource "google_secret_manager_secret" "app" {
  for_each  = toset(["database-url", "gnews-api-key", "supabase-service-role-key"])
  secret_id = "justnews-${var.environment}-${each.value}"
  replication {
    auto {}
  }
  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_iam_member" "runtime_reader" {
  for_each  = google_secret_manager_secret.app
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

# --- api ----------------------------------------------------------------

resource "google_cloud_run_v2_service" "api" {
  name     = "justnews-api-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.runtime.email

    scaling {
      # Scale to zero. An idle service must cost nothing, or the free tier is
      # spent on nobody. The cold start this buys is acceptable because
      # cacheable pages never reach this service at all.
      min_instance_count = 0
      max_instance_count = var.max_instances
    }

    containers {
      image = var.api_image

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        # CPU only while a request is in flight - this is what keeps the
        # 180,000 free vCPU-seconds from draining while nobody is reading.
        cpu_idle = true
      }

      env {
        name  = "APP_ENV"
        value = var.environment
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app["database-url"].secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get { path = "/health" }
        initial_delay_seconds = 3
        period_seconds        = 5
        failure_threshold     = 10
      }

      liveness_probe {
        # Liveness hits /health, never /health/ready: a database outage must
        # not make Cloud Run kill healthy containers and turn a degradation
        # into an outage.
        http_get { path = "/health" }
        period_seconds    = 30
        failure_threshold = 3
      }
    }

    max_instance_request_concurrency = 80
    timeout                          = "30s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# --- ingestion job ------------------------------------------------------

resource "google_cloud_run_v2_job" "ingestion" {
  name     = "justnews-ingestion-${var.environment}"
  location = var.region

  template {
    template {
      service_account = google_service_account.runtime.email
      # One attempt. A failed pass is not worth retrying: the next scheduled
      # run is fifteen minutes away and will pick up whatever was missed.
      max_retries = 0
      timeout     = "600s"

      containers {
        image = var.ingestion_image
        args  = ["run"]

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app["database-url"].secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "GNEWS_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app["gnews-api-key"].secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }
}
