# VPC and Networking Configuration

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "storage.googleapis.com",
    "firestore.googleapis.com",
    "redis.googleapis.com"
  ])
  
  project = local.project_id
  service = each.value
  
  disable_on_destroy = false
}

# Custom VPC Network
resource "google_compute_network" "vpc" {
  name                    = local.network_name
  auto_create_subnetworks = false
  routing_mode           = "GLOBAL"
  
  depends_on = [google_project_service.required_apis]
  
  labels = local.labels
}

# Subnet for GKE cluster
resource "google_compute_subnetwork" "subnet" {
  name          = local.subnet_name
  network       = google_compute_network.vpc.id
  ip_cidr_range = local.subnet_cidr
  region        = local.region
  
  # Secondary IP ranges for GKE
  secondary_ip_range {
    range_name    = "${local.subnet_name}-pods"
    ip_cidr_range = local.pods_cidr
  }
  
  secondary_ip_range {
    range_name    = "${local.subnet_name}-services"
    ip_cidr_range = local.services_cidr
  }
  
  # Enable private Google access
  private_ip_google_access = true
  
  # Enable flow logs for security monitoring
  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata            = "INCLUDE_ALL_METADATA"
  }
}

# Cloud Router for NAT
resource "google_compute_router" "router" {
  name    = "${local.network_name}-router"
  region  = local.region
  network = google_compute_network.vpc.id
}

# Cloud NAT for outbound internet access from private nodes
resource "google_compute_router_nat" "nat" {
  name                               = "${local.network_name}-nat"
  router                            = google_compute_router.router.name
  region                            = local.region
  nat_ip_allocate_option           = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall rules
resource "google_compute_firewall" "allow_internal" {
  name    = "${local.network_name}-allow-internal"
  network = google_compute_network.vpc.name
  
  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "icmp"
  }
  
  source_ranges = [
    local.subnet_cidr,
    local.pods_cidr,
    local.services_cidr
  ]
  
  description = "Allow internal communication within VPC"
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "${local.network_name}-allow-ssh"
  network = google_compute_network.vpc.name
  
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  
  # Restrict SSH access to specific IPs in production
  source_ranges = ["0.0.0.0/0"]  # Configure this for production
  target_tags   = ["ssh-access"]
  
  description = "Allow SSH access"
}

resource "google_compute_firewall" "allow_http_https" {
  name    = "${local.network_name}-allow-http-https"
  network = google_compute_network.vpc.name
  
  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
  
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server", "https-server"]
  
  description = "Allow HTTP and HTTPS traffic"
}

resource "google_compute_firewall" "allow_health_checks" {
  name    = "${local.network_name}-allow-health-checks"
  network = google_compute_network.vpc.name
  
  allow {
    protocol = "tcp"
    ports    = ["8000", "8080"]
  }
  
  # Google Cloud health check ranges
  source_ranges = [
    "130.211.0.0/22",
    "35.191.0.0/16"
  ]
  
  target_tags = ["health-check"]
  
  description = "Allow Google Cloud health checks"
}

# Static IP for load balancer
resource "google_compute_global_address" "lb_ip" {
  count = var.enable_global_load_balancer ? 1 : 0
  
  name         = "${local.cluster_name}-lb-ip"
  address_type = "EXTERNAL"
  
  labels = local.labels
}

# Reserve IP range for private service connection (if using Cloud SQL)
resource "google_compute_global_address" "private_service_range" {
  count = var.enable_cloud_sql ? 1 : 0
  
  name          = "${local.network_name}-private-service-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

# Private service connection for Cloud SQL
resource "google_service_networking_connection" "private_service_connection" {
  count = var.enable_cloud_sql ? 1 : 0
  
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_service_range[0].name]
  
  depends_on = [google_project_service.required_apis]
}