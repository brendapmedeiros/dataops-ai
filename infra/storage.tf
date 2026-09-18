# separo o data lake em tres camadas: raw, quarentena e curated

resource "google_storage_bucket" "raw" {
  name                        = "${var.project_id}-data-raw"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  depends_on = [
    google_project_service.required_services
  ]

  versioning {
    enabled = true
  }
}

# na quarentena aplico ciclo de vida para economizar armazenamento
resource "google_storage_bucket" "quarantine" {
  name                        = "${var.project_id}-data-quarantine"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  depends_on = [
    google_project_service.required_services
  ]

  # movo arquivos isolados ha mais de 30 dias para a classe nearline
  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = 30
    }
  }

  # deleto historico de quarentena apos 90 dias
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 90
    }
  }
}

resource "google_storage_bucket" "curated" {
  name                        = "${var.project_id}-data-curated"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  depends_on = [
    google_project_service.required_services
  ]

  versioning {
    enabled = true
  }
}
