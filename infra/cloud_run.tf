# configuro os servicos do cloud run em modo serverless com escala a zero

resource "google_cloud_run_v2_service" "api" {
  name     = "dataops-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  depends_on = [
    google_project_service.required_services,
    google_secret_manager_secret_version.gemini_api_key_bootstrap,
    google_secret_manager_secret_version.database_url_bootstrap,
  ]

  template {
    service_account = google_service_account.app_sa.email

    scaling {
      # zero instancias ociosas para garantir custo zero quando nao houver uso
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/dataops-ai/api:latest"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "GCS_RAW_BUCKET"
        value = google_storage_bucket.raw.name
      }

      env {
        name  = "GCS_QUARANTINE_BUCKET"
        value = google_storage_bucket.quarantine.name
      }

      env {
        name  = "GCS_CURATED_BUCKET"
        value = google_storage_bucket.curated.name
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_service" "dashboard" {
  name     = "dataops-dashboard"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  depends_on = [
    google_project_service.required_services,
  ]

  template {
    service_account = google_service_account.app_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/dataops-ai/dashboard:latest"

      ports {
        container_port = 8501
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
      }

      # sobreponho o entrypoint padrao do container para rodar streamlit em vez de uvicorn
      command = ["streamlit"]
      args    = ["run", "dashboard/app.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.headless", "true"]

      env {
        name  = "DATAOPS_API_URL"
        value = google_cloud_run_v2_service.api.uri
      }
    }
  }
}

resource "google_cloud_run_v2_service" "frontend" {
  count    = var.enable_frontend_react ? 1 : 0
  name     = "dataops-frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  depends_on = [
    google_project_service.required_services,
  ]

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/dataops-ai/frontend:latest"

      ports {
        container_port = 80
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "256Mi"
        }
      }
    }
  }
}

# libero acesso publico para demonstracao no portfolio
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "dashboard_public" {
  name     = google_cloud_run_v2_service.dashboard.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  count    = var.enable_frontend_react ? 1 : 0
  name     = google_cloud_run_v2_service.frontend[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
