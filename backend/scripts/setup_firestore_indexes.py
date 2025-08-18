#!/usr/bin/env python3
"""
Firestore Composite Index Setup for Performance Optimization
Creates the required indexes for ultra-fast query performance
"""

import json
import os
from typing import List, Dict, Any

def generate_firestore_indexes() -> Dict[str, Any]:
    """Generate Firestore index configuration for optimal performance"""
    
    indexes = {
        "indexes": [
            # User jobs with status filter (most common query)
            {
                "collectionGroup": "jobs",
                "queryScope": "COLLECTION",
                "fields": [
                    {"fieldPath": "user_id", "order": "ASCENDING"},
                    {"fieldPath": "status", "order": "ASCENDING"},
                    {"fieldPath": "created_at", "order": "DESCENDING"}
                ]
            },
            
            # User jobs with model filter
            {
                "collectionGroup": "jobs",
                "queryScope": "COLLECTION", 
                "fields": [
                    {"fieldPath": "user_id", "order": "ASCENDING"},
                    {"fieldPath": "model_name", "order": "ASCENDING"},
                    {"fieldPath": "created_at", "order": "DESCENDING"}
                ]
            },
            
            # User jobs with task type filter
            {
                "collectionGroup": "jobs",
                "queryScope": "COLLECTION",
                "fields": [
                    {"fieldPath": "user_id", "order": "ASCENDING"},
                    {"fieldPath": "task_type", "order": "ASCENDING"},
                    {"fieldPath": "created_at", "order": "DESCENDING"}
                ]
            },
            
            # Batch parent jobs
            {
                "collectionGroup": "jobs",
                "queryScope": "COLLECTION",
                "fields": [
                    {"fieldPath": "user_id", "order": "ASCENDING"},
                    {"fieldPath": "job_type", "order": "ASCENDING"},
                    {"fieldPath": "created_at", "order": "DESCENDING"}
                ]
            },
            
            # Batch children by parent ID
            {
                "collectionGroup": "jobs",
                "queryScope": "COLLECTION",
                "fields": [
                    {"fieldPath": "batch_parent_id", "order": "ASCENDING"},
                    {"fieldPath": "status", "order": "ASCENDING"},
                    {"fieldPath": "created_at", "order": "DESCENDING"}
                ]
            },
            
            # Status-based queries for monitoring
            {
                "collectionGroup": "jobs",
                "queryScope": "COLLECTION",
                "fields": [
                    {"fieldPath": "status", "order": "ASCENDING"},
                    {"fieldPath": "updated_at", "order": "DESCENDING"}
                ]
            },
            
            # Complex batch queries with multiple filters
            {
                "collectionGroup": "jobs",
                "queryScope": "COLLECTION",
                "fields": [
                    {"fieldPath": "user_id", "order": "ASCENDING"},
                    {"fieldPath": "job_type", "order": "ASCENDING"},
                    {"fieldPath": "status", "order": "ASCENDING"},
                    {"fieldPath": "created_at", "order": "DESCENDING"}
                ]
            }
        ],
        
        "fieldOverrides": [
            # Enable single-field indexes for commonly filtered fields
            {
                "collectionGroup": "jobs",
                "fieldPath": "user_id",
                "indexes": [
                    {"order": "ASCENDING", "queryScope": "COLLECTION"},
                    {"order": "DESCENDING", "queryScope": "COLLECTION"}
                ]
            },
            {
                "collectionGroup": "jobs", 
                "fieldPath": "created_at",
                "indexes": [
                    {"order": "ASCENDING", "queryScope": "COLLECTION"},
                    {"order": "DESCENDING", "queryScope": "COLLECTION"}
                ]
            },
            {
                "collectionGroup": "jobs",
                "fieldPath": "status",
                "indexes": [
                    {"order": "ASCENDING", "queryScope": "COLLECTION"}
                ]
            }
        ]
    }
    
    return indexes

def save_firestore_indexes():
    """Save Firestore indexes to firestore.indexes.json"""
    
    indexes = generate_firestore_indexes()
    
    # Save to firestore.indexes.json (Firebase CLI format)
    with open('firestore.indexes.json', 'w') as f:
        json.dump(indexes, f, indent=2)
    
    print("✅ Generated firestore.indexes.json")
    print("📋 To deploy indexes, run:")
    print("   firebase deploy --only firestore:indexes")
    print()
    print("🔍 Index Summary:")
    print(f"   - Composite indexes: {len(indexes['indexes'])}")
    print(f"   - Field overrides: {len(indexes['fieldOverrides'])}")
    print()
    print("⚡ These indexes will optimize:")
    print("   - User job queries (by status, model, task type)")
    print("   - Batch parent/child relationships")
    print("   - Status-based monitoring queries")
    print("   - Complex filtered queries")

def generate_gcloud_commands():
    """Generate gcloud commands for index creation"""
    
    commands = [
        "# Create composite indexes for optimal query performance",
        "",
        "# User jobs with status filter",
        "gcloud firestore indexes composite create \\",
        "  --collection-group=jobs \\",
        "  --field-config field-path=user_id,order=ascending \\",
        "  --field-config field-path=status,order=ascending \\",
        "  --field-config field-path=created_at,order=descending",
        "",
        "# User jobs with model filter", 
        "gcloud firestore indexes composite create \\",
        "  --collection-group=jobs \\",
        "  --field-config field-path=user_id,order=ascending \\",
        "  --field-config field-path=model_name,order=ascending \\",
        "  --field-config field-path=created_at,order=descending",
        "",
        "# Batch children by parent ID",
        "gcloud firestore indexes composite create \\",
        "  --collection-group=jobs \\",
        "  --field-config field-path=batch_parent_id,order=ascending \\",
        "  --field-config field-path=status,order=ascending \\",
        "  --field-config field-path=created_at,order=descending",
        "",
        "# Check index status:",
        "gcloud firestore indexes list",
        ""
    ]
    
    with open('setup_firestore_indexes.sh', 'w') as f:
        f.write('\n'.join(commands))
    
    os.chmod('setup_firestore_indexes.sh', 0o755)
    print("✅ Generated setup_firestore_indexes.sh")
    print("📋 Run: ./setup_firestore_indexes.sh")

if __name__ == "__main__":
    print("🔍 Setting up Firestore indexes for performance optimization...")
    print("=" * 60)
    
    save_firestore_indexes()
    generate_gcloud_commands()
    
    print()
    print("🎯 Next Steps:")
    print("1. Authenticate with GCP: gcloud auth application-default login")
    print("2. Set project: gcloud config set project YOUR_PROJECT_ID")
    print("3. Deploy indexes: firebase deploy --only firestore:indexes")
    print("4. Monitor index build: gcloud firestore indexes list")
    print()
    print("⚡ Expected performance improvement: 10-100x faster queries")
