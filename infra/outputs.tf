# exponho os endpoints e nomes dos recursos gerados

output "api_url" {
  description = "url publica da api dataops"
  value       = google_cloud_run_v2_service.api.uri
}

output "dashboard_url" {
  description = "url publica do dashboard streamlit"
  value       = google_cloud_run_v2_service.dashboard.uri
}

output "frontend_url" {
  description = "url publica do cockpit react"
  value       = var.enable_frontend_react ? google_cloud_run_v2_service.frontend[0].uri : null
}

output "artifact_registry_repository" {
  description = "caminho do repositorio no artifact registry"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}"
}

output "quarantine_bucket" {
  description = "nome do bucket de quarentena"
  value       = google_storage_bucket.quarantine.name
}

output "curated_bucket" {
  description = "nome do bucket curated"
  value       = google_storage_bucket.curated.name
}

output "raw_bucket" {
  description = "nome do bucket raw"
  value       = google_storage_bucket.raw.name
}

output "service_account_email" {
  description = "email da service account criada"
  value       = google_service_account.app_sa.email
}
