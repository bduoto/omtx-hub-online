#!/bin/bash

# Firestore Indexes Setup Script
# Creates all required composite indexes for optimal performance

set -e

echo "🗃️ OMTX-Hub Firestore Indexes Setup"
echo "===================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK first"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ No GCP project configured. Run setup_gcp_project.sh first"
    exit 1
fi

echo "📋 Setting up indexes for project: $PROJECT_ID"

# Create firestore.indexes.json
cat > firestore.indexes.json << 'EOF'
{
  "indexes": [
    {
      "collectionGroup": "jobs",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "user_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "DESCENDING"
        }
      ]
    },
    {
      "collectionGroup": "jobs",
      "queryScope": "COLLECTION", 
      "fields": [
        {
          "fieldPath": "user_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "status",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "DESCENDING"
        }
      ]
    },
    {
      "collectionGroup": "jobs",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "job_type",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "DESCENDING"
        }
      ]
    },
    {
      "collectionGroup": "jobs",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "batch_parent_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "ASCENDING"
        }
      ]
    },
    {
      "collectionGroup": "jobs",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "user_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "job_type",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "DESCENDING"
        }
      ]
    },
    {
      "collectionGroup": "jobs",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "model_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "task_type",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "DESCENDING"
        }
      ]
    },
    {
      "collectionGroup": "jobs",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "user_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "model_id",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "DESCENDING"
        }
      ]
    }
  ],
  "fieldOverrides": []
}
EOF

echo "✅ Created firestore.indexes.json"

# Create firebase.json if it doesn't exist
if [ ! -f firebase.json ]; then
    cat > firebase.json << EOF
{
  "firestore": {
    "rules": "firestore.rules",
    "indexes": "firestore.indexes.json"
  }
}
EOF
    echo "✅ Created firebase.json"
fi

# Create firestore.rules if it doesn't exist
if [ ! -f firestore.rules ]; then
    cat > firestore.rules << 'EOF'
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow read/write access to jobs collection
    match /jobs/{jobId} {
      allow read, write: if true;
    }
    
    // Allow read/write access to batches collection
    match /batches/{batchId} {
      allow read, write: if true;
    }
    
    // Allow read/write access to users collection
    match /users/{userId} {
      allow read, write: if true;
    }
  }
}
EOF
    echo "✅ Created firestore.rules"
fi

# Check if firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    echo "📦 Installing Firebase CLI..."
    npm install -g firebase-tools
fi

# Login to Firebase if needed
echo "🔐 Checking Firebase authentication..."
if ! firebase projects:list &> /dev/null; then
    echo "🔑 Please login to Firebase..."
    firebase login
fi

# Set the Firebase project
echo "🔧 Setting Firebase project to: $PROJECT_ID"
firebase use $PROJECT_ID || firebase use --add $PROJECT_ID

# Deploy indexes
echo "🚀 Deploying Firestore indexes..."
firebase deploy --only firestore:indexes

echo "✅ Firestore indexes deployed successfully!"

# Display index status
echo "📊 Index Status:"
echo "==============="
gcloud firestore indexes list

echo ""
echo "🎉 Firestore Setup Complete!"
echo "=============================="
echo "✅ Indexes created and deployed"
echo "✅ Security rules configured"
echo "✅ Database ready for high-performance queries"
echo ""
echo "📋 Index Creation URLs (if needed manually):"
echo "https://console.firebase.google.com/project/$PROJECT_ID/firestore/indexes"
echo ""
echo "🔗 Firestore Console:"
echo "https://console.firebase.google.com/project/$PROJECT_ID/firestore"