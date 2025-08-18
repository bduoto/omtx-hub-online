# Apply Storage and Performance Fixes

## Quick Fix Instructions

1. **Open Supabase Dashboard**
   - Go to your Supabase project dashboard
   - Navigate to the SQL Editor

2. **Run the Migration**
   - Copy the entire contents of `fix_storage_and_performance.sql`
   - Paste into the SQL editor
   - Click "Run" to execute

3. **Verify the Fixes**
   - Check that no errors occurred
   - Try uploading a file to test storage policies
   - Run a batch prediction to test performance

## Alternative: Manual Fixes

If you prefer to apply fixes step by step:

### Fix Storage Policies (URGENT)
In Supabase Dashboard > Storage > Policies:

1. Select the `omtx-myresults` bucket
2. Delete all existing policies
3. Add new policy:
   - Name: "Allow all operations"
   - Allowed operations: SELECT, INSERT, UPDATE, DELETE
   - Target roles: anon, authenticated
   - WITH CHECK expression: `true`
   - USING expression: `true`

### Fix Database Performance (URGENT)
In SQL Editor, run:

```sql
-- Critical indexes to prevent timeouts
CREATE INDEX IF NOT EXISTS idx_my_results_user_created 
ON my_results(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_status_updated 
ON jobs(status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_input_data_batch
ON jobs((input_data->>'parent_batch_id'))
WHERE input_data->>'parent_batch_id' IS NOT NULL;
```

## Testing the Fixes

After applying, test with:
1. Run a single protein-ligand prediction
2. Check if it saves to My Results
3. Run a batch prediction
4. Check if all individual jobs are created and tracked