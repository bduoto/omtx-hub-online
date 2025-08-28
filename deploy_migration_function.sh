#!/bin/bash

echo "🚀 Deploying Job Migration Cloud Function..."

cd backend/cloud_functions

# Deploy the migration function
gcloud functions deploy migrate-jobs-to-deployment-user \
  --runtime python310 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point migrate_jobs_to_deployment_user \
  --source . \
  --project om-models \
  --region us-central1 \
  --memory 512MB \
  --timeout 540s

if [ $? -eq 0 ]; then
    echo "✅ Migration function deployed successfully!"
    echo ""
    echo "📝 To run the migration, execute this curl command:"
    echo ""
    echo "curl https://us-central1-om-models.cloudfunctions.net/migrate-jobs-to-deployment-user"
    echo ""
    echo "📊 To verify the migration, run:"
    echo ""
    echo "curl https://us-central1-om-models.cloudfunctions.net/migrate-jobs-to-deployment-user"
else
    echo "❌ Deployment failed"
fi