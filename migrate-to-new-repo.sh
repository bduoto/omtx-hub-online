#!/bin/bash

# Migration script to transition from omtx-hub to omtx-hub-online
# This script helps you track the new repo and copy necessary files

echo "🚀 Starting migration from omtx-hub to omtx-hub-online..."

# Step 1: Add the new repo as a remote
echo "📌 Step 1: Adding omtx-hub-online as a new remote..."
git remote add online https://github.com/bduoto/omtx-hub-online.git
git fetch online

# Step 2: Create a new branch for migration work
echo "📌 Step 2: Creating migration branch..."
git checkout -b migration-to-online

# Step 3: Show current remotes
echo "📌 Current remotes:"
git remote -v

echo ""
echo "✅ New remote 'online' added successfully!"
echo ""
echo "Now you can:"
echo "1. Push current work to new repo:  git push online migration-to-online"
echo "2. Pull from new repo:             git pull online main"
echo "3. Set upstream to new repo:       git branch --set-upstream-to=online/main"
echo ""
echo "To copy specific files to the new repo, use the copy script next."