# GKE Cluster Configuration

# Service account for GKE nodes
resource "google_service_account" "gke_nodes" {
  account_id   = "${local.cluster_name}-nodes"
  display_name = "GKE Nodes Service Account for ${local.cluster_name}"
  project      = local.project_id
}

# IAM bindings for node service account
resource "google_project_iam_member" "gke_nodes_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/storage.objectViewer"
  ])
  
  project = local.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

# Service account for OMTX-Hub application
resource "google_service_account" "omtx_hub_app" {
  account_id   = "${local.cluster_name}-app"
  display_name = "OMTX-Hub Application Service Account"
  project      = local.project_id
}

# IAM bindings for application service account
resource "google_project_iam_member" "omtx_hub_app_roles" {
  for_each = toset([
    "roles/storage.admin",
    "roles/datastore.user",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent"
  ])
  
  project = local.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.omtx_hub_app.email}"
}

# GKE Cluster
resource "google_container_cluster" "primary" {
  name     = local.cluster_name
  location = local.region
  
  # Regional cluster for high availability
  node_locations = local.zones
  
  # Network configuration
  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name
  
  # IP allocation policy for pods and services
  ip_allocation_policy {
    cluster_secondary_range_name  = "${local.subnet_name}-pods"
    services_secondary_range_name = "${local.subnet_name}-services"
  }
  
  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = var.enable_private_nodes
    enable_private_endpoint = false  # Keep public endpoint for CI/CD access
    master_ipv4_cidr_block = local.master_cidr
    
    master_global_access_config {
      enabled = true
    }
  }
  
  # Master authorized networks
  dynamic "master_authorized_networks_config" {
    for_each = var.master_authorized_networks != null ? [1] : []
    content {
      dynamic "cidr_blocks" {
        for_each = var.master_authorized_networks
        content {
          cidr_block   = cidr_blocks.value.cidr_block
          display_name = cidr_blocks.value.display_name
        }
      }
    }
  }
  
  # Network policy
  network_policy {
    enabled  = var.enable_network_policy
    provider = var.enable_network_policy ? "CALICO" : null
  }
  
  # Enable network policy addon
  addons_config {
    network_policy_config {
      disabled = !var.enable_network_policy
    }
    
    http_load_balancing {
      disabled = false
    }
    
    horizontal_pod_autoscaling {
      disabled = false
    }
    
    cloudrun_config {
      disabled = true
    }
    
    dns_cache_config {
      enabled = true
    }
    
    gcp_filestore_csi_driver_config {
      enabled = false
    }
    
    gce_persistent_disk_csi_driver_config {
      enabled = true
    }
  }
  
  # Workload Identity
  dynamic "workload_identity_config" {
    for_each = var.enable_workload_identity ? [1] : []
    content {
      workload_pool = "${local.project_id}.svc.id.goog"
    }
  }
  
  # Logging and monitoring
  logging_service    = var.enable_logging ? "logging.googleapis.com/kubernetes" : "none"
  monitoring_service = var.enable_monitoring ? "monitoring.googleapis.com/kubernetes" : "none"
  
  # Enable shielded nodes for security
  enable_shielded_nodes = true
  
  # Enable Autopilot if specified
  enable_autopilot = var.enable_autopilot
  
  # Resource usage export (for cost management)
  resource_usage_export_config {
    enable_network_egress_metering       = true
    enable_resource_consumption_metering = true
    
    bigquery_destination {
      dataset_id = google_bigquery_dataset.gke_usage[0].dataset_id
    }
  }
  
  # Cluster autoscaling
  cluster_autoscaling {
    enabled = !var.enable_autopilot
    
    dynamic "resource_limits" {
      for_each = !var.enable_autopilot ? [1] : []
      content {
        resource_type = "cpu"
        minimum       = 4
        maximum       = 1000
      }
    }
    
    dynamic "resource_limits" {
      for_each = !var.enable_autopilot ? [1] : []
      content {
        resource_type = "memory"
        minimum       = 16
        maximum       = 4000
      }
    }
    
    auto_provisioning_defaults {
      oauth_scopes = [
        "https://www.googleapis.com/auth/cloud-platform"
      ]
      service_account = google_service_account.gke_nodes.email
      
      management {
        auto_repair  = true
        auto_upgrade = true
      }
      
      shielded_instance_config {
        enable_secure_boot          = true
        enable_integrity_monitoring = true
      }
    }
  }
  
  # Database encryption
  database_encryption {
    state    = "ENCRYPTED"
    key_name = google_kms_crypto_key.gke_key.id
  }
  
  # Maintenance policy
  maintenance_policy {
    recurring_window {
      start_time = "2023-01-01T02:00:00Z"
      end_time   = "2023-01-01T06:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SA"
    }
  }
  
  # Node pool configuration (only if not using Autopilot)
  dynamic "node_pool" {
    for_each = var.enable_autopilot ? [] : [1]
    content {
      name = "default-pool"
      
      # Start with minimal nodes, let autoscaling handle it
      initial_node_count = var.node_count
      
      # Autoscaling configuration
      autoscaling {
        min_node_count = var.min_node_count
        max_node_count = var.max_node_count
      }
      
      # Node configuration
      node_config {
        machine_type = var.node_machine_type
        disk_size_gb = var.node_disk_size
        disk_type    = var.node_disk_type
        
        # Use custom service account
        service_account = google_service_account.gke_nodes.email
        
        # OAuth scopes
        oauth_scopes = [
          "https://www.googleapis.com/auth/cloud-platform"
        ]
        
        # Labels for node identification
        labels = merge(local.labels, {
          node-type = "compute-optimized"
        })
        
        # Metadata
        metadata = {
          disable-legacy-endpoints = "true"
        }
        
        # Network tags
        tags = ["gke-node", "${local.cluster_name}-node"]
        
        # Preemptible nodes for cost savings (if enabled)
        preemptible = var.enable_preemptible_nodes
        spot        = var.enable_spot_nodes
        
        # Shielded instance config
        shielded_instance_config {
          enable_secure_boot          = true
          enable_integrity_monitoring = true
        }
        
        # Workload metadata config
        workload_metadata_config {
          mode = var.enable_workload_identity ? "GKE_METADATA" : "GCE_METADATA"
        }
      }
      
      # Node management
      management {
        auto_repair  = true
        auto_upgrade = true
      }
      
      # Upgrade settings
      upgrade_settings {
        max_surge       = 1
        max_unavailable = 0
      }
    }
  }
  
  # Binary authorization (for container image security)
  binary_authorization {
    enabled = true
  }
  
  # Pod security policy (deprecated but included for compatibility)
  pod_security_policy_config {
    enabled = false
  }
  
  # Vertical Pod Autoscaling
  vertical_pod_autoscaling {
    enabled = true
  }
  
  # Release channel for automatic updates
  release_channel {
    channel = "REGULAR"
  }
  
  # Notification config for cluster events
  notification_config {
    pubsub {
      enabled = true
      topic   = google_pubsub_topic.gke_notifications.id
    }
  }
  
  depends_on = [
    google_project_service.required_apis,
    google_compute_subnetwork.subnet,
    google_service_account.gke_nodes,
    google_kms_crypto_key.gke_key
  ]
  
  lifecycle {
    ignore_changes = [
      node_pool,
      initial_node_count,
    ]
  }
}

# Workload Identity binding
resource "google_service_account_iam_binding" "workload_identity" {
  count = var.enable_workload_identity ? 1 : 0
  
  service_account_id = google_service_account.omtx_hub_app.name
  role               = "roles/iam.workloadIdentityUser"
  
  members = [
    "serviceAccount:${local.project_id}.svc.id.goog[omtx-hub/omtx-hub-service-account]"
  ]
}

# KMS key for GKE encryption
resource "google_kms_key_ring" "gke" {
  name     = "${local.cluster_name}-keyring"
  location = local.region
}

resource "google_kms_crypto_key" "gke_key" {
  name     = "${local.cluster_name}-key"
  key_ring = google_kms_key_ring.gke.id
  purpose  = "ENCRYPT_DECRYPT"
  
  lifecycle {
    prevent_destroy = true
  }
}

# IAM binding for GKE to use the KMS key
resource "google_kms_crypto_key_iam_binding" "gke_key_binding" {
  crypto_key_id = google_kms_crypto_key.gke_key.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  
  members = [
    "serviceAccount:service-${data.google_project.project.number}@container-engine-robot.iam.gserviceaccount.com"
  ]
}

# Pub/Sub topic for GKE notifications
resource "google_pubsub_topic" "gke_notifications" {
  name = "${local.cluster_name}-notifications"
  
  labels = local.labels
}

# BigQuery dataset for resource usage export
resource "google_bigquery_dataset" "gke_usage" {
  count = var.enable_monitoring ? 1 : 0
  
  dataset_id  = "${replace(local.cluster_name, "-", "_")}_usage"
  description = "GKE resource usage data for ${local.cluster_name}"
  location    = "US"
  
  labels = local.labels
}

# Data source for project information
data "google_project" "project" {
  project_id = local.project_id
}