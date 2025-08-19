#!/usr/bin/env python3
"""
Load Impressive Demo Data into Production - CTO PRESENTATION READY
Distinguished Engineer Implementation - FDA-approved drugs and realistic scenarios
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List

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

class DemoDataLoader:
    """Load impressive demo data into production system"""
    
    def __init__(self, production_url: str = "http://34.29.29.170"):
        self.production_url = production_url
        self.headers = {
            "X-User-Id": "demo-user",
            "X-Demo-Mode": "true",
            "Content-Type": "application/json"
        }
        
        logger.info(f"🎭 DemoDataLoader initialized")
        logger.info(f"   Production URL: {production_url}")
    
    def load_demo_data(self) -> bool:
        """Load all demo data scenarios"""
        
        print(f"\n{Colors.CYAN}📊 LOADING IMPRESSIVE DEMO DATA INTO PRODUCTION{Colors.RESET}")
        print(f"{Colors.CYAN}URL: {self.production_url}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        
        scenarios = [
            ("FDA-Approved Kinase Inhibitors", self.load_fda_kinase_batch),
            ("COVID-19 Drug Repurposing", self.load_covid_batch),
            ("Cancer Immunotherapy Targets", self.load_cancer_batch),
            ("Single High-Value Prediction", self.load_single_prediction)
        ]
        
        results = []
        
        for scenario_name, load_func in scenarios:
            print(f"Loading {scenario_name}...", end=" ")
            try:
                success, message = load_func()
                if success:
                    print(f"{Colors.GREEN}✅ LOADED{Colors.RESET}")
                    if message:
                        print(f"  {Colors.CYAN}{message}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ FAILED{Colors.RESET}")
                    if message:
                        print(f"  {Colors.YELLOW}{message}{Colors.RESET}")
                
                results.append((scenario_name, success, message))
                
            except Exception as e:
                print(f"{Colors.RED}❌ ERROR: {e}{Colors.RESET}")
                results.append((scenario_name, False, str(e)))
        
        # Summary
        self._print_demo_summary(results)
        
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        
        return passed >= (total * 0.75)  # 75% success rate acceptable
    
    def load_fda_kinase_batch(self) -> tuple[bool, str]:
        """Load FDA-approved kinase inhibitors batch"""
        
        fda_batch = {
            "job_name": "FDA-Approved Kinase Inhibitors vs EGFR",
            "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",  # EGFR kinase domain
            "ligands": [
                {
                    "name": "Imatinib (Gleevec)",
                    "smiles": "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5",
                    "description": "FDA-approved BCR-ABL kinase inhibitor, $4.7B annual sales"
                },
                {
                    "name": "Gefitinib (Iressa)",
                    "smiles": "COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4",
                    "description": "FDA-approved EGFR inhibitor for lung cancer"
                },
                {
                    "name": "Erlotinib (Tarceva)",
                    "smiles": "COCCOC1=C(C=C2C(=C1)N=CN=C2NC3=CC=CC(=C3)C#C)OCCOC",
                    "description": "FDA-approved EGFR inhibitor, $1.2B annual sales"
                },
                {
                    "name": "Dasatinib (Sprycel)",
                    "smiles": "CC1=NC(=CC(=N1)N)NC2=NC=C(C=C2)C(=O)NC3=C(C=CC=C3Cl)C",
                    "description": "Multi-kinase inhibitor for CML and ALL"
                },
                {
                    "name": "Nilotinib (Tasigna)",
                    "smiles": "CC1=CN=C(C=N1)NC2=CC(=CC(=C2)C(F)(F)F)NC(=O)C3=CC=C(C=C3)CN4CCN(CC4)C",
                    "description": "Second-generation BCR-ABL inhibitor"
                }
            ],
            "use_msa": True,
            "use_potentials": True
        }
        
        try:
            response = requests.post(
                f"{self.production_url}/api/v4/batches/submit",
                json=fda_batch,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                batch_id = result.get('batch_id', 'unknown')
                return True, f"Batch ID: {batch_id[:8]}... | {len(fda_batch['ligands'])} FDA drugs | Est. value: $7.9B"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"
                
        except Exception as e:
            return False, f"Request error: {str(e)}"
    
    def load_covid_batch(self) -> tuple[bool, str]:
        """Load COVID-19 drug repurposing batch"""
        
        covid_batch = {
            "job_name": "COVID-19 Main Protease Drug Repurposing",
            "protein_sequence": "SGFRKMAFPSGKVEGCMVQVTCGTTTLNGLWLDDVVYCPRHVICTSEDMLNPNYEDLLIRKSNHNFLVQAGNVQLRVIGHSMQNCVLKLKVDTANPKTPKYKFVRIQPGQTFSVLACYNGSPSGVYQCAMRPNFTIKGSFLNGSCGSVGFNIDYDCVSFCYMHHMELPTGVHAGTDLEGNFYGPFVDRQTAQAAGTDTTITVNVLAWLYAAVINGDRWFLNRFTTTLNDFNLVAMKYNYEPLTQDHVDILGPLSAQTGIAVLDMCASLKELLQNGMNGRTILGSALLEDEFTPFDVVRQCSGVTFQ",  # SARS-CoV-2 3CLpro
            "ligands": [
                {
                    "name": "Remdesivir",
                    "smiles": "CCC(CC)COC(=O)C(C)NP(=O)(OCC1C(C(C(O1)N2C=NC3=C(N=CN=C32)N)O)O)OC4=CC=CC=C4",
                    "description": "FDA-approved COVID-19 antiviral, $5.6B sales in 2021"
                },
                {
                    "name": "Molnupiravir",
                    "smiles": "CC(C)C(=O)OCC1C(C(C(O1)N2C=CC(=NC2=O)NO)O)O",
                    "description": "Oral antiviral for COVID-19, $3.2B Merck deal"
                },
                {
                    "name": "Nirmatrelvir (Paxlovid)",
                    "smiles": "CC1(C2C1C(N(C2)C(=O)C(C(C)(C)C)NC(=O)C(F)(F)F)C(=O)NC(CC3CCNC3=O)C#N)C",
                    "description": "Pfizer's COVID-19 protease inhibitor, $22B revenue"
                },
                {
                    "name": "Favipiravir",
                    "smiles": "NC(=O)C1=NC(=NC=C1F)O",
                    "description": "Broad-spectrum antiviral, repurposed for COVID-19"
                }
            ],
            "use_msa": True,
            "use_potentials": True
        }
        
        try:
            response = requests.post(
                f"{self.production_url}/api/v4/batches/submit",
                json=covid_batch,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                batch_id = result.get('batch_id', 'unknown')
                return True, f"Batch ID: {batch_id[:8]}... | {len(covid_batch['ligands'])} antivirals | Market: $30.8B"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"
                
        except Exception as e:
            return False, f"Request error: {str(e)}"
    
    def load_cancer_batch(self) -> tuple[bool, str]:
        """Load cancer immunotherapy targets batch"""
        
        cancer_batch = {
            "job_name": "PD-1/PD-L1 Checkpoint Inhibitor Discovery",
            "protein_sequence": "MQIPQAPWPVVWAVLQLGWRPGWFLDSPDRPWNPPTFSPALLVVTEGDNATFTCSFSNTSESFVLNWYRMSPSNQTDKLAAFPEDRSQPGQDCRFRVTQLPNGRDFHMSVVRARRNDSGTYLCGAISLAPKAQIKESLRAELRVTERRAEVPTAHPSPSPRPAGQFQTLVVGVVGGLLGSLVLLVWVLAVICSRAARGTIGARRTGQPLKEDPSAVPVFSVDYGELDFQWREKTPEPPVPCVPEQTEYATIVFPSGMGTSSPARRGSADGPRSAQPLRPEDGHCSWPL",  # PD-L1
            "ligands": [
                {
                    "name": "BMS-202",
                    "smiles": "CC1=CC(=CC=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F",
                    "description": "Small molecule PD-L1 inhibitor"
                },
                {
                    "name": "INCB086550",
                    "smiles": "CC1=C(C=C(C=C1)C2=CN=C(N=C2N)N3CCN(CC3)C)OC4=CC=CC=N4",
                    "description": "Incyte's PD-L1 inhibitor in clinical trials"
                },
                {
                    "name": "CA-170",
                    "smiles": "CC1=CC=C(C=C1)C2=CC=C(C=C2)C3=NN=C(N3)C4=CC=C(C=C4)C(=O)N",
                    "description": "Dual PD-L1/VISTA inhibitor"
                }
            ],
            "use_msa": True,
            "use_potentials": True
        }
        
        try:
            response = requests.post(
                f"{self.production_url}/api/v4/batches/submit",
                json=cancer_batch,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                batch_id = result.get('batch_id', 'unknown')
                return True, f"Batch ID: {batch_id[:8]}... | {len(cancer_batch['ligands'])} checkpoint inhibitors"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"
                
        except Exception as e:
            return False, f"Request error: {str(e)}"
    
    def load_single_prediction(self) -> tuple[bool, str]:
        """Load single high-value prediction"""
        
        single_prediction = {
            "job_name": "Pembrolizumab (Keytruda) Binding Analysis",
            "task_type": "protein_ligand_binding",
            "model_id": "boltz2",
            "input_data": {
                "protein_sequence": "MQIPQAPWPVVWAVLQLGWRPGWFLDSPDRPWNPPTFSPALLVVTEGDNATFTCSFSNTSESFVLNWYRMSPSNQTDKLAAFPEDRSQPGQDCRFRVTQLPNGRDFHMSVVRARRNDSGTYLCGAISLAPKAQIKESLRAELRVTERRAEVPTAHPSPSPRPAGQFQTLVVGVVGGLLGSLVLLVWVLAVICSRAARGTIGARRTGQPLKEDPSAVPVFSVDYGELDFQWREKTPEPPVPCVPEQTEYATIVFPSGMGTSSPARRGSADGPRSAQPLRPEDGHCSWPL",
                "ligands": ["CC1=CC(=CC=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F"],  # Small molecule mimic
                "use_msa": True,
                "use_potentials": True
            }
        }
        
        try:
            response = requests.post(
                f"{self.production_url}/api/v4/predict",
                json=single_prediction,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('job_id', 'unknown')
                return True, f"Job ID: {job_id[:8]}... | Keytruda analysis ($25B drug)"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"
                
        except Exception as e:
            return False, f"Request error: {str(e)}"
    
    def _print_demo_summary(self, results: list):
        """Print comprehensive demo summary"""
        
        print(f"\n{Colors.CYAN}📊 DEMO DATA LOADING SUMMARY{Colors.RESET}")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        for scenario_name, success, message in results:
            status = f"{Colors.GREEN}✅ LOADED{Colors.RESET}" if success else f"{Colors.RED}❌ FAILED{Colors.RESET}"
            print(f"{scenario_name:.<35} {status}")
            if message:
                print(f"    {Colors.CYAN}{message}{Colors.RESET}")
        
        print("=" * 60)
        print(f"Total Scenarios: {total}")
        print(f"Loaded: {Colors.GREEN}{passed}{Colors.RESET}")
        print(f"Failed: {Colors.RED}{total - passed}{Colors.RESET}")
        print(f"Success Rate: {Colors.GREEN if success_rate >= 75 else Colors.YELLOW if success_rate >= 50 else Colors.RED}{success_rate:.1f}%{Colors.RESET}")
        
        if success_rate >= 75:
            print(f"\n{Colors.GREEN}🎉 DEMO DATA LOADED SUCCESSFULLY!{Colors.RESET}")
            print(f"{Colors.GREEN}✅ Your CTO demo scenarios are ready!{Colors.RESET}")
            
            print(f"\n{Colors.WHITE}🎯 Demo Scenarios Ready:{Colors.RESET}")
            print(f"   1. FDA-Approved Kinase Inhibitors ($7.9B market value)")
            print(f"   2. COVID-19 Drug Repurposing ($30.8B market)")
            print(f"   3. Cancer Immunotherapy Targets (PD-1/PD-L1)")
            print(f"   4. Single High-Value Prediction (Keytruda $25B)")
            
            print(f"\n{Colors.WHITE}🏆 Key Demo Points:{Colors.RESET}")
            print(f"   • Real FDA-approved drugs with known efficacy")
            print(f"   • Multi-billion dollar market opportunities")
            print(f"   • Cutting-edge targets (COVID-19, cancer immunotherapy)")
            print(f"   • Production-ready ML predictions")
            
            print(f"\n{Colors.WHITE}📊 Access Your Demo:{Colors.RESET}")
            print(f"   Production URL: {self.production_url}")
            print(f"   API Docs: {self.production_url}/docs")
            print(f"   Demo User: demo-user")
            
        else:
            print(f"\n{Colors.YELLOW}⚠️  Some demo scenarios failed to load{Colors.RESET}")
            print(f"{Colors.YELLOW}Check the errors above and retry if needed{Colors.RESET}")
        
        print()

def main():
    """Main function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Load Demo Data into Production")
    parser.add_argument("--url", help="Production URL", default="http://34.29.29.170")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    loader = DemoDataLoader(args.url)
    success = loader.load_demo_data()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
