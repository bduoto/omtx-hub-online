# OMTX-Hub CI/CD Pipeline

This directory contains GitHub Actions workflows for automated testing, building, and deployment of the OMTX-Hub platform.

## 🚀 Workflows Overview

### 1. CI/CD Pipeline (`ci-cd.yml`)
**Main deployment pipeline for application code**

**Triggers:**
- Push to `main` (production deployment)
- Push to `develop` (staging deployment)  
- Pull requests to `main`

**Jobs:**
- **Security Scan**: Vulnerability scanning with Trivy
- **Backend Test**: Python unit tests, linting, type checking
- **Frontend Test**: Node.js tests, linting, type checking
- **Load Test**: Performance validation with Locust
- **Build & Push**: Docker image building and registry push
- **Deploy Staging**: Automated staging deployment
- **Deploy Production**: Production deployment with approval
- **Notify**: Deployment status notifications

### 2. Infrastructure Management (`infrastructure.yml`)
**Terraform infrastructure provisioning and management**

**Triggers:**
- Push to `main` (Terraform changes)
- Pull requests (validation only)
- Manual workflow dispatch

**Jobs:**
- **Terraform Validate**: Format and validation checks
- **Security Scan**: Infrastructure security with tfsec
- **Plan Staging/Production**: Infrastructure change planning
- **Apply**: Infrastructure deployment with approval
- **Cost Estimation**: Infrastructure cost analysis

### 3. Security Monitoring (`security.yml`)
**Comprehensive security scanning and compliance**

**Triggers:**
- Daily schedule (2 AM UTC)
- Push to main branches
- Pull requests
- Manual dispatch

**Jobs:**
- **Dependency Scan**: Python/Node.js vulnerability scanning
- **SAST**: Static application security testing with CodeQL
- **Secret Scan**: Credential leak detection with TruffleHog
- **Container Scan**: Docker image security scanning
- **Infrastructure Scan**: Terraform/Kubernetes security checks
- **Runtime Security**: Live application security validation
- **Compliance Check**: Security policy validation

## 🔧 Setup Instructions

### 1. Required GitHub Secrets

Create these secrets in your GitHub repository settings:

#### GCP Configuration
```
GCP_PROJECT_ID            # Staging GCP project ID
GCP_PROJECT_ID_STAGING     # Staging GCP project ID  
GCP_PROJECT_ID_PROD        # Production GCP project ID
GCP_SA_KEY                 # Staging service account key (JSON)
GCP_SA_KEY_PROD           # Production service account key (JSON)
GCP_REGION                # GCP region (e.g., us-central1)
```

#### Kubernetes Configuration
```
GKE_CLUSTER_NAME          # GKE cluster name
GKE_REGION               # GKE region
```

#### Terraform Configuration
```
TERRAFORM_STATE_BUCKET        # Staging Terraform state bucket
TERRAFORM_STATE_BUCKET_PROD   # Production Terraform state bucket
```

#### Security Configuration
```
SNYK_TOKEN               # Snyk security scanning token
INFRACOST_API_KEY        # Infrastructure cost estimation
```

#### Network Configuration (Optional)
```
OFFICE_CIDR              # Office network CIDR for GKE access
CI_CD_CIDR              # CI/CD network CIDR for GKE access
```

### 2. Service Account Setup

Create dedicated service accounts for CI/CD:

```bash
# Staging service account
gcloud iam service-accounts create github-actions-staging \
  --display-name="GitHub Actions Staging" \
  --project=$STAGING_PROJECT_ID

# Production service account  
gcloud iam service-accounts create github-actions-prod \
  --display-name="GitHub Actions Production" \
  --project=$PRODUCTION_PROJECT_ID

# Grant necessary permissions
for PROJECT in $STAGING_PROJECT_ID $PRODUCTION_PROJECT_ID; do
  SA_EMAIL="github-actions-$(echo $PROJECT | cut -d'-' -f2)@$PROJECT.iam.gserviceaccount.com"
  
  gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/container.developer"
    
  gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.admin"
    
  gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/compute.admin"
done

# Create and download keys
gcloud iam service-accounts keys create github-staging-key.json \
  --iam-account=github-actions-staging@$STAGING_PROJECT_ID.iam.gserviceaccount.com

gcloud iam service-accounts keys create github-prod-key.json \
  --iam-account=github-actions-prod@$PRODUCTION_PROJECT_ID.iam.gserviceaccount.com
```

### 3. GitHub Environments

Create GitHub environments for deployment protection:

1. **staging**
   - No protection rules (auto-deploy)
   - Environment secrets for staging

2. **production** 
   - Require reviewers: Add team members
   - Deployment branches: Limit to `main`
   - Environment secrets for production

### 4. Branch Protection

Configure branch protection for `main`:

```yaml
# .github/branch-protection.yml
protection_rules:
  main:
    required_status_checks:
      strict: true
      contexts:
        - "Backend Tests"
        - "Frontend Tests" 
        - "Security Scan"
        - "Terraform Validate"
    enforce_admins: true
    required_pull_request_reviews:
      required_approving_review_count: 2
      dismiss_stale_reviews: true
      require_code_owner_reviews: true
    restrictions: null
```

## 🔄 Deployment Process

### Staging Deployment
1. Push to `develop` branch
2. Automated testing and security scans
3. Docker image build and push
4. Automatic deployment to staging
5. Health checks and smoke tests

### Production Deployment
1. Create PR from `develop` to `main`
2. Code review and approval
3. Merge to `main` triggers production pipeline
4. Load testing execution
5. **Manual approval required** for production deployment
6. Blue-green deployment with health checks
7. Automatic rollback on failure

### Infrastructure Changes
1. Modify Terraform files
2. Create PR with infrastructure changes
3. Terraform plan automatically generated
4. Review and approve infrastructure changes
5. **Manual workflow dispatch** to apply changes
6. Cost estimation and compliance checks

## 📊 Monitoring and Alerting

### Pipeline Monitoring
- GitHub Actions dashboard
- Deployment status notifications
- Failed build alerts
- Security scan results

### Security Monitoring
- Daily vulnerability scans
- Dependency security alerts
- Secret leak detection
- Compliance policy violations

### Cost Monitoring
- Infrastructure cost estimation
- Resource usage tracking
- Cost anomaly detection
- Budget threshold alerts

## 🚨 Troubleshooting

### Common Issues

**1. Authentication Failures**
```bash
# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:github-actions*"

# Verify key format
cat github-key.json | jq .
```

**2. Terraform State Locks**
```bash
# List state locks
gsutil ls gs://$TERRAFORM_STATE_BUCKET/**/*.tflock

# Force unlock (use carefully)
terraform force-unlock LOCK_ID
```

**3. Docker Build Failures**
```bash
# Check build context
docker build --no-cache -t test .

# Verify base image
docker pull python:3.11-slim
```

**4. GKE Deployment Issues**
```bash
# Check cluster connectivity
kubectl cluster-info

# Verify deployment status
kubectl get deployments -n omtx-hub
kubectl describe deployment omtx-hub-backend -n omtx-hub
```

### Emergency Procedures

**1. Rollback Production Deployment**
```bash
# Manual rollback via GitHub Actions
# 1. Go to Actions tab
# 2. Find latest successful deployment
# 3. Re-run deployment job

# Or via kubectl
kubectl rollout undo deployment/omtx-hub-backend -n omtx-hub
```

**2. Disable Automatic Deployments**
```bash
# Temporarily disable workflows
# 1. Rename workflow files to .yml.disabled
# 2. Or use repository settings to disable Actions
```

**3. Emergency Infrastructure Changes**
```bash
# Direct Terraform apply (bypass CI/CD)
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

## 📋 Security Best Practices

### Secret Management
- Use GitHub secrets for all sensitive data
- Rotate service account keys quarterly
- Use environment-specific secrets
- Never commit secrets to version control

### Access Control
- Limit repository access to authorized personnel
- Use branch protection rules
- Require code reviews for all changes
- Enable audit logging

### Compliance
- Regular security scans
- Dependency updates
- Infrastructure compliance checks
- Security policy enforcement

## 🔗 Related Documentation

- [Kubernetes Deployment Guide](../infrastructure/k8s/README.md)
- [Terraform Infrastructure Guide](../infrastructure/terraform/README.md)
- [Security Policy](../SECURITY.md)
- [Contributing Guidelines](../CONTRIBUTING.md)