output "api_url" {
  description = "Public URL of the API service"
  value       = google_cloud_run_v2_service.api.uri
}

output "ingestion_job" {
  description = "Cloud Run Job name, used by the ingestion workflow"
  value       = google_cloud_run_v2_job.ingestion.name
}

output "runtime_service_account" {
  description = "Service account the workloads run as"
  value       = google_service_account.runtime.email
}

output "image_repository" {
  description = "Artifact Registry path to push images to"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}
