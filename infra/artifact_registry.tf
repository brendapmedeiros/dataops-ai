# configuro o repositorio no artifact registry para armazenar as imagens docker
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "dataops-ai"
  description   = "Repositorio Docker para imagens do DataOps AI"
  format        = "DOCKER"

  depends_on = [
    google_project_service.required_services
  ]
}
