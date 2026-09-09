# defino as variaveis centrais do projeto
variable "project_id" {
  description = "identificador do projeto no google cloud"
  type        = string
  default     = "dataops-ai-prod"
}

variable "region" {
  description = "regiao padrao dos servicos"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "ambiente de implantacao"
  type        = string
  default     = "production"
}

variable "gemini_model" {
  description = "modelo padrao do gemini para diagnostico"
  type        = string
  default     = "gemini-2.5-flash"
}

# mantenho falso por padrao para evitar custos acidentais de cloud sql
variable "enable_cloud_sql" {
  description = "ativa instancia gerenciada do cloud sql quando necessario"
  type        = bool
  default     = false
}

