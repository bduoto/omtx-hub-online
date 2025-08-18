#!/usr/bin/env python3
"""
Production Load Testing Framework
Senior Principal Engineer Implementation

Comprehensive load testing suite for the unified batch processing system
with realistic workload simulation, performance benchmarking, and stress testing.
"""

import asyncio
import aiohttp
import json
import random
import time
import statistics
from typing import Dict, Any, List, Callable, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

@dataclass
class LoadTestResult:
    """Result of a load test scenario"""
    scenario_name: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    min_response_time_ms: float
    requests_per_second: float
    error_rate_percentage: float
    errors: List[str]
    timestamp: datetime

@dataclass
class StressTestConfig:
    """Configuration for stress testing"""
    base_url: str = "http://localhost:8000"
    max_concurrent_users: int = 100
    ramp_up_duration: int = 60  # seconds
    test_duration: int = 300    # seconds
    ramp_down_duration: int = 30
    think_time_range: Tuple[float, float] = (1.0, 3.0)  # seconds between requests
    
class WorkloadScenario:
    """Base class for load testing scenarios"""
    
    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight
        self.response_times: List[float] = []
        self.errors: List[str] = []
        self.success_count = 0
        self.failure_count = 0
    
    async def execute(self, session: aiohttp.ClientSession, user_context: Dict[str, Any]) -> bool:
        """Execute the scenario. Return True if successful, False if failed."""
        raise NotImplementedError
    
    def record_response(self, response_time_ms: float, success: bool, error: str = None):
        """Record response metrics"""
        self.response_times.append(response_time_ms)
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            if error:
                self.errors.append(error)

class BatchSubmissionScenario(WorkloadScenario):
    """Simulate batch job submissions"""
    
    def __init__(self):
        super().__init__("batch_submission", weight=0.1)  # Lower weight - expensive operation
        self.ligand_pool = self._generate_ligand_pool()
        
    def _generate_ligand_pool(self) -> List[Dict[str, str]]:
        """Generate a pool of realistic ligands for testing"""
        sample_ligands = [
            {"name": "Aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O"},
            {"name": "Caffeine", "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"},
            {"name": "Ibuprofen", "smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O"},
            {"name": "Acetaminophen", "smiles": "CC(=O)Nc1ccc(cc1)O"},
            {"name": "Morphine", "smiles": "CN1CC[C@]23c4c5ccc(O)c4O[C@H]2[C@@H](O)C=C[C@H]3[C@H]1C5"},
            {"name": "Penicillin", "smiles": "CC1(C)S[C@@H]2[C@H](NC(=O)Cc3ccccc3)C(=O)N2[C@H]1C(=O)O"},
            {"name": "Dopamine", "smiles": "NCCc1ccc(O)c(O)c1"},
            {"name": "Serotonin", "smiles": "NCCc1c[nH]c2ccc(O)cc12"},
        ]
        
        # Generate variations
        ligand_pool = []
        for i in range(100):
            base_ligand = random.choice(sample_ligands)
            ligand_pool.append({
                "name": f"{base_ligand['name']}_variant_{i}",
                "smiles": base_ligand["smiles"]
            })
        
        return ligand_pool
    
    async def execute(self, session: aiohttp.ClientSession, user_context: Dict[str, Any]) -> bool:
        """Submit a batch job with realistic parameters"""
        start_time = time.time()
        
        try:
            # Generate realistic batch request
            batch_size = random.randint(5, 20)  # Realistic batch sizes
            ligands = random.sample(self.ligand_pool, min(batch_size, len(self.ligand_pool)))
            
            request_data = {
                "job_name": f"load_test_batch_{random.randint(1000, 9999)}",
                "protein_sequence": "MKWVTFISLLLLFSSAYSRGVFRRDAHKSEVAHRFKDLGEENFKALVLIAFAQYLQQCPFEDHVKLVNEVTEFAKTCVADESAENCDKSLHTLFGDKLCTVATLRETYGEMADCCAKQEPERNECFLQHKDDNPNLPRLVRPEVDVMCTAFHDNEETFLKKYLYEIARRHPYFYAPELLFFAKRYKAAFTECCQAADKAACLLPKLDELRDEGKASSAKQRLKCASLQKFGERAFKAWAVARLSQRFPKAEFAEVSKLVTDLTKVHTECCHGDLLECADDRADLAKYICENQDSISSKLKECCEKPLLEKSHCIAEVENDEMPADLPSLAADFVESKDVCKNYAEAKDVFLGMFLYEYARRHPDYSVVLLLRLAKTYETTLEKCCAAADPHECYAKVFDEFKPLVEEPQNLIKQNCELFEQLGEYKFQNALLVRYTKKVPQVSTPTLVEVSRNLGKVGSKCCKHPEAKRMPCAEDYLSVVLNQLCVLHEKTPVSDRVTKCCTESLVNRRPCFSALEVDETYVPKEFNAETFTFHADICTLSEKERQIKKQTALVELVKHKPKATKEQLKAVMDDFAAFVEKCCKADDKETCFAEEGKKLVAASQAALGL",
                "protein_name": f"LoadTest_Protein_{random.randint(1, 100)}",
                "ligands": ligands,
                "model_name": "boltz2",
                "use_msa": random.choice([True, False]),
                "use_potentials": random.choice([True, False]),
                "configuration": {
                    "priority": random.choice(["normal", "high"]),
                    "scheduling_strategy": random.choice(["adaptive", "parallel", "sequential"]),
                    "max_concurrent_jobs": random.randint(3, 8),
                    "retry_failed_jobs": True
                }
            }
            
            async with session.post(
                f"{session._connector._base_url}/api/v3/batches/submit",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    user_context['last_batch_id'] = result.get('batch_id')
                    self.record_response(response_time, True)
                    return True
                else:
                    error_text = await response.text()
                    self.record_response(response_time, False, f"HTTP {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.record_response(response_time, False, str(e))
            return False

class BatchStatusScenario(WorkloadScenario):
    """Simulate batch status polling (high frequency)"""
    
    def __init__(self):
        super().__init__("batch_status_check", weight=0.6)  # High weight - frequent operation
        
    async def execute(self, session: aiohttp.ClientSession, user_context: Dict[str, Any]) -> bool:
        """Check status of a batch job"""
        start_time = time.time()
        
        # Use last submitted batch or generate a random one
        batch_id = user_context.get('last_batch_id', f"test_batch_{random.randint(1000, 9999)}")
        
        try:
            async with session.get(
                f"{session._connector._base_url}/api/v3/batches/{batch_id}/status",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status in [200, 404]:  # 404 is expected for non-existent batches
                    self.record_response(response_time, True)
                    return True
                else:
                    error_text = await response.text()
                    self.record_response(response_time, False, f"HTTP {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.record_response(response_time, False, str(e))
            return False

class BatchListScenario(WorkloadScenario):
    """Simulate batch listing (moderate frequency)"""
    
    def __init__(self):
        super().__init__("batch_list", weight=0.2)
        
    async def execute(self, session: aiohttp.ClientSession, user_context: Dict[str, Any]) -> bool:
        """List user batches"""
        start_time = time.time()
        
        try:
            params = {
                "user_id": user_context.get('user_id', 'load_test_user'),
                "limit": random.randint(10, 50),
                "offset": random.randint(0, 100)
            }
            
            async with session.get(
                f"{session._connector._base_url}/api/v3/batches/",
                params=params,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    self.record_response(response_time, True)
                    return True
                else:
                    error_text = await response.text()
                    self.record_response(response_time, False, f"HTTP {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.record_response(response_time, False, str(e))
            return False

class BatchResultsScenario(WorkloadScenario):
    """Simulate batch results retrieval"""
    
    def __init__(self):
        super().__init__("batch_results", weight=0.1)  # Lower weight - expensive operation
        
    async def execute(self, session: aiohttp.ClientSession, user_context: Dict[str, Any]) -> bool:
        """Retrieve batch results"""
        start_time = time.time()
        
        batch_id = user_context.get('last_batch_id', f"test_batch_{random.randint(1000, 9999)}")
        
        try:
            async with session.get(
                f"{session._connector._base_url}/api/v3/batches/{batch_id}/results",
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status in [200, 404]:  # 404 is expected for incomplete/non-existent batches
                    self.record_response(response_time, True)
                    return True
                else:
                    error_text = await response.text()
                    self.record_response(response_time, False, f"HTTP {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.record_response(response_time, False, str(e))
            return False

class VirtualUser:
    """Simulates a single user's behavior"""
    
    def __init__(self, user_id: str, scenarios: List[WorkloadScenario], config: StressTestConfig):
        self.user_id = user_id
        self.scenarios = scenarios
        self.config = config
        self.context = {"user_id": user_id}
        self.is_active = False
        
    async def run(self, session: aiohttp.ClientSession, duration: float):
        """Run user simulation for specified duration"""
        self.is_active = True
        start_time = time.time()
        
        while self.is_active and (time.time() - start_time) < duration:
            # Select scenario based on weights
            weights = [s.weight for s in self.scenarios]
            scenario = random.choices(self.scenarios, weights=weights)[0]
            
            # Execute scenario
            await scenario.execute(session, self.context)
            
            # Think time between requests
            think_time = random.uniform(*self.config.think_time_range)
            await asyncio.sleep(think_time)
    
    def stop(self):
        """Stop the user simulation"""
        self.is_active = False

class ProductionLoadTester:
    """
    Enterprise Load Testing Framework
    
    Features:
    - Realistic user behavior simulation
    - Gradual load ramping (ramp-up/ramp-down)
    - Multiple scenario types with weighted selection
    - Comprehensive performance metrics
    - Stress testing with configurable limits
    - Real-time monitoring and reporting
    """
    
    def __init__(self, config: StressTestConfig):
        self.config = config
        self.scenarios = [
            BatchSubmissionScenario(),
            BatchStatusScenario(),
            BatchListScenario(),
            BatchResultsScenario()
        ]
        self.virtual_users: List[VirtualUser] = []
        self.results: List[LoadTestResult] = []
        
    async def run_smoke_test(self) -> LoadTestResult:
        """Quick smoke test with minimal load"""
        logger.info("🔥 Running smoke test...")
        
        config = StressTestConfig(
            base_url=self.config.base_url,
            max_concurrent_users=5,
            test_duration=30,
            ramp_up_duration=5,
            ramp_down_duration=5
        )
        
        return await self._execute_load_test("smoke_test", config)
    
    async def run_load_test(self) -> LoadTestResult:
        """Standard load test with expected traffic"""
        logger.info("📊 Running load test...")
        return await self._execute_load_test("load_test", self.config)
    
    async def run_stress_test(self) -> LoadTestResult:
        """Stress test to find breaking points"""
        logger.info("💪 Running stress test...")
        
        stress_config = StressTestConfig(
            base_url=self.config.base_url,
            max_concurrent_users=self.config.max_concurrent_users * 2,  # Double the load
            test_duration=self.config.test_duration,
            ramp_up_duration=self.config.ramp_up_duration * 2,
            ramp_down_duration=self.config.ramp_down_duration,
            think_time_range=(0.5, 1.5)  # Faster requests
        )
        
        return await self._execute_load_test("stress_test", stress_config)
    
    async def run_spike_test(self) -> LoadTestResult:
        """Sudden traffic spike test"""
        logger.info("⚡ Running spike test...")
        
        spike_config = StressTestConfig(
            base_url=self.config.base_url,
            max_concurrent_users=self.config.max_concurrent_users * 3,  # Triple spike
            test_duration=60,  # Short duration
            ramp_up_duration=10,  # Rapid ramp-up
            ramp_down_duration=10,
            think_time_range=(0.1, 0.5)  # Very fast requests
        )
        
        return await self._execute_load_test("spike_test", spike_config)
    
    async def _execute_load_test(self, test_name: str, config: StressTestConfig) -> LoadTestResult:
        """Execute a load test with the given configuration"""
        start_time = time.time()
        logger.info(f"🚀 Starting {test_name} with {config.max_concurrent_users} max users")
        
        # Reset scenario metrics
        for scenario in self.scenarios:
            scenario.response_times.clear()
            scenario.errors.clear()
            scenario.success_count = 0
            scenario.failure_count = 0
        
        # Create HTTP session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=config.max_concurrent_users * 2,
            limit_per_host=config.max_concurrent_users,
            ttl_dns_cache=300,
            ttl_record_cache=300,
            use_dns_cache=True
        )
        connector._base_url = config.base_url
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Phase 1: Ramp-up
            await self._ramp_up_users(session, config)
            
            # Phase 2: Sustained load
            await asyncio.sleep(config.test_duration)
            
            # Phase 3: Ramp-down
            await self._ramp_down_users(config)
        
        # Calculate results
        total_time = time.time() - start_time
        result = self._calculate_results(test_name, total_time)
        self.results.append(result)
        
        logger.info(f"✅ {test_name} completed: {result.requests_per_second:.1f} RPS, {result.error_rate_percentage:.1f}% errors")
        return result
    
    async def _ramp_up_users(self, session: aiohttp.ClientSession, config: StressTestConfig):
        """Gradually add users to simulate realistic load increase"""
        ramp_interval = config.ramp_up_duration / config.max_concurrent_users
        
        for i in range(config.max_concurrent_users):
            user = VirtualUser(f"user_{i}", self.scenarios, config)
            self.virtual_users.append(user)
            
            # Start user simulation
            asyncio.create_task(user.run(session, config.test_duration + config.ramp_down_duration))
            
            # Wait before adding next user
            if i < config.max_concurrent_users - 1:
                await asyncio.sleep(ramp_interval)
        
        logger.info(f"📈 Ramped up to {len(self.virtual_users)} concurrent users")
    
    async def _ramp_down_users(self, config: StressTestConfig):
        """Gradually remove users"""
        ramp_interval = config.ramp_down_duration / len(self.virtual_users)
        
        for user in self.virtual_users:
            user.stop()
            await asyncio.sleep(ramp_interval)
        
        logger.info("📉 Ramped down all users")
        self.virtual_users.clear()
    
    def _calculate_results(self, test_name: str, duration: float) -> LoadTestResult:
        """Calculate comprehensive test results"""
        all_response_times = []
        all_errors = []
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        
        for scenario in self.scenarios:
            all_response_times.extend(scenario.response_times)
            all_errors.extend(scenario.errors)
            total_requests += len(scenario.response_times)
            successful_requests += scenario.success_count
            failed_requests += scenario.failure_count
        
        if not all_response_times:
            return LoadTestResult(
                scenario_name=test_name,
                duration_seconds=duration,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time_ms=0,
                p95_response_time_ms=0,
                p99_response_time_ms=0,
                max_response_time_ms=0,
                min_response_time_ms=0,
                requests_per_second=0,
                error_rate_percentage=0,
                errors=[],
                timestamp=datetime.utcnow()
            )
        
        # Calculate statistics
        avg_response_time = statistics.mean(all_response_times)
        p95_response_time = self._percentile(all_response_times, 95)
        p99_response_time = self._percentile(all_response_times, 99)
        max_response_time = max(all_response_times)
        min_response_time = min(all_response_times)
        requests_per_second = total_requests / duration if duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        return LoadTestResult(
            scenario_name=test_name,
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            max_response_time_ms=max_response_time,
            min_response_time_ms=min_response_time,
            requests_per_second=requests_per_second,
            error_rate_percentage=error_rate,
            errors=list(set(all_errors))[:10],  # Unique errors, limited to 10
            timestamp=datetime.utcnow()
        )
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of response time data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def generate_report(self) -> str:
        """Generate comprehensive load test report"""
        if not self.results:
            return "No load test results available."
        
        report = []
        report.append("🚀 LOAD TEST RESULTS REPORT")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append(f"Base URL: {self.config.base_url}")
        report.append("")
        
        for result in self.results:
            report.append(f"📊 {result.scenario_name.upper()}")
            report.append("-" * 30)
            report.append(f"Duration: {result.duration_seconds:.1f}s")
            report.append(f"Total Requests: {result.total_requests:,}")
            report.append(f"Successful: {result.successful_requests:,}")
            report.append(f"Failed: {result.failed_requests:,}")
            report.append(f"Requests/Second: {result.requests_per_second:.1f}")
            report.append(f"Error Rate: {result.error_rate_percentage:.1f}%")
            report.append("")
            report.append("Response Times:")
            report.append(f"  Average: {result.avg_response_time_ms:.1f}ms")
            report.append(f"  95th Percentile: {result.p95_response_time_ms:.1f}ms")
            report.append(f"  99th Percentile: {result.p99_response_time_ms:.1f}ms")
            report.append(f"  Min: {result.min_response_time_ms:.1f}ms")
            report.append(f"  Max: {result.max_response_time_ms:.1f}ms")
            report.append("")
            
            if result.errors:
                report.append("Top Errors:")
                for error in result.errors[:5]:
                    report.append(f"  • {error}")
                report.append("")
        
        # Performance assessment
        report.append("🎯 PERFORMANCE ASSESSMENT")
        report.append("-" * 30)
        
        latest_result = self.results[-1]
        
        if latest_result.error_rate_percentage < 1:
            report.append("✅ Error Rate: EXCELLENT (<1%)")
        elif latest_result.error_rate_percentage < 5:
            report.append("⚠️ Error Rate: ACCEPTABLE (<5%)")
        else:
            report.append("❌ Error Rate: CONCERNING (>5%)")
        
        if latest_result.p95_response_time_ms < 1000:
            report.append("✅ Response Time: EXCELLENT (P95 <1s)")
        elif latest_result.p95_response_time_ms < 3000:
            report.append("⚠️ Response Time: ACCEPTABLE (P95 <3s)")
        else:
            report.append("❌ Response Time: SLOW (P95 >3s)")
        
        if latest_result.requests_per_second > 50:
            report.append("✅ Throughput: HIGH (>50 RPS)")
        elif latest_result.requests_per_second > 20:
            report.append("⚠️ Throughput: MODERATE (>20 RPS)")
        else:
            report.append("❌ Throughput: LOW (<20 RPS)")
        
        return "\n".join(report)

async def main():
    """Example usage of the load testing framework"""
    logging.basicConfig(level=logging.INFO)
    
    # Configure load test
    config = StressTestConfig(
        base_url="http://localhost:8000",
        max_concurrent_users=20,
        test_duration=60,
        ramp_up_duration=20,
        ramp_down_duration=10
    )
    
    tester = ProductionLoadTester(config)
    
    # Run test suite
    await tester.run_smoke_test()
    await tester.run_load_test()
    await tester.run_stress_test()
    
    # Generate report
    print(tester.generate_report())

if __name__ == "__main__":
    asyncio.run(main())