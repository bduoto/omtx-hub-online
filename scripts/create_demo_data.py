#!/usr/bin/env python3
"""
Create Demo Data - IMPRESSIVE CTO PRESENTATION DATA
Distinguished Engineer Implementation - Realistic high-quality demo scenarios
"""

import asyncio
import json
import uuid
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

try:
    from google.cloud import firestore
    from google.cloud import storage
except ImportError:
    print("❌ Google Cloud libraries not installed")
    print("   Run: pip install google-cloud-firestore google-cloud-storage")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    RESET = '\033[0m'

class DemoDataCreator:
    """Create impressive demo data for CTO presentation"""

    def __init__(self):
        self.db = firestore.Client()
        self.storage_client = storage.Client()
        self.demo_user_id = "demo-user"
        self.enterprise_user_id = "enterprise-demo"

        # High-value drug candidates for impressive demo
        self.demo_ligands = [
            {
                "name": "Imatinib (Gleevec)",
                "smiles": "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5",
                "description": "FDA-approved BCR-ABL kinase inhibitor",
                "expected_affinity": 9.2
            },
            {
                "name": "Gefitinib (Iressa)",
                "smiles": "COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4",
                "description": "FDA-approved EGFR inhibitor",
                "expected_affinity": 8.8
            },
            {
                "name": "Erlotinib (Tarceva)",
                "smiles": "COCCOC1=C(C=C2C(=C1)N=CN=C2NC3=CC=CC(=C3)C#C)OCCOC",
                "description": "FDA-approved EGFR inhibitor",
                "expected_affinity": 8.6
            },
            {
                "name": "Dasatinib (Sprycel)",
                "smiles": "CC1=NC(=CC(=N1)N)NC2=NC=C(C=C2)C(=O)NC3=C(C=CC=C3Cl)C",
                "description": "Multi-kinase inhibitor",
                "expected_affinity": 9.0
            },
            {
                "name": "Nilotinib (Tasigna)",
                "smiles": "CC1=CN=C(C=N1)NC2=CC(=CC(=C2)C(F)(F)F)NC(=O)C3=CC=C(C=C3)CN4CCN(CC4)C",
                "description": "Second-generation BCR-ABL inhibitor",
                "expected_affinity": 8.9
            }
        ]

        logger.info(f"🎭 DemoDataCreator initialized")
        logger.info(f"   Demo User: {self.demo_user_id}")
        logger.info(f"   Enterprise User: {self.enterprise_user_id}")

    async def create_demo_data(self) -> Dict[str, Any]:
        """Create complete demo data set"""

        print(f"\n{Colors.CYAN}🎭 CREATING IMPRESSIVE DEMO DATA{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*50}{Colors.RESET}\n")

        demo_data = {}

        # Step 1: Create demo users
        print("1️⃣ Creating demo users...")
        demo_data['users'] = await self._create_demo_users()

        # Step 2: Create successful batch
        print("2️⃣ Creating successful batch...")
        demo_data['successful_batch'] = await self._create_successful_batch()

        # Step 3: Create in-progress batch
        print("3️⃣ Creating in-progress batch...")
        demo_data['progress_batch'] = await self._create_progress_batch()

        # Step 4: Create historical data
        print("4️⃣ Creating historical data...")
        demo_data['historical_batches'] = await self._create_historical_data()

        # Step 5: Create usage analytics
        print("5️⃣ Creating usage analytics...")
        demo_data['analytics'] = await self._create_usage_analytics()

        # Step 6: Save demo data
        print("6️⃣ Saving demo data...")
        await self._save_demo_data(demo_data)

        # Summary
        self._print_demo_summary(demo_data)

        return demo_data

    async def _create_demo_users(self) -> List[Dict[str, Any]]:
        """Create demo user accounts"""

        users = [
            {
                "user_id": self.demo_user_id,
                "email": "demo@omtx-hub.com",
                "display_name": "Demo User",
                "organization": "OMTX Demo Organization",
                "tier": "enterprise",
                "created_at": firestore.SERVER_TIMESTAMP,
                "demo_account": True,
                "quotas": {
                    "monthly_jobs": 10000,
                    "concurrent_jobs": 50,
                    "storage_gb": 1000,
                    "gpu_minutes_monthly": 50000
                },
                "usage_current_month": {
                    "jobs_submitted": 247,
                    "jobs_completed": 241,
                    "gpu_minutes_used": 1847,
                    "storage_used_gb": 23.4
                }
            },
            {
                "user_id": self.enterprise_user_id,
                "email": "enterprise@pharma-corp.com",
                "display_name": "Dr. Sarah Chen",
                "organization": "PharmaCorp Research",
                "tier": "enterprise",
                "created_at": firestore.SERVER_TIMESTAMP,
                "demo_account": True,
                "quotas": {
                    "monthly_jobs": 50000,
                    "concurrent_jobs": 100,
                    "storage_gb": 5000,
                    "gpu_minutes_monthly": 100000
                },
                "usage_current_month": {
                    "jobs_submitted": 1247,
                    "jobs_completed": 1198,
                    "gpu_minutes_used": 8934,
                    "storage_used_gb": 156.7
                }
            }
        ]

        # Save users to Firestore
        for user in users:
            user_ref = self.db.collection('users').document(user['user_id'])
            user_ref.set(user)

            print(f"   ✅ Created user: {user['display_name']} ({user['tier']} tier)")

        return users

    async def _create_successful_batch(self) -> Dict[str, Any]:
        """Create a completed batch with impressive results"""

        batch_id = str(uuid.uuid4())

        batch_data = {
            "batch_id": batch_id,
            "user_id": self.demo_user_id,
            "job_name": "Kinase Inhibitor Lead Optimization",
            "status": "completed",
            "created_at": firestore.SERVER_TIMESTAMP,
            "completed_at": firestore.SERVER_TIMESTAMP,
            "protein_target": "EGFR Kinase Domain (PDB: 1M17)",
            "protein_sequence": "MKKFFDSAFIHVPELTVEELVKLENQSLNTIISEAG...",  # Truncated for demo
            "total_ligands": len(self.demo_ligands),
            "completed_ligands": len(self.demo_ligands),
            "failed_ligands": 0,
            "processing_time_minutes": 18,
            "gpu_type": "L4",
            "cost_usd": 3.47,
            "results_summary": {
                "high_affinity_count": 5,
                "medium_affinity_count": 0,
                "low_affinity_count": 0,
                "average_affinity": 8.9,
                "best_affinity": 9.2,
                "confidence_score": 0.94
            }
        }

        # Save batch to Firestore
        batch_ref = self.db.collection('users').document(self.demo_user_id)\
            .collection('batches').document(batch_id)
        batch_ref.set(batch_data)

        # Create individual job results
        for i, ligand in enumerate(self.demo_ligands):
            job_id = str(uuid.uuid4())

            # Generate realistic results with some variation
            base_affinity = ligand["expected_affinity"]
            actual_affinity = base_affinity + random.uniform(-0.3, 0.3)

            job_data = {
                "job_id": job_id,
                "batch_id": batch_id,
                "user_id": self.demo_user_id,
                "ligand_index": i,
                "ligand_name": ligand["name"],
                "ligand_smiles": ligand["smiles"],
                "ligand_description": ligand["description"],
                "status": "completed",
                "created_at": firestore.SERVER_TIMESTAMP,
                "completed_at": firestore.SERVER_TIMESTAMP,
                "processing_time_seconds": random.randint(180, 240),
                "results": {
                    "binding_affinity": round(actual_affinity, 2),
                    "confidence_score": round(0.88 + random.uniform(0, 0.08), 3),
                    "ptm_score": round(0.85 + random.uniform(0, 0.10), 3),
                    "iptm_score": round(0.82 + random.uniform(0, 0.12), 3),
                    "interaction_energy": round(-35.0 - random.uniform(0, 20), 2),
                    "rmsd": round(random.uniform(0.8, 2.1), 2),
                    "has_structure": True,
                    "structure_quality": "high"
                },
                "ranking": i + 1
            }

            job_ref = self.db.collection('users').document(self.demo_user_id)\
                .collection('jobs').document(job_id)
            job_ref.set(job_data)

        print(f"   ✅ Created successful batch: {batch_data['job_name']}")
        print(f"      - {len(self.demo_ligands)} FDA-approved drugs")
        print(f"      - Average affinity: {batch_data['results_summary']['average_affinity']} kcal/mol")
        print(f"      - Processing time: {batch_data['processing_time_minutes']} minutes")
        print(f"      - Cost: ${batch_data['cost_usd']}")

        return batch_data

    async def _create_progress_batch(self) -> Dict[str, Any]:
        """Create an in-progress batch for live demo"""

        batch_id = str(uuid.uuid4())

        total_ligands = 25
        completed_ligands = 16

        batch_data = {
            "batch_id": batch_id,
            "user_id": self.demo_user_id,
            "job_name": "COVID-19 Protease Inhibitor Screening",
            "status": "running",
            "created_at": firestore.SERVER_TIMESTAMP,
            "started_at": firestore.SERVER_TIMESTAMP,
            "protein_target": "SARS-CoV-2 Main Protease (Mpro)",
            "protein_sequence": "SGFRKMAFPSGKVEGCMVQVTCGTTTLNGLWLDDVVYCPRHVICTSEDMLNPNYEDLLIRKSNHNFLVQAGNVQLRVIGHSMQNCVLKLKVDTANPKTPKYKFVRIQPGQTFSVLACYNGSPSGVYQCAMRPNFTIKGSFLNGSCGSVGFNIDYDCVSFCYMHHMELPTGVHAGTDLEGNFYGPFVDRQTAQAAGTDTTITVNVLAWLYAAVINGDRWFLNRFTTTLNDFNLVAMKYNYEPLTQDHVDILGPLSAQTGIAVLDMCASLKELLQNGMNGRTILGSALLEDEFTPFDVVRQCSGVTFQ",
            "total_ligands": total_ligands,
            "completed_ligands": completed_ligands,
            "failed_ligands": 1,
            "running_ligands": 3,
            "pending_ligands": total_ligands - completed_ligands - 1 - 3,
            "progress_percent": round((completed_ligands / total_ligands) * 100, 1),
            "estimated_completion_minutes": 8,
            "gpu_type": "L4",
            "estimated_cost_usd": 2.15
        }

        # Save batch to Firestore
        batch_ref = self.db.collection('users').document(self.demo_user_id)\
            .collection('batches').document(batch_id)
        batch_ref.set(batch_data)

        # Create some completed jobs and some running jobs
        for i in range(total_ligands):
            job_id = str(uuid.uuid4())

            if i < completed_ligands:
                status = "completed"
                results = {
                    "binding_affinity": round(6.5 + random.uniform(0, 3.0), 2),
                    "confidence_score": round(0.75 + random.uniform(0, 0.15), 3),
                    "ptm_score": round(0.80 + random.uniform(0, 0.15), 3),
                    "has_structure": True
                }
            elif i < completed_ligands + 3:
                status = "running"
                results = {}
            elif i < completed_ligands + 4:
                status = "failed"
                results = {"error": "Convergence failed after 300 iterations"}
            else:
                status = "pending"
                results = {}

            job_data = {
                "job_id": job_id,
                "batch_id": batch_id,
                "user_id": self.demo_user_id,
                "ligand_index": i,
                "ligand_name": f"Compound_{i+1:03d}",
                "ligand_smiles": f"CC(C)CC{i}=CC=C(C=C{i})C(C)C",  # Simplified for demo
                "status": status,
                "created_at": firestore.SERVER_TIMESTAMP,
                "results": results
            }

            job_ref = self.db.collection('users').document(self.demo_user_id)\
                .collection('jobs').document(job_id)
            job_ref.set(job_data)

        print(f"   ✅ Created in-progress batch: {batch_data['job_name']}")
        print(f"      - {completed_ligands}/{total_ligands} completed ({batch_data['progress_percent']}%)")
        print(f"      - ETA: {batch_data['estimated_completion_minutes']} minutes")

        return batch_data

    async def _create_historical_data(self) -> List[Dict[str, Any]]:
        """Create historical batch data for analytics"""

        historical_batches = []

        # Create 10 historical batches over the past month
        for i in range(10):
            batch_id = str(uuid.uuid4())
            days_ago = random.randint(1, 30)

            batch_data = {
                "batch_id": batch_id,
                "user_id": self.demo_user_id,
                "job_name": f"Historical Batch {i+1}",
                "status": "completed",
                "created_at": datetime.now() - timedelta(days=days_ago),
                "completed_at": datetime.now() - timedelta(days=days_ago, hours=-2),
                "total_ligands": random.randint(5, 50),
                "completed_ligands": random.randint(4, 48),
                "processing_time_minutes": random.randint(10, 120),
                "cost_usd": round(random.uniform(1.50, 15.00), 2),
                "gpu_type": "L4"
            }

            historical_batches.append(batch_data)

        print(f"   ✅ Created {len(historical_batches)} historical batches")

        return historical_batches

    async def _create_usage_analytics(self) -> Dict[str, Any]:
        """Create usage analytics data"""

        analytics = {
            "monthly_summary": {
                "jobs_submitted": 247,
                "jobs_completed": 241,
                "success_rate": 97.6,
                "total_cost_usd": 89.34,
                "gpu_hours_used": 137.4,
                "average_job_time_minutes": 3.2,
                "cost_savings_vs_a100": 84.2
            },
            "weekly_trends": [
                {"week": "Week 1", "jobs": 52, "cost": 18.45},
                {"week": "Week 2", "jobs": 67, "cost": 23.12},
                {"week": "Week 3", "jobs": 71, "cost": 24.89},
                {"week": "Week 4", "jobs": 57, "cost": 22.88}
            ],
            "top_targets": [
                {"target": "EGFR Kinase", "jobs": 89, "success_rate": 98.9},
                {"target": "COVID-19 Mpro", "jobs": 67, "success_rate": 95.5},
                {"target": "p53-MDM2", "jobs": 45, "success_rate": 97.8},
                {"target": "BCR-ABL", "jobs": 34, "success_rate": 100.0}
            ]
        }

        print(f"   ✅ Created usage analytics")
        print(f"      - 97.6% success rate")
        print(f"      - 84.2% cost savings vs A100")
        print(f"      - $89.34 total monthly cost")

        return analytics

    async def _save_demo_data(self, demo_data: Dict[str, Any]):
        """Save demo data to file"""

        # Add metadata
        demo_data['metadata'] = {
            'created_at': datetime.now().isoformat(),
            'version': '1.0',
            'description': 'OMTX-Hub Demo Data for CTO Presentation',
            'total_users': len(demo_data['users']),
            'total_batches': 2 + len(demo_data['historical_batches'])
        }

        # Save to JSON file
        with open('demo_data.json', 'w') as f:
            json.dump(demo_data, f, indent=2, default=str)

        print(f"   ✅ Demo data saved to demo_data.json")

    def _print_demo_summary(self, demo_data: Dict[str, Any]):
        """Print comprehensive demo summary"""

        print(f"\n{Colors.CYAN}📊 DEMO DATA SUMMARY{Colors.RESET}")
        print("=" * 60)

        print(f"\n{Colors.WHITE}👥 DEMO USERS:{Colors.RESET}")
        for user in demo_data['users']:
            print(f"   • {user['display_name']} ({user['email']})")
            print(f"     Tier: {user['tier']} | Jobs: {user['usage_current_month']['jobs_completed']}")

        print(f"\n{Colors.WHITE}🧪 DEMO SCENARIOS:{Colors.RESET}")

        successful = demo_data['successful_batch']
        print(f"   1. ✅ Completed Batch: '{successful['job_name']}'")
        print(f"      • {successful['total_ligands']} FDA-approved drugs")
        print(f"      • Average affinity: {successful['results_summary']['average_affinity']} kcal/mol")
        print(f"      • 94% confidence score")
        print(f"      • Cost: ${successful['cost_usd']} (84% savings vs A100)")

        progress = demo_data['progress_batch']
        print(f"\n   2. ⏳ In-Progress Batch: '{progress['job_name']}'")
        print(f"      • {progress['completed_ligands']}/{progress['total_ligands']} completed ({progress['progress_percent']}%)")
        print(f"      • ETA: {progress['estimated_completion_minutes']} minutes")
        print(f"      • Real-time progress updates")

        print(f"\n   3. 📈 Historical Data:")
        print(f"      • {len(demo_data['historical_batches'])} completed batches")
        print(f"      • 97.6% success rate")
        print(f"      • $89.34 monthly spend")

        print(f"\n{Colors.WHITE}🎯 DEMO HIGHLIGHTS:{Colors.RESET}")
        print(f"   • Enterprise-grade multi-tenant architecture")
        print(f"   • Real-time progress tracking with Firestore")
        print(f"   • 84% cost reduction with L4 GPU optimization")
        print(f"   • FDA-approved drug candidates with high binding affinity")
        print(f"   • Complete user isolation and quota management")
        print(f"   • Production-ready monitoring and analytics")

        print(f"\n{Colors.GREEN}✅ DEMO DATA READY FOR CTO PRESENTATION!{Colors.RESET}")
        print("=" * 60)

async def main():
    """Main function"""

    import argparse

    parser = argparse.ArgumentParser(description="Create Demo Data for CTO Presentation")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        creator = DemoDataCreator()
        demo_data = await creator.create_demo_data()

        print(f"\n{Colors.CYAN}🎭 DEMO ENVIRONMENT READY!{Colors.RESET}")
        print(f"\n{Colors.WHITE}Demo Credentials:{Colors.RESET}")
        print(f"   Email: demo@omtx-hub.com")
        print(f"   User ID: demo-user")
        print(f"   Tier: Enterprise")

        print(f"\n{Colors.WHITE}What to Show:{Colors.RESET}")
        print(f"   1. Login as demo user")
        print(f"   2. View completed 'Kinase Inhibitor' batch")
        print(f"   3. Submit new batch with 3-5 ligands")
        print(f"   4. Show real-time progress updates")
        print(f"   5. Download results as ZIP")
        print(f"   6. Show cost savings dashboard")

        return 0

    except Exception as e:
        print(f"{Colors.RED}❌ Failed to create demo data: {e}{Colors.RESET}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)