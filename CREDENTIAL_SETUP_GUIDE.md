# 🔧 OMTX-Hub Credential Setup Guide

## Quick Fix for Production API

Your consolidated API is successfully deployed but needs real credentials to enable full batch processing functionality. This guide will get you up and running in 10 minutes.

## 🎯 What You Need

1. **GCP Service Account** - For Firestore database and Cloud Storage
2. **Modal API Tokens** - For GPU processing with Boltz-2, RFAntibody, Chai-1

---

## 📋 Part 1: GCP Service Account Setup

### Step 1: Create Service Account
```bash
# Set your project (already using om-models)
export PROJECT_ID="om-models"

# Create service account
gcloud iam service-accounts create omtx-hub-service \
    --description="OMTX-Hub production service account" \
    --display-name="OMTX-Hub Service Account" \
    --project=$PROJECT_ID
```

### Step 2: Grant Required Permissions
```bash
# Firestore database access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

# Cloud Storage access  
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

# Cloud Storage bucket creation (if needed)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

### Step 3: Generate and Download Key
```bash
# Create and download the service account key
gcloud iam service-accounts keys create ~/omtx-hub-credentials.json \
    --iam-account=omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com \
    --project=$PROJECT_ID

# Verify the key was created
ls -la ~/omtx-hub-credentials.json
```

### Step 4: Format for Kubernetes Secret
```bash
# Convert to single line for Kubernetes secret (removes newlines)
cat ~/omtx-hub-credentials.json | jq -c . > ~/omtx-hub-credentials-oneline.json

# Display the formatted JSON (copy this for next step)
cat ~/omtx-hub-credentials-oneline.json
```

---

## 🚀 Part 2: Modal API Token Setup

### Step 1: Get Modal Tokens
```bash
# Install Modal CLI if not already installed
pip install modal

# Authenticate and get tokens
modal token new

# Display your current tokens
modal token show
```

### Step 2: Find Your Token Values
Your Modal tokens are stored in `~/.modal.toml`:
```bash
# View your Modal configuration
cat ~/.modal.toml
```

Look for:
```toml
[default]
token_id = "ak-xxxxxxxxxxxxx"
token_secret = "as-xxxxxxxxxxxxx"
active = true
```

---

## 🔧 Part 3: Update Production Secrets

### Step 1: Update Kubernetes Secret
Edit the production secrets file:
```bash
# Edit the secrets file
nano production-secrets.yaml
```

Replace the placeholder values:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: omtx-hub-secrets
  namespace: omtx-hub
type: Opaque
stringData:
  GCP_CREDENTIALS_JSON: |
    {"type":"service_account","project_id":"om-models","private_key_id":"your-key-id","private_key":"-----BEGIN PRIVATE KEY-----\nYOUR-PRIVATE-KEY\n-----END PRIVATE KEY-----\n","client_email":"omtx-hub-service@om-models.iam.gserviceaccount.com","client_id":"your-client-id","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/omtx-hub-service%40om-models.iam.gserviceaccount.com"}
  MODAL_TOKEN_ID: "ak-your-actual-token-id"
  MODAL_TOKEN_SECRET: "as-your-actual-token-secret"
  REDIS_PASSWORD: "your-redis-password-if-using"
  JWT_SECRET_KEY: "your-jwt-secret-key-here"
  MODAL_WEBHOOK_SECRET: "generate-with-openssl-rand-hex-32"
```

### Step 2: Apply Updated Secrets
```bash
# Apply the updated secrets to your cluster
kubectl apply -f production-secrets.yaml

# Restart the deployment to pick up new secrets
kubectl rollout restart deployment/omtx-hub-backend -n omtx-hub

# Check deployment status
kubectl get pods -n omtx-hub -w
```

---

## ✅ Part 4: Verification

### Step 1: Test Database Connection
```bash
# Check pod logs for successful GCP connection
kubectl logs -n omtx-hub deployment/omtx-hub-backend | grep -i firestore

# Should see: "✅ Connected to GCP Firestore: om-models"
```

### Step 2: Test API Endpoints
```bash
# Test system status endpoint
curl http://34.29.29.170/api/v1/system/status

# Should return healthy status with database: "healthy"
```

### Step 3: Test Job Creation
```bash
# Test job submission
curl -X POST http://34.29.29.170/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model": "boltz2",
    "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLDAKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWUAIEMGIDSETWNTGGHMLLEYTDSSYEEKATRHYSAADLRLENTYYDSSNDHSSEIEITQLMNQLPPKLLQMDSSDTSDSQPGMISSSVQAIQGMISEAAHNSNTAAEQVNGESSITRIMSRQTSLNSEVGVPEQFNEDEAMDLLNDFGLLSQSHSADKRMLMDWDGYGMDYAQSVEDHSGQHIIIYHPPGATVIRLKDNFKLGQMISEAHLTASATQADATLGTFLNQSQATDRFYLESSFGAGMAELGSHIHTEMSRLSQSSGQKSSMYIGSNLIQAMLQQSTQMASSTSYEPSGGSEEDQESDIAGISIGPRISSLGLNNRFKIPSHPQGEAEQQHEGIEYIEDMILQHGSLTLTSLYEAIDLQMWAKQMYDLQGQLHLIRQNSQPLHYSDIFKGNSAEFDSEEDIRPQVLLNFTNQVGFQVTEQSYTGIPVGLQPSSNQAASQQLSLPQFSTKEGSISQPGFSPLMAADLLGRLLSVTHIKLDQNKDNSMKSHTTGDIPVEPKPKAKASSVWSVTYKSEYLRQQESLKESLRQNSQNGFLLSQSSFGPVTINASSFSQLGMNQSQLQQSQAGQQAQQQSQSGTIQAGLRLDNQAQLALVKLLNGLMQQQATGIQMTLQSLYAQSTAQFQRQLTQLMSVSLQQQAETPQHQPQQPQDQFTAVIKVMSQFLDQTHQASSQLHQEQLQRLGSFMQKLQQLAQPQFSLQMSTKQSQLNQTTQQLNRLSGGFQPLGEITSEEIAQLGASILSSFLRQQEHMGIQQLHSLSSQLQHMGMSDRQGFAQQFQQLQQWAQESGIRLSKFNQFVNPEQGSIIVRQGGIEGTLKLLQDLESLIKQAGGVQILNQNAEIVSLTQIASLVGAFNQEQGKFYQQLKNLSSALSGSLNKLVQQLPSLADNLSAKAMLGQTMQEQELQSQKVQQLNQKLQQLARQTEVVALYQELSAQLSQLSQQADQEAQMQSPKMDLTSQQLQLQQSQQTQVQRQLQEQYLQQLGSFTQRQLQQLTRKHLQQLQAVQQLHQQQGQLAHRLKNLQRHLNRSSLSHHRQQEQQLTADLHRRSGLFIRKLVGNASQSSASLQNQGISLQKLVQQLHQSQQYTNQLKTKLLSLEHGGQGSGQGTQLTQKKVSQSSQNGQLSVHRNRQGQSQSNQQLQAYEKFLQSLLQQQPQGHLSATNRQQYLGQGQQQQDQVHQNSHRISLQLQGISSMSRQLHSHSSLLGRVQALNQASQGEQTAYVEQQKSQMMLQKQSMQNQVLQYKHAEALQSRLQNLGGQHRNQSTGQLQTLMNQLMNHLSEAQTQQRLRQNSKLSQQLQRLAQLLLKQDERLQKKQTQGSPSIQQSAQQYQLQTQERAATTGATQAASRHQQFGLVQQKQAAQQKNQTADHQHQHNSQAQQLMQQLHLQDAPGQNPQGQLEQLPPQKSPTQTQQATQLQLYNRLQKHQDQVATTIQNLQNQQQINQLSGQQQQAENQLSTISVAQLQNKQQQQLNALQRTAKNQRDQEDLDLQTQAHVLSQQVSQSYDLQTQASHLQQQAHSLSLILSTQKLQYQQLQKSDGQMPKASRNQGSDMQLSAQTLQQQANQTNQEQSLQQQFQHLQQLQTNQDNTLQERLEQQLVGNRNQAGQAQQERPTGQKQLQTAHQLGQQQLEQPKQNQEEQTTQEQQQATQQQTQQQQVQSQSEDQRLTGQQEGAELQSEQEQEMQMKQQQTQQQQQGLQLQQPLQAQQQEQSQGQRQLHQHQQLQQQDDNSDEQAADQIEQKKQATQASQMKQSQQQRLAQHQQQKQLQKQQTALHTQSQAQQEQLQNQNQNQGTEQSISEHQEQHGQLNQLQQTNTNAQERLQIQLQLSQKRLSLQLQLRQQQNQQQGNMLENLISAHTQQMVQRDQKQTNVGHLQGLLQNSMLSHLQNLQREQQRAENQTQGKSQIQHNQRQLHQGLTATLQMHSQQQRQENQNQNKSMLQIQLQNSRRTQAQDAATEQGQRAQQTQSQHQQQGQRQHQQSMDQQEQTNELQQQAQKLQNQLQNQLADIQQLQNKHHQHHLLENQTQSQSTQKQNASELQKHQRQSQELQQAERLQQLQQRVLHLQGLRTASQDHQQVADHQQLRALQGQRQLQTRQQDQKQTIQQHHNLQQQKQLSMEAQTQQGGLQALQQAQRMQQMSQLQKRAQQQAADQVSQALNQLQSSRYRAQLKQQLHAQQLQQNLGQALQQTQLQGEQHQLQEEQQLQSEQGNLSGTPSSFSLLSSSSLQGQMEAEGQQQKLQDQLQAEKQQQIQLAQIQHLQAQQRRQQHQLQQQNQMQSTQSQHNQGQGAAQQQLQQQTQQQTMNQAQQGGQRQHGQHQGQQQGELQNGLQNAQLRQQTQQNQSHNSQAAQERQQHQQQKQATLQQQQSQRTQHQSQSQLQKLQSDMQKQHQGGQMQHQHQQAHGLQQLHQQTQQQQRHQQHQQNSAQLQPQMQSLQGGQRAQQHQAQQQQLQNLSGLSTTQLQAQQTQRHQAALQQQNGGQMHQHQQAHQLQRQHHHQSQQQHQQQQEHQHQNQTNQAQQRQHQGQGQQGRLQSQLQSQTAQQRRHLQDLQAQLQRRGLAHQQRQHQGLAALQQQNGGQMHQHQKLQALHQQHQQHHQSQTQGQHEQEQQQTLQAQLGQGMQGQLSQQVQRHALQHLQEQLHQQGLRQHQTQQQHQRLQAQLGQAQHHQHQQLQLQQQHQQQNGQHQLHQHQAHQNQLLNQYAQLQGALLMSGLRQHEQEQQHQTQQLGEQLQQQHQQGAGHQHQRTRNKRTEHQQNAHQLQAQLGQQMHLHQKQKDGQHQHQHTQLQAQAQGSQQNLLSQLQKQLQHHQQGGMMQLQQQQQHRQLAAQLQAAGLQHQRQQQHQTQQLGQHQGQHQQQHGLQQQHQQHHLQGGLLQQLQKQQQHQRTQAHLGRRHAQQGLQQLSGSRLGHQAAHQGQQHQLQQLQEQLNQLQTQQAQLRQHQQGGQHQQLHQHQAGQQQGLAHLQAAGGQLQQLQTQNQQTAAQLQQQMHAQQQKAKQQQLQGQALQQQHQAGGQQLQQLQGHAAQQQQGLRTQSNQKAEAQQRHEQKLQQQLLQQGLLQQLQQLNHQQGLLHQQQHQQQLQQQQQAQLQRQQQLLNGGQQQQLQQQQQTQQQLQQNQLQGLQQLQAAQQNHHQNGLQNLQGLLQQLHGQAQERQNQTQLQLAALQQQGRRQHQQQHQLQHQRHQQQGLQHGLQQQGHQGQHQAQLKQKLQLLLLQGQRKGRQLEQQQQHQHQAQLQAQQQGLHHSLQAHQLQQAQQQHGGLQGQHLQHMQHGGQRQAQLQQQHRGQHHQLQAQQGGHQQGGQRQQLHQHQHHQTQQHLQGLQQSSQQHRQHQHLQQAAQHRHQGQAHLQHLQHQQQNQLQYLQGQQQHQAHHQQQQQHQHQHQRRRQHQHLQHQLQQQGRQHQHTQHQHAQQGAQAHQHLQQRQHQHHQGQLQHQQHAQQGLRHQQQQHQSHQAQLRQHQHQQHQQGGLHQQGQHQHQHQQHHQHQHLHQQAGHQLQRQHQHHQGQHLQGHQHAHQAQQHRQHQHLQQAAQHRHQGQAHLQHLQHQQQNQLQYLQGQQQHQAHHQQQQQHQHQHQRRRQHQHLQHQLQQQGRQHQHTQHQHAQQGAQAHQHLQQRQHQHHQGQLQHQQHAQQGLRHQQQQHQSHQAQLRQHQHQQHQQGGLHQQGQHQHQHQQHHQHQHLHQQAGHQLQRQHQHHQGQHLQGHQHAHQAQQHRQHQHLQQ"
  }'
```

---

## 🎉 Success Indicators

When properly configured, you should see:

1. **Database Connection**: `✅ Connected to GCP Firestore: om-models`
2. **System Status**: `{"status": "healthy", "components": {"database": "healthy", "storage": "healthy"}}`
3. **Job Creation**: Jobs successfully created with status `"pending"` → `"running"` → `"completed"`

---

## 🚨 Troubleshooting

### Issue: Database Still Unavailable
```bash
# Check if secrets are applied
kubectl get secrets -n omtx-hub

# Check pod environment variables
kubectl exec -n omtx-hub deployment/omtx-hub-backend -- env | grep -i gcp
```

### Issue: Modal Authentication Failed
```bash
# Check Modal tokens in pod
kubectl exec -n omtx-hub deployment/omtx-hub-backend -- env | grep -i modal

# Verify tokens are valid
modal token show
```

### Issue: Pods Not Restarting
```bash
# Force restart deployment
kubectl rollout restart deployment/omtx-hub-backend -n omtx-hub

# Check restart status
kubectl rollout status deployment/omtx-hub-backend -n omtx-hub
```

---

## 📞 Need Help?

If you encounter issues:

1. **Check pod logs**: `kubectl logs -n omtx-hub deployment/omtx-hub-backend`
2. **Verify secrets**: `kubectl describe secret omtx-hub-secrets -n omtx-hub`
3. **Test endpoints**: Use the curl commands above to verify functionality

Once you complete these steps, your production API will have full batch processing capabilities with real GPU execution!