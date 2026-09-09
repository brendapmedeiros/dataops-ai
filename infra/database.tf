# deixo a criacao do cloud sql opcional para garantir custo zero em testes
resource "google_sql_database_instance" "postgres" {
  count            = var.enable_cloud_sql ? 1 : 0
  name             = "${var.project_id}-pg"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled = false
    }

    ip_configuration {
      ipv4_enabled = true
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "dataops_db" {
  count    = var.enable_cloud_sql ? 1 : 0
  name     = "dataops_ai"
  instance = google_sql_database_instance.postgres[0].name
}
