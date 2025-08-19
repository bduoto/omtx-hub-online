# Cloud Run Infrastructure for OMTX-Hub L4 Migration
# Distinguished Engineer Implementation - Production-ready with observability

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Local variables for configuration
locals {
  project_id = var.project_id
  region     = var.region
  
  # L4 GPU configuration
  gpu_config = {
    type  = "nvidia-l4"
    count = 1
  }
  
  # Resource limits optimized for L4
  l4_resources = {
    cpu_limit    = "8"      # 8 vCPUs for L4
    memory_limit = "32Gi"   # 32GB RAM (L4 needs extra for data preprocessing)
    gpu_limit    = "1"      # Single L4 GPU
  }
  
  # Common labels
  labels = {
    environment = var.environment
    component   = "ml-compute"
    gpu-type    = "l4"
    managed-by  = "terraform"
  }
}

# Cloud Run Service for synchronous predictions
resource "google_cloud_run_v2_service" "boltz2_service" {
  name     = "boltz2-service"
  location = local.region
  project  = local.project_id

  template {
    # Scaling configuration
    scaling {
      min_instance_count = 0   # Scale to zero when idle
      max_instance_count = 10  # Max 10 instances for cost control
    }
    
    # Service account with minimal permissions
    service_account = google_service_account.cloud_run_sa.email
    
    containers {
      name  = "boltz2-l4"
      image = "${var.container_registry}/${local.project_id}/boltz2-l4:latest"
      
      # Resource configuration for L4
      resources {
        limits = {
          cpu               = local.l4_resources.cpu_limit
          memory            = local.l4_resources.memory_limit
          "nvidia.com/gpu"  = local.l4_resources.gpu_limit
        }
        
        # Startup resources (lower for faster cold starts)
        startup_cpu_boost = true
      }
      
      # GPU configuration
      dynamic "gpu" {
        for_each = [local.gpu_config]
        content {
          type  = gpu.value.type
          count = gpu.value.count
        }
      }
      
      # Environment variables for L4 optimization
      env {
        name  = "GPU_TYPE"
        value = "L4"
      }
      
      env {
        name  = "CUDA_VISIBLE_DEVICES"
        value = "0"
      }
      
      env {
        name  = "TORCH_CUDA_ARCH_LIST"
        value = "8.9"  # L4 architecture
      }
      
      env {
        name  = "TF32_ENABLE"
        value = "1"
      }
      
      env {
        name  = "CUBLAS_WORKSPACE_CONFIG"
        value = ":4096:8"
      }
      
      # GCP configuration
      env {
        name  = "GCP_PROJECT_ID"
        value = local.project_id
      }
      
      env {
        name  = "GCS_BUCKET_NAME"
        value = var.storage_bucket_name
      }
      
      # Performance tuning
      env {
        name  = "OPTIMIZATION_LEVEL"
        value = "aggressive"
      }
      
      env {
        name  = "MAX_VRAM_GB"
        value = "22"  # Conservative L4 limit
      }
      
      # Health check endpoint
      ports {
        container_port = 8080
        name          = "http1"
      }
      
      # Startup probe for GPU initialization
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 60   # GPU initialization time
        timeout_seconds      = 30
        period_seconds       = 10
        failure_threshold    = 6
      }
      
      # Liveness probe
      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 120
        timeout_seconds      = 30
        period_seconds       = 60
        failure_threshold    = 3
      }
      
      # Volume mounts for shared memory (important for DataLoader)
      volume_mounts {
        name       = "dshm"
        mount_path = "/dev/shm"
      }
    }
    
    # Shared memory volume for efficient data loading
    volumes {
      name = "dshm"
      empty_dir {
        medium     = "Memory"
        size_limit = "8Gi"
      }
    }
    
    # Timeout configuration
    timeout = "3600s"  # 1 hour timeout for large proteins
    
    # Execution environment
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"
    
    # Labels
    labels = local.labels
  }
  
  # Traffic configuration
  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
  
  depends_on = [
    google_project_service.cloud_run_api,
    google_service_account.cloud_run_sa
  ]
}

# Cloud Run Job for batch processing
resource "google_cloud_run_v2_job" "boltz2_batch" {
  name     = "boltz2-batch"
  location = local.region
  project  = local.project_id

  template {
    # Job configuration
    parallelism = 10  # Max 10 parallel tasks
    task_count  = 1   # Will be overridden at runtime
    
    template {
      # Service account
      service_account = google_service_account.cloud_run_sa.email
      
      # Task timeout
      task_timeout = "7200s"  # 2 hours per task
      
      containers {
        name  = "boltz2-batch-l4"
        image = "${var.container_registry}/${local.project_id}/boltz2-l4:latest"
        
        # Resource configuration (same as service)
        resources {
          limits = {
            cpu               = local.l4_resources.cpu_limit
            memory            = local.l4_resources.memory_limit
            "nvidia.com/gpu"  = local.l4_resources.gpu_limit
          }
        }
        
        # GPU configuration
        dynamic "gpu" {
          for_each = [local.gpu_config]
          content {
            type  = gpu.value.type
            count = gpu.value.count
          }
        }
        
        # Environment variables (same as service + batch-specific)
        env {
          name  = "EXECUTION_MODE"
          value = "batch"
        }
        
        env {
          name  = "GPU_TYPE"
          value = "L4"
        }
        
        env {
          name  = "GCP_PROJECT_ID"
          value = local.project_id
        }
        
        env {
          name  = "GCS_BUCKET_NAME"
          value = var.storage_bucket_name
        }
        
        env {
          name  = "OPTIMIZATION_LEVEL"
          value = "aggressive"
        }
        
        # Batch processing configuration
        env {
          name  = "BATCH_SIZE"
          value = "8"  # Optimal for L4
        }
        
        env {
          name  = "PARALLEL_SHARDS"
          value = "true"
        }
        
        # Volume mounts
        volume_mounts {
          name       = "dshm"
          mount_path = "/dev/shm"
        }
      }
      
      # Shared memory volume
      volumes {
        name = "dshm"
        empty_dir {
          medium     = "Memory"
          size_limit = "8Gi"
        }
      }
    }
  }
  
  # Labels
  labels = local.labels
  
  depends_on = [
    google_project_service.cloud_run_api,
    google_service_account.cloud_run_sa
  ]
}

# Service account for Cloud Run services
resource "google_service_account" "cloud_run_sa" {
  account_id   = "cloud-run-boltz2"
  display_name = "Cloud Run Boltz2 Service Account"
  description  = "Service account for Boltz2 Cloud Run services with L4 GPU"
  project      = local.project_id
}

# IAM bindings for service account
resource "google_project_iam_member" "cloud_run_storage" {
  project = local.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "cloud_run_firestore" {
  project = local.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "cloud_run_monitoring" {
  project = local.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Enable required APIs
resource "google_project_service" "cloud_run_api" {
  project = local.project_id
  service = "run.googleapis.com"
  
  disable_dependent_services = false
  disable_on_destroy        = false
}

resource "google_project_service" "eventarc_api" {
  project = local.project_id
  service = "eventarc.googleapis.com"
  
  disable_dependent_services = false
  disable_on_destroy        = false
}

# Cloud Run service IAM for public access (if needed)
resource "google_cloud_run_service_iam_member" "public_access" {
  count = var.allow_public_access ? 1 : 0
  
  location = google_cloud_run_v2_service.boltz2_service.location
  project  = google_cloud_run_v2_service.boltz2_service.project
  service  = google_cloud_run_v2_service.boltz2_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "boltz2_service_url" {
  description = "URL of the Boltz2 Cloud Run service"
  value       = google_cloud_run_v2_service.boltz2_service.uri
}

output "boltz2_batch_job_name" {
  description = "Name of the Boltz2 batch job"
  value       = google_cloud_run_v2_job.boltz2_batch.name
}

output "service_account_email" {
  description = "Email of the Cloud Run service account"
  value       = google_service_account.cloud_run_sa.email
}

# Variables
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run services"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "container_registry" {
  description = "Container registry URL"
  type        = string
  default     = "gcr.io"
}

variable "storage_bucket_name" {
  description = "GCS bucket name for job files"
  type        = string
}

variable "allow_public_access" {
  description = "Allow public access to Cloud Run service"
  type        = bool
  default     = false
}
