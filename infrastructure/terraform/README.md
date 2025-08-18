# OMTX-Hub Terraform Infrastructure

This directory contains Terraform configurations for deploying the complete OMTX-Hub infrastructure on Google Cloud Platform (GCP).

## 🏗️ Infrastructure Overview

The Terraform configuration creates:

- **GKE Cluster** with regional deployment and auto-scaling
- **VPC Network** with private subnets and security groups
- **Storage** buckets for application data and backups
- **Redis Cache** using Memorystore for rate limiting
- **Load Balancer** with global IP and SSL certificates
- **IAM** service accounts and security policies
- **KMS** encryption keys for data at rest
- **Monitoring** with Cloud Logging and Cloud Monitoring

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install Terraform
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform

# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
source ~/.bashrc
gcloud init

# Authenticate with GCP
gcloud auth login
gcloud auth application-default login
```

### 2. Configuration

```bash
# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your configuration
vim terraform.tfvars
```

Required variables:
```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"
environment = "production"
```

### 3. Deploy

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply
```

### 4. Connect to Cluster

```bash
# Get connection command from output
terraform output kubectl_connection_command

# Or run directly
gcloud container clusters get-credentials $(terraform output -raw cluster_name) \
  --region $(terraform output -raw region) \
  --project $(terraform output -raw project_id)
```

## 📁 File Structure

```
terraform/
├── main.tf                    # Main configuration and providers
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── vpc.tf                     # VPC, subnets, and networking
├── gke.tf                     # GKE cluster configuration
├── storage.tf                 # Storage buckets and databases
├── terraform.tfvars.example   # Example configuration
└── README.md                  # This file
```

## 🔧 Configuration Options

### Environment Sizing

**Production (High Performance)**
```hcl
environment = "production"
node_machine_type = "e2-standard-8"
min_node_count = 3
max_node_count = 20
enable_backup = true
enable_monitoring = true
```

**Staging (Balanced)**
```hcl
environment = "staging"
node_machine_type = "e2-standard-4"
min_node_count = 1
max_node_count = 10
enable_preemptible_nodes = true
```

**Development (Cost Optimized)**
```hcl
environment = "development"
node_machine_type = "e2-medium"
min_node_count = 1
max_node_count = 3
enable_spot_nodes = true
enable_backup = false
```

### Security Options

**High Security (Production)**
```hcl
enable_private_nodes = true
enable_network_policy = true
enable_workload_identity = true
master_authorized_networks = [
  {
    cidr_block = "203.0.113.0/24"
    display_name = "Office network"
  }
]
```

**Development (Relaxed)**
```hcl
enable_private_nodes = false
master_authorized_networks = [
  {
    cidr_block = "0.0.0.0/0"
    display_name = "All networks"
  }
]
```

### Cost Optimization

**Maximum Savings**
```hcl
enable_preemptible_nodes = true
enable_spot_nodes = true
enable_autopilot = true
enable_backup = false
node_machine_type = "e2-medium"
```

**Balanced Cost/Performance**
```hcl
enable_preemptible_nodes = true
node_machine_type = "e2-standard-4"
enable_backup = true
backup_retention_days = 7
```

## 🔍 Terraform Commands

### Basic Operations

```bash
# Initialize (first time only)
terraform init

# Validate configuration
terraform validate

# Format code
terraform fmt

# Plan changes
terraform plan

# Apply changes
terraform apply

# Show current state
terraform show

# List resources
terraform state list

# Destroy infrastructure (BE CAREFUL!)
terraform destroy
```

### Working with State

```bash
# Show specific resource
terraform state show google_container_cluster.primary

# Import existing resource
terraform import google_container_cluster.primary projects/PROJECT_ID/locations/REGION/clusters/CLUSTER_NAME

# Remove resource from state (doesn't delete)
terraform state rm google_container_cluster.primary

# Move resource in state
terraform state mv google_container_cluster.old google_container_cluster.new
```

### Workspaces (Multi-Environment)

```bash
# Create workspace
terraform workspace new staging

# List workspaces
terraform workspace list

# Switch workspace
terraform workspace select production

# Show current workspace
terraform workspace show
```

## 📊 Outputs

Key outputs available after deployment:

| Output | Description |
|--------|-------------|
| `cluster_name` | GKE cluster name |
| `cluster_endpoint` | GKE API server endpoint |
| `kubectl_connection_command` | Command to connect kubectl |
| `load_balancer_ip` | External IP address |
| `app_storage_bucket` | Main storage bucket |
| `redis_host` | Redis cache endpoint |
| `app_service_account_email` | Service account for workload identity |

```bash
# Show all outputs
terraform output

# Show specific output
terraform output cluster_name

# Show sensitive outputs
terraform output -raw cluster_ca_certificate
```

## 🔐 Security Best Practices

### State Management

**Use Remote State**
```hcl
terraform {
  backend "gcs" {
    bucket = "your-terraform-state-bucket"
    prefix = "omtx-hub/infrastructure"
  }
}
```

**Lock State**
```bash
# Enable state locking with backend configuration
terraform init -backend-config="bucket=your-state-bucket"
```

### Secrets Management

**Never Commit Secrets**
```bash
# Add to .gitignore
echo "terraform.tfvars" >> .gitignore
echo "*.tfstate*" >> .gitignore
echo ".terraform/" >> .gitignore
```

**Use Environment Variables**
```bash
export TF_VAR_project_id="your-project"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
```

### Access Control

**Service Account for Terraform**
```bash
# Create dedicated service account
gcloud iam service-accounts create terraform-sa

# Grant necessary permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:terraform-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/owner"

# Create and download key
gcloud iam service-accounts keys create terraform-sa-key.json \
  --iam-account=terraform-sa@PROJECT_ID.iam.gserviceaccount.com
```

## 🚨 Troubleshooting

### Common Issues

**1. Authentication Errors**
```bash
# Re-authenticate
gcloud auth application-default login

# Check current project
gcloud config get-value project

# Set project
gcloud config set project YOUR_PROJECT_ID
```

**2. API Not Enabled**
```bash
# Check enabled APIs
gcloud services list --enabled

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com
```

**3. Quota Exceeded**
```bash
# Check quotas
gcloud compute project-info describe --project=PROJECT_ID

# Request quota increase through console
```

**4. State Lock Issues**
```bash
# Force unlock (use carefully)
terraform force-unlock LOCK_ID

# Disable state locking temporarily
terraform plan -lock=false
```

### Debugging

**Enable Detailed Logging**
```bash
export TF_LOG=DEBUG
terraform plan
```

**Validate Configuration**
```bash
terraform validate
terraform plan -detailed-exitcode
```

**Check Resource Dependencies**
```bash
terraform graph | dot -Tpng > graph.png
```

## 🔄 Maintenance

### Updates

**Terraform Version**
```bash
# Check current version
terraform version

# Upgrade providers
terraform init -upgrade
```

**GKE Version**
```bash
# Check available versions
gcloud container get-server-config --region=us-central1

# Update cluster version in variables.tf
cluster_version = "1.29"

# Apply update
terraform plan
terraform apply
```

### Backup and Recovery

**State Backup**
```bash
# Download current state
terraform state pull > terraform.tfstate.backup

# Upload state (if needed)
terraform state push terraform.tfstate.backup
```

**Resource Recreation**
```bash
# Taint resource for recreation
terraform taint google_container_cluster.primary

# Apply to recreate
terraform apply
```

### Monitoring Costs

**Cost Estimation**
```bash
# Use cost estimation tools
terraform plan -out=plan.out
terraform show -json plan.out | cost-estimation-tool
```

**Resource Cleanup**
```bash
# Find unused resources
terraform state list | grep -v used_resource

# Remove unused resources
terraform state rm unused_resource
```

## 📞 Support

### Getting Help

1. **Terraform Documentation**: https://registry.terraform.io/providers/hashicorp/google
2. **GCP Documentation**: https://cloud.google.com/docs
3. **Community**: https://discuss.hashicorp.com/c/terraform-providers

### Emergency Procedures

**Complete Rollback**
```bash
# Revert to previous state
git checkout HEAD~1 -- .
terraform plan
terraform apply
```

**Emergency Resource Deletion**
```bash
# Remove resource protection
# Edit .tf files to remove lifecycle.prevent_destroy
terraform apply

# Then destroy
terraform destroy -target=resource.name
```