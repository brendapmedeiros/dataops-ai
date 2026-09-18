# crio a service account dedicada para o dataops ai seguindo menor privilegio
resource "google_service_account" "app_sa" {
  account_id   = "dataops-ai-runner"
  display_name = "Service Account para execucao do DataOps AI"

  depends_on = [
    google_project_service.required_services
  ]
}

# permito leitura de segredos apenas para a service account da aplicacao
resource "google_secret_manager_secret_iam_member" "gemini_secret_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "db_secret_access" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa.email}"
}

# concedo permissao de escrita e leitura nos buckets do data lake
resource "google_storage_bucket_iam_member" "raw_access" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_storage_bucket_iam_member" "quarantine_access" {
  bucket = google_storage_bucket.quarantine.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_storage_bucket_iam_member" "curated_access" {
  bucket = google_storage_bucket.curated.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.app_sa.email}"
}

# concedo permissao para puxar imagens do artifact registry
resource "google_artifact_registry_repository_iam_member" "cr_pull" {
  location   = var.region
  repository = google_artifact_registry_repository.repo.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.app_sa.email}"
}
