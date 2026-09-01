variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "region" {
  description = "Cloud Run region. Must stay inside the always-free set."
  type        = string
  default     = "us-east1"
  validation {
    # Deploying outside these three silently starts billing, and the first
    # sign is an invoice.
    condition     = contains(["us-east1", "us-central1", "us-west1"], var.region)
    error_message = "Cloud Run's always-free tier covers only us-east1, us-central1 and us-west1."
  }
}

variable "api_image" {
  description = "Fully qualified API image, digest-pinned"
  type        = string
}

variable "ingestion_image" {
  description = "Fully qualified ingestion image, digest-pinned"
  type        = string
}

variable "max_instances" {
  description = "Instance ceiling. A cap, not a target - it is the blast-radius limit on the free tier."
  type        = number
  default     = 3
}
