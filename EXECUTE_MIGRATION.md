# 🚀 EXECUTE MIGRATION TO DEPLOYMENT USER

## Quick Migration via Google Cloud Shell

1. **Open Cloud Shell**: https://shell.cloud.google.com/?project=om-models

2. **Copy and paste this complete migration script**:

```bash
#!/bin/bash

echo "🚀 Starting OMTX-Hub Job Migration"
echo "📍 Target: All jobs → omtx_deployment_user"
echo "=" * 50

# Set project
gcloud config set project om-models

# Migration variables
DEPLOYMENT_USER="omtx_deployment_user"
COLLECTION="jobs"

echo "📊 Step 1: Count current jobs by user"

# Count test_user jobs
TEST_COUNT=$(gcloud firestore documents list \
  --collection-group=$COLLECTION \
  --filter="user_id = test_user" \
  --format="value(name)" | wc -l)

# Count current_user jobs  
CURRENT_COUNT=$(gcloud firestore documents list \
  --collection-group=$COLLECTION \
  --filter="user_id = current_user" \
  --format="value(name)" | wc -l)

# Count anonymous jobs
ANON_COUNT=$(gcloud firestore documents list \
  --collection-group=$COLLECTION \
  --filter="user_id = anonymous" \
  --format="value(name)" | wc -l)

# Count deployment user jobs (current)
DEPLOY_COUNT=$(gcloud firestore documents list \
  --collection-group=$COLLECTION \
  --filter="user_id = $DEPLOYMENT_USER" \
  --format="value(name)" | wc -l)

echo "📈 Current job counts:"
echo "  test_user: $TEST_COUNT"
echo "  current_user: $CURRENT_COUNT"
echo "  anonymous: $ANON_COUNT"
echo "  omtx_deployment_user: $DEPLOY_COUNT"

TOTAL_TO_MIGRATE=$((TEST_COUNT + CURRENT_COUNT + ANON_COUNT))
echo "  TOTAL TO MIGRATE: $TOTAL_TO_MIGRATE"

echo ""
echo "🔄 Step 2: Performing migration..."

# Function to migrate user jobs
migrate_user_jobs() {
    local user=$1
    local count=$2
    
    if [ $count -gt 0 ]; then
        echo "  📦 Migrating $count jobs from $user..."
        
        # Get all job IDs for this user and migrate them
        gcloud firestore documents list \
          --collection-group=$COLLECTION \
          --filter="user_id = $user" \
          --format="value(name)" | \
        while read -r job_path; do
            # Extract job ID from path
            job_id=$(basename "$job_path")
            
            # Update the job
            gcloud firestore documents patch \
              "projects/om-models/databases/(default)/documents/$COLLECTION/$job_id" \
              --update-mask="user_id,original_user_id,migrated_at,migration_note" \
              --data="{
                \"user_id\": {\"stringValue\": \"$DEPLOYMENT_USER\"},
                \"original_user_id\": {\"stringValue\": \"$user\"},
                \"migrated_at\": {\"timestampValue\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\"},
                \"migration_note\": {\"stringValue\": \"Migrated from $user to deployment user\"}
              }" > /dev/null
            
            echo -n "."  # Progress indicator
        done
        
        echo " ✅ Completed $user migration"
    fi
}

# Migrate each user type
migrate_user_jobs "test_user" $TEST_COUNT
migrate_user_jobs "current_user" $CURRENT_COUNT  
migrate_user_jobs "anonymous" $ANON_COUNT

echo ""
echo "✅ Step 3: Verification"

# Count deployment user jobs after migration
FINAL_COUNT=$(gcloud firestore documents list \
  --collection-group=$COLLECTION \
  --filter="user_id = $DEPLOYMENT_USER" \
  --format="value(name)" | wc -l)

echo "📊 Final deployment user job count: $FINAL_COUNT"
echo "🎯 Expected total: $((DEPLOY_COUNT + TOTAL_TO_MIGRATE))"

if [ $FINAL_COUNT -eq $((DEPLOY_COUNT + TOTAL_TO_MIGRATE)) ]; then
    echo "🎉 MIGRATION SUCCESSFUL!"
    echo "✅ All $TOTAL_TO_MIGRATE jobs migrated to deployment user"
else
    echo "⚠️ Migration may be incomplete"
    echo "   Expected: $((DEPLOY_COUNT + TOTAL_TO_MIGRATE))"
    echo "   Actual: $FINAL_COUNT"
fi

echo ""
echo "🚀 Migration Complete!"
echo "🔍 You can now view all historical results in the frontend"
echo "📱 My Results and My Batches pages should show all data"
```

3. **Execute the migration**:
   - The script will show progress with dots (.)
   - It will verify the migration was successful
   - Expected result: ~2050+ jobs under deployment user

4. **Test the results**:
   - Go to your frontend: http://localhost:5173
   - Check "My Results" page - should show all individual jobs
   - Check "My Batches" page - should show all batch jobs
   - All historical GPU prediction results now accessible!

## Alternative: Manual Firestore Console

If you prefer manual approach:

1. Go to: https://console.cloud.google.com/firestore/data?project=om-models
2. Click on "jobs" collection
3. Use "Start a query" → Add filter: `user_id != omtx_deployment_user`
4. Select all results → Bulk edit → Change `user_id` to `omtx_deployment_user`

---

**Expected Result**: All 2,042 historical jobs will be consolidated under the deployment user, making all your GPU prediction results visible in the frontend My Results and My Batches pages! 🎉