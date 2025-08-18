# Storage Configuration

# Cloud Storage bucket for application data
resource "google_storage_bucket" "app_storage" {
  name     = "${local.project_id}-${local.environment}-omtx-hub-storage"
  location = local.region
  
  # Prevent accidental deletion
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }
  
  # Enable versioning for data protection
  versioning {
    enabled = true
  }
  
  # Encryption
  encryption {
    default_kms_key_name = google_kms_crypto_key.storage_key.id
  }
  
  # Public access prevention
  public_access_prevention = "enforced"
  
  # Uniform bucket-level access
  uniform_bucket_level_access = true
  
  labels = local.labels
}

# Cloud Storage bucket for backups
resource "google_storage_bucket" "backup_storage" {
  count = var.enable_backup ? 1 : 0
  
  name     = "${local.project_id}-${local.environment}-omtx-hub-backups"
  location = local.region
  
  # Backup retention policy
  lifecycle_rule {
    condition {
      age = var.backup_retention_days
    }
    action {
      type = "Delete"
    }
  }
  
  # Archive old backups for cost savings
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
  
  # Enable versioning
  versioning {
    enabled = true
  }
  
  # Encryption
  encryption {
    default_kms_key_name = google_kms_crypto_key.storage_key.id
  }
  
  # Public access prevention
  public_access_prevention = "enforced"
  
  # Uniform bucket-level access
  uniform_bucket_level_access = true
  
  labels = merge(local.labels, {
    purpose = "backup"
  })
}

# Cloud Storage bucket for Terraform state (optional)
resource "google_storage_bucket" "terraform_state" {
  name     = "${local.project_id}-terraform-state"
  location = local.region
  
  # Prevent deletion of state files
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
  
  # Enable versioning for state history
  versioning {
    enabled = true
  }
  
  # Encryption
  encryption {
    default_kms_key_name = google_kms_crypto_key.storage_key.id
  }
  
  # Public access prevention
  public_access_prevention = "enforced"
  
  # Uniform bucket-level access
  uniform_bucket_level_access = true
  
  labels = merge(local.labels, {
    purpose = "terraform-state"
  })
}

# KMS key for storage encryption
resource "google_kms_crypto_key" "storage_key" {
  name     = "${local.cluster_name}-storage-key"
  key_ring = google_kms_key_ring.gke.id
  purpose  = "ENCRYPT_DECRYPT"
  
  rotation_period = "2592000s" # 30 days
  
  lifecycle {
    prevent_destroy = true
  }
}

# IAM binding for storage service account
resource "google_storage_bucket_iam_member" "app_storage_admin" {
  bucket = google_storage_bucket.app_storage.name
  role   = "roles/storage.admin"
  member = "serviceAccount:${google_service_account.omtx_hub_app.email}"
}

resource "google_storage_bucket_iam_member" "backup_storage_admin" {
  count = var.enable_backup ? 1 : 0
  
  bucket = google_storage_bucket.backup_storage[0].name
  role   = "roles/storage.admin"
  member = "serviceAccount:${google_service_account.omtx_hub_app.email}"
}

# Memorystore Redis instance
resource "google_redis_instance" "cache" {
  count = var.enable_memorystore ? 1 : 0
  
  name           = "${local.cluster_name}-redis"
  memory_size_gb = 2
  region         = local.region
  
  # Network configuration
  authorized_network   = google_compute_network.vpc.id
  connect_mode        = "PRIVATE_SERVICE_ACCESS"
  redis_version       = "REDIS_6_X"
  
  # High availability configuration
  tier                = "STANDARD_HA"
  replica_count      = 1
  read_replicas_mode = "READ_REPLICAS_ENABLED"
  
  # Security
  auth_enabled       = true
  transit_encryption_mode = "SERVER_CLIENT"
  
  # Maintenance
  maintenance_policy {
    weekly_maintenance_window {
      day = "SATURDAY"
      start_time {
        hours   = 2
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
  }
  
  # Backup configuration
  persistence_config {
    persistence_mode    = "RDB"
    rdb_snapshot_period = "TWELVE_HOURS"
  }
  
  labels = merge(local.labels, {
    service = "redis-cache"
  })
  
  depends_on = [google_project_service.required_apis]
}

# Cloud SQL instance (optional)
resource "google_sql_database_instance" "postgres" {
  count = var.enable_cloud_sql ? 1 : 0
  
  name             = "${local.cluster_name}-postgres"
  database_version = "POSTGRES_14"
  region          = local.region
  
  settings {
    tier              = "db-f1-micro"
    availability_type = "REGIONAL"
    
    # Backup configuration
    backup_configuration {
      enabled                        = true
      start_time                    = "02:00"
      location                      = local.region
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 30
      }
    }
    
    # IP configuration
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
      require_ssl     = true
    }
    
    # Maintenance window
    maintenance_window {
      day          = 7  # Sunday
      hour         = 2
      update_track = "stable"
    }
    
    # Database flags
    database_flags {
      name  = "log_statement"
      value = "all"
    }
    
    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"
    }
    
    # Disk configuration
    disk_autoresize       = true
    disk_autoresize_limit = 100
    disk_size            = 20
    disk_type            = "PD_SSD"
    
    # Performance insights
    insights_config {
      query_insights_enabled  = true
      query_string_length    = 1024
      record_application_tags = true
      record_client_address  = true
    }
  }
  
  # Deletion protection
  deletion_protection = true
  
  depends_on = [
    google_service_networking_connection.private_service_connection
  ]
}

# Cloud SQL database
resource "google_sql_database" "app_db" {
  count = var.enable_cloud_sql ? 1 : 0
  
  name     = "omtx_hub"
  instance = google_sql_database_instance.postgres[0].name
}

# Cloud SQL user
resource "google_sql_user" "app_user" {
  count = var.enable_cloud_sql ? 1 : 0
  
  name     = "omtx_hub_user"
  instance = google_sql_database_instance.postgres[0].name
  password = random_password.db_password[0].result
}

# Random password for database
resource "random_password" "db_password" {
  count = var.enable_cloud_sql ? 1 : 0
  
  length  = 32
  special = true
}

# Secret for database password
resource "google_secret_manager_secret" "db_password" {
  count = var.enable_cloud_sql ? 1 : 0
  
  secret_id = "${local.cluster_name}-db-password"
  
  replication {
    automatic = true
  }
  
  labels = local.labels
}

resource "google_secret_manager_secret_version" "db_password" {
  count = var.enable_cloud_sql ? 1 : 0
  
  secret      = google_secret_manager_secret.db_password[0].id
  secret_data = random_password.db_password[0].result
}