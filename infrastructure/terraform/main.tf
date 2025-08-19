# OMTX-Hub GKE Infrastructure
# Complete production-ready GKE setup with VPC, networking, and security

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
  
  # Uncomment and configure for production
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "omtx-hub/infrastructure"
  # }
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Local values
locals {
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
  
  labels = {
    environment = var.environment
    project     = "omtx-hub"
    managed_by  = "terraform"
  }
  region     = var.region
  zones      = var.zones
  
  # Common labels
  labels = {
    project     = "omtx-hub"
    environment = var.environment
    managed-by  = "terraform"
  }
  
  # Network configuration
  network_name    = "${var.environment}-omtx-hub-network"
  subnet_name     = "${var.environment}-omtx-hub-subnet"
  cluster_name    = "${var.environment}-omtx-hub-cluster"
  
  # CIDR ranges
  subnet_cidr           = var.subnet_cidr
  pods_cidr            = var.pods_cidr
  services_cidr        = var.services_cidr
  master_cidr          = var.master_cidr
}