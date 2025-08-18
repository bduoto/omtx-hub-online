#!/bin/bash

# After creating the repo on GitHub, run this script to connect and push

echo "Setting up remote repository connection..."

# Using your GitHub username
GITHUB_USERNAME="bduoto"

git remote add origin https://github.com/$GITHUB_USERNAME/omtx-hub-online.git
git branch -M main
git push -u origin main

echo "Repository pushed to GitHub successfully!"