# Variables for OMTX-Hub Infrastructure

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "zones" {
  description = "GCP zones for multi-zone deployment"
  type        = list(string)
  default     = ["us-central1-a", "us-central1-b", "us-central1-c"]
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"
  
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be one of: production, staging, development."
  }
}

# Network Configuration
variable "subnet_cidr" {
  description = "CIDR range for the subnet"
  type        = string
  default     = "10.10.0.0/24"
}

variable "pods_cidr" {
  description = "CIDR range for pods"
  type        = string
  default     = "10.20.0.0/16"
}

variable "services_cidr" {
  description = "CIDR range for services"
  type        = string
  default     = "10.30.0.0/16"
}

variable "master_cidr" {
  description = "CIDR range for GKE master nodes"
  type        = string
  default     = "10.40.0.0/28"
}

# GKE Configuration
variable "cluster_version" {
  description = "GKE cluster version"
  type        = string
  default     = "1.28"
}

variable "node_count" {
  description = "Initial number of nodes per zone"
  type        = number
  default     = 1
}

variable "min_node_count" {
  description = "Minimum number of nodes per zone"
  type        = number
  default     = 1
}

variable "max_node_count" {
  description = "Maximum number of nodes per zone"
  type        = number
  default     = 10
}

variable "node_machine_type" {
  description = "Machine type for cluster nodes"
  type        = string
  default     = "e2-standard-4"
}

variable "node_disk_size" {
  description = "Disk size for cluster nodes (GB)"
  type        = number
  default     = 100
}

variable "node_disk_type" {
  description = "Disk type for cluster nodes"
  type        = string
  default     = "pd-standard"
}

variable "enable_preemptible_nodes" {
  description = "Enable preemptible nodes for cost savings"
  type        = bool
  default     = false
}

# Security Configuration
variable "enable_network_policy" {
  description = "Enable Kubernetes network policy"
  type        = bool
  default     = true
}

variable "enable_private_nodes" {
  description = "Enable private GKE nodes"
  type        = bool
  default     = true
}

variable "enable_workload_identity" {
  description = "Enable Workload Identity for secure GCP access"
  type        = bool
  default     = true
}

variable "master_authorized_networks" {
  description = "List of authorized networks for GKE master access"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = [
    {
      cidr_block   = "0.0.0.0/0"
      display_name = "All networks (configure for production)"
    }
  ]
}

# Storage Configuration
variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

# Monitoring Configuration
variable "enable_logging" {
  description = "Enable Google Cloud Logging"
  type        = bool
  default     = true
}

variable "enable_monitoring" {
  description = "Enable Google Cloud Monitoring"
  type        = bool
  default     = true
}

# Cost Management
variable "enable_autopilot" {
  description = "Use GKE Autopilot for simplified management"
  type        = bool
  default     = false
}

variable "enable_spot_nodes" {
  description = "Enable Spot VMs for cost optimization"
  type        = bool
  default     = false
}

# Database Configuration
variable "enable_cloud_sql" {
  description = "Create Cloud SQL instance for metadata"
  type        = bool
  default     = false
}

variable "enable_memorystore" {
  description = "Create Memorystore Redis instance"
  type        = bool
  default     = true
}

# Load Balancer Configuration
variable "enable_global_load_balancer" {
  description = "Create global load balancer with SSL"
  type        = bool
  default     = true
}

variable "ssl_domains" {
  description = "Domains for SSL certificate"
  type        = list(string)
  default     = ["api.omtx-hub.com"]
}

# Backup and DR
variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}

# Resource Quotas
variable "resource_quotas" {
  description = "Resource quotas for the cluster"
  type = object({
    cpu_limit    = string
    memory_limit = string
    storage_limit = string
  })
  default = {
    cpu_limit    = "1000"
    memory_limit = "4000Gi"
    storage_limit = "10Ti"
  }
}