# GCP Authentication Setup Guide

## 🏆 RECOMMENDED: Service Account Authentication

### Step 1: Create a Service Account
```bash
# Create service account
gcloud iam service-accounts create omtx-hub-service \
    --description="OMTX Hub Service Account" \
    --display-name="OMTX Hub"

# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:omtx-hub-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:omtx-hub-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
```

### Step 2: Create and Download Key
```bash
# Create key file
gcloud iam service-accounts keys create ~/omtx-hub-service-key.json \
    --iam-account=omtx-hub-service@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Move to secure location
mkdir -p ~/.config/gcp
mv ~/omtx-hub-service-key.json ~/.config/gcp/
chmod 600 ~/.config/gcp/omtx-hub-service-key.json
```

### Step 3: Set Environment Variable
Add to your shell profile (~/.bashrc, ~/.zshrc, etc.):
```bash
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcp/omtx-hub-service-key.json"
```

## 🔄 ALTERNATIVE: Application Default Credentials (ADC)

### For Development (Current Method)
```bash
# One-time setup - creates long-lived credentials
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform
```

### For Production Servers
```bash
# On GCP Compute Engine/Cloud Run - automatic
# Uses instance service account
```

## 🛡️ SECURITY BEST PRACTICES

### 1. Service Account Permissions
- Use principle of least privilege
- Only grant necessary roles:
  - `roles/datastore.user` for Firestore
  - `roles/storage.objectAdmin` for Cloud Storage

### 2. Key Management
- Store keys outside of version control
- Use environment variables
- Rotate keys regularly (every 90 days)
- Monitor key usage

### 3. Environment-Specific Setup
```bash
# Development
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcp/omtx-hub-dev-key.json"

# Production
export GOOGLE_APPLICATION_CREDENTIALS="/etc/gcp/omtx-hub-prod-key.json"
```

## 🔧 IMPLEMENTATION IN CODE

The application will automatically use credentials in this order:
1. GOOGLE_APPLICATION_CREDENTIALS environment variable
2. gcloud ADC credentials
3. GCP instance metadata (on GCP)

No code changes needed - Google client libraries handle this automatically!
