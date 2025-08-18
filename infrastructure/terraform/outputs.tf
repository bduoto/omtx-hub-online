# Terraform Outputs

output "project_id" {
  description = "GCP project ID"
  value       = local.project_id
}

output "region" {
  description = "GCP region"
  value       = local.region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# Network outputs
output "vpc_name" {
  description = "VPC network name"
  value       = google_compute_network.vpc.name
}

output "vpc_id" {
  description = "VPC network ID"
  value       = google_compute_network.vpc.id
}

output "subnet_name" {
  description = "Subnet name"
  value       = google_compute_subnetwork.subnet.name
}

output "subnet_cidr" {
  description = "Subnet CIDR range"
  value       = google_compute_subnetwork.subnet.ip_cidr_range
}

output "pods_cidr" {
  description = "Pods secondary CIDR range"
  value       = local.pods_cidr
}

output "services_cidr" {
  description = "Services secondary CIDR range"
  value       = local.services_cidr
}

# GKE outputs
output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "GKE cluster CA certificate"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "cluster_location" {
  description = "GKE cluster location"
  value       = google_container_cluster.primary.location
}

output "cluster_node_locations" {
  description = "GKE cluster node locations"
  value       = google_container_cluster.primary.node_locations
}

# Service account outputs
output "gke_service_account_email" {
  description = "GKE nodes service account email"
  value       = google_service_account.gke_nodes.email
}

output "app_service_account_email" {
  description = "Application service account email"
  value       = google_service_account.omtx_hub_app.email
}

# Storage outputs
output "app_storage_bucket" {
  description = "Application storage bucket name"
  value       = google_storage_bucket.app_storage.name
}

output "app_storage_url" {
  description = "Application storage bucket URL"
  value       = google_storage_bucket.app_storage.url
}

output "backup_storage_bucket" {
  description = "Backup storage bucket name"
  value       = var.enable_backup ? google_storage_bucket.backup_storage[0].name : null
}

output "terraform_state_bucket" {
  description = "Terraform state bucket name"
  value       = google_storage_bucket.terraform_state.name
}

# Load balancer outputs
output "load_balancer_ip" {
  description = "Global load balancer IP address"
  value       = var.enable_global_load_balancer ? google_compute_global_address.lb_ip[0].address : null
}

output "load_balancer_ip_name" {
  description = "Global load balancer IP address name"
  value       = var.enable_global_load_balancer ? google_compute_global_address.lb_ip[0].name : null
}

# Redis outputs
output "redis_host" {
  description = "Redis instance host"
  value       = var.enable_memorystore ? google_redis_instance.cache[0].host : null
  sensitive   = true
}

output "redis_port" {
  description = "Redis instance port"
  value       = var.enable_memorystore ? google_redis_instance.cache[0].port : null
}

output "redis_auth_string" {
  description = "Redis auth string"
  value       = var.enable_memorystore ? google_redis_instance.cache[0].auth_string : null
  sensitive   = true
}

# Database outputs
output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = var.enable_cloud_sql ? google_sql_database_instance.postgres[0].connection_name : null
}

output "database_private_ip" {
  description = "Cloud SQL private IP address"
  value       = var.enable_cloud_sql ? google_sql_database_instance.postgres[0].private_ip_address : null
  sensitive   = true
}

output "database_name" {
  description = "Database name"
  value       = var.enable_cloud_sql ? google_sql_database.app_db[0].name : null
}

output "database_user" {
  description = "Database user name"
  value       = var.enable_cloud_sql ? google_sql_user.app_user[0].name : null
}

# KMS outputs
output "gke_kms_key" {
  description = "GKE encryption KMS key ID"
  value       = google_kms_crypto_key.gke_key.id
}

output "storage_kms_key" {
  description = "Storage encryption KMS key ID"
  value       = google_kms_crypto_key.storage_key.id
}

# Pub/Sub outputs
output "gke_notifications_topic" {
  description = "GKE notifications Pub/Sub topic"
  value       = google_pubsub_topic.gke_notifications.name
}

# Connection commands
output "kubectl_connection_command" {
  description = "Command to connect kubectl to the cluster"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${google_container_cluster.primary.location} --project ${local.project_id}"
}

output "docker_registry" {
  description = "Docker registry URL for this project"
  value       = "gcr.io/${local.project_id}"
}

# Deployment information
output "deployment_info" {
  description = "Key information for deployment"
  value = {
    project_id      = local.project_id
    cluster_name    = google_container_cluster.primary.name
    cluster_region  = google_container_cluster.primary.location
    vpc_network     = google_compute_network.vpc.name
    subnet_name     = google_compute_subnetwork.subnet.name
    service_account = google_service_account.omtx_hub_app.email
    storage_bucket  = google_storage_bucket.app_storage.name
    
    # Connection details
    kubectl_command = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${google_container_cluster.primary.location} --project ${local.project_id}"
    docker_registry = "gcr.io/${local.project_id}"
    
    # Load balancer (if enabled)
    load_balancer_ip = var.enable_global_load_balancer ? google_compute_global_address.lb_ip[0].address : null
    
    # Redis (if enabled)
    redis_host = var.enable_memorystore ? google_redis_instance.cache[0].host : null
    redis_port = var.enable_memorystore ? google_redis_instance.cache[0].port : null
    
    # Database (if enabled)
    database_connection = var.enable_cloud_sql ? google_sql_database_instance.postgres[0].connection_name : null
  }
  sensitive = true
}

# Environment-specific configurations
output "environment_config" {
  description = "Environment-specific configuration values"
  value = {
    enable_autopilot     = var.enable_autopilot
    enable_memorystore   = var.enable_memorystore
    enable_cloud_sql     = var.enable_cloud_sql
    enable_backup        = var.enable_backup
    enable_monitoring    = var.enable_monitoring
    node_machine_type    = var.node_machine_type
    min_node_count       = var.min_node_count
    max_node_count       = var.max_node_count
    enable_private_nodes = var.enable_private_nodes
  }
}