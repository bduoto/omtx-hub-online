# Create composite indexes for optimal query performance

# User jobs with status filter
gcloud firestore indexes composite create \
  --collection-group=jobs \
  --field-config field-path=user_id,order=ascending \
  --field-config field-path=status,order=ascending \
  --field-config field-path=created_at,order=descending

# User jobs with model filter
gcloud firestore indexes composite create \
  --collection-group=jobs \
  --field-config field-path=user_id,order=ascending \
  --field-config field-path=model_name,order=ascending \
  --field-config field-path=created_at,order=descending

# Batch children by parent ID
gcloud firestore indexes composite create \
  --collection-group=jobs \
  --field-config field-path=batch_parent_id,order=ascending \
  --field-config field-path=status,order=ascending \
  --field-config field-path=created_at,order=descending

# Check index status:
gcloud firestore indexes list
