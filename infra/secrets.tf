# centralizo as credenciais no secret manager em vez de usar arquivos locais

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"

  replication {
    auto {}
  }

  depends_on = [
    google_project_service.required_services
  ]
}

# crio uma versao inicial de bootstrap para que o cloud run nao falhe ao buscar "latest"
resource "google_secret_manager_secret_version" "gemini_api_key_bootstrap" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key_initial

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"

  replication {
    auto {}
  }

  depends_on = [
    google_project_service.required_services
  ]
}

resource "google_secret_manager_secret_version" "database_url_bootstrap" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url_initial

  lifecycle {
    ignore_changes = [secret_data]
  }
}
