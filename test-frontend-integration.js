// Test Frontend-Backend Integration
// Run this in the browser console at http://localhost:5173

async function testBackendIntegration() {
  const API_BASE = 'https://omtx-hub-backend-zhye5az7za-uc.a.run.app';
  
  console.log('🔍 Testing Backend Integration...\n');
  
  // 1. Test Health Endpoint
  console.log('1️⃣ Testing Health Endpoint...');
  try {
    const healthRes = await fetch(`${API_BASE}/health`);
    const health = await healthRes.json();
    console.log('✅ Health Check:', health);
  } catch (error) {
    console.error('❌ Health Check Failed:', error);
  }
  
  // 2. Submit Individual Job
  console.log('\n2️⃣ Submitting Individual Job...');
  try {
    const jobRes = await fetch(`${API_BASE}/api/v1/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'boltz2',
        protein_sequence: 'MVLSPADKTNVKAAW',
        ligand_smiles: 'CC(=O)OC1=CC=CC=C1C(=O)O',
        job_name: 'Frontend Test Job',
        user_id: 'frontend_test'
      })
    });
    const job = await jobRes.json();
    console.log('✅ Job Submitted:', job);
    
    // 3. Check Job Status
    if (job.job_id) {
      console.log('\n3️⃣ Checking Job Status...');
      setTimeout(async () => {
        const statusRes = await fetch(`${API_BASE}/api/v1/jobs/${job.job_id}`);
        const status = await statusRes.json();
        console.log('✅ Job Status:', status);
      }, 5000);
    }
  } catch (error) {
    console.error('❌ Job Submission Failed:', error);
  }
  
  // 4. List Recent Jobs
  console.log('\n4️⃣ Listing Recent Jobs...');
  try {
    const listRes = await fetch(`${API_BASE}/api/v1/jobs?limit=5`);
    const jobs = await listRes.json();
    console.log('✅ Recent Jobs:', jobs);
  } catch (error) {
    console.error('❌ List Jobs Failed:', error);
  }
}

// Run the test
testBackendIntegration();