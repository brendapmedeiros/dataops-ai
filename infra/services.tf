# ativo as apis necessarias no gcp para garantir que o terraform funcione em projeto novo
resource "google_project_service" "required_services" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}
