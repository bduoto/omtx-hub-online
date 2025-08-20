#!/usr/bin/env python3
"""
Live API Monitoring for CTO Demo - REAL-TIME DASHBOARD
Distinguished Engineer Implementation - Live system monitoring during demo
"""

import requests
import json
import time
import threading
from datetime import datetime
from typing import Dict, Any

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    RESET = '\033[0m'

class DemoAPIMonitor:
    """Real-time API monitoring for CTO demo"""
    
    def __init__(self, api_url: str = "http://34.29.29.170"):
        self.api_url = api_url
        self.monitoring = False
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'last_health_check': None,
            'uptime_percentage': 100.0
        }
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        
        print(f"\n{Colors.CYAN}🔍 STARTING LIVE API MONITORING{Colors.RESET}")
        print(f"{Colors.CYAN}API URL: {self.api_url}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        
        self.monitoring = True
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Start display thread
        display_thread = threading.Thread(target=self._display_loop)
        display_thread.daemon = True
        display_thread.start()
        
        try:
            while self.monitoring:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}🛑 Stopping monitoring...{Colors.RESET}")
            self.monitoring = False
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        
        response_times = []
        
        while self.monitoring:
            try:
                # Health check
                start_time = time.time()
                response = requests.get(f"{self.api_url}/health", timeout=5)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # Convert to ms
                response_times.append(response_time)
                
                self.stats['total_requests'] += 1
                
                if response.status_code == 200:
                    self.stats['successful_requests'] += 1
                    self.stats['last_health_check'] = datetime.now()
                else:
                    self.stats['failed_requests'] += 1
                
                # Calculate average response time
                if response_times:
                    self.stats['avg_response_time'] = sum(response_times[-10:]) / len(response_times[-10:])
                
                # Calculate uptime percentage
                if self.stats['total_requests'] > 0:
                    self.stats['uptime_percentage'] = (self.stats['successful_requests'] / self.stats['total_requests']) * 100
                
            except Exception as e:
                self.stats['total_requests'] += 1
                self.stats['failed_requests'] += 1
            
            time.sleep(5)  # Check every 5 seconds
    
    def _display_loop(self):
        """Display monitoring dashboard"""
        
        while self.monitoring:
            # Clear screen
            print("\033[2J\033[H", end="")
            
            # Header
            print(f"{Colors.CYAN}🔍 LIVE API MONITORING DASHBOARD{Colors.RESET}")
            print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
            print(f"API URL: {Colors.WHITE}{self.api_url}{Colors.RESET}")
            print(f"Time: {Colors.WHITE}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
            print()
            
            # Health Status
            if self.stats['last_health_check']:
                health_color = Colors.GREEN
                health_status = "✅ HEALTHY"
                last_check = self.stats['last_health_check'].strftime('%H:%M:%S')
            else:
                health_color = Colors.RED
                health_status = "❌ UNHEALTHY"
                last_check = "Never"
            
            print(f"{Colors.WHITE}🏥 HEALTH STATUS{Colors.RESET}")
            print(f"Status: {health_color}{health_status}{Colors.RESET}")
            print(f"Last Check: {Colors.CYAN}{last_check}{Colors.RESET}")
            print()
            
            # Performance Metrics
            print(f"{Colors.WHITE}⚡ PERFORMANCE METRICS{Colors.RESET}")
            print(f"Total Requests: {Colors.CYAN}{self.stats['total_requests']}{Colors.RESET}")
            print(f"Successful: {Colors.GREEN}{self.stats['successful_requests']}{Colors.RESET}")
            print(f"Failed: {Colors.RED}{self.stats['failed_requests']}{Colors.RESET}")
            print(f"Uptime: {Colors.GREEN}{self.stats['uptime_percentage']:.1f}%{Colors.RESET}")
            print(f"Avg Response Time: {Colors.CYAN}{self.stats['avg_response_time']:.0f}ms{Colors.RESET}")
            print()
            
            # API Endpoints Status
            print(f"{Colors.WHITE}🔗 API ENDPOINTS{Colors.RESET}")
            endpoints = [
                ("/health", "Health Check"),
                ("/docs", "API Documentation"),
                ("/metrics", "Metrics"),
                ("/ready", "Readiness Probe"),
                ("/startup", "Startup Probe")
            ]
            
            for endpoint, description in endpoints:
                try:
                    response = requests.get(f"{self.api_url}{endpoint}", timeout=2)
                    if response.status_code == 200:
                        status = f"{Colors.GREEN}✅ OK{Colors.RESET}"
                    else:
                        status = f"{Colors.YELLOW}⚠️  {response.status_code}{Colors.RESET}"
                except:
                    status = f"{Colors.RED}❌ DOWN{Colors.RESET}"
                
                print(f"{description:.<25} {status}")
            
            print()
            
            # Demo Instructions
            print(f"{Colors.WHITE}🎯 DEMO COMMANDS{Colors.RESET}")
            print(f"Open API Docs: {Colors.CYAN}curl {self.api_url}/docs{Colors.RESET}")
            print(f"Submit Test Job: {Colors.CYAN}curl -X POST {self.api_url}/api/v4/predict{Colors.RESET}")
            print(f"Check Metrics: {Colors.CYAN}curl {self.api_url}/metrics{Colors.RESET}")
            print()
            print(f"{Colors.YELLOW}Press Ctrl+C to stop monitoring{Colors.RESET}")
            
            time.sleep(2)  # Update every 2 seconds
    
    def test_api_endpoints(self):
        """Test all API endpoints once"""
        
        print(f"\n{Colors.CYAN}🧪 TESTING ALL API ENDPOINTS{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        
        endpoints = [
            ("/health", "Health Check"),
            ("/docs", "API Documentation"),
            ("/metrics", "Metrics Endpoint"),
            ("/ready", "Readiness Probe"),
            ("/startup", "Startup Probe"),
            ("/api/v4/batches", "Batch API"),
            ("/api/v4/predict", "Prediction API (GET)"),
        ]
        
        for endpoint, description in endpoints:
            print(f"Testing {description}...", end=" ")
            
            try:
                response = requests.get(f"{self.api_url}{endpoint}", timeout=5)
                
                if response.status_code == 200:
                    print(f"{Colors.GREEN}✅ OK ({response.status_code}){Colors.RESET}")
                elif response.status_code in [404, 405]:  # Method not allowed is OK for some endpoints
                    print(f"{Colors.YELLOW}⚠️  {response.status_code} (Expected){Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ {response.status_code}{Colors.RESET}")
                    
            except requests.exceptions.Timeout:
                print(f"{Colors.RED}❌ TIMEOUT{Colors.RESET}")
            except requests.exceptions.ConnectionError:
                print(f"{Colors.RED}❌ CONNECTION ERROR{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.RED}❌ ERROR: {str(e)[:30]}{Colors.RESET}")
        
        print(f"\n{Colors.GREEN}✅ API endpoint testing complete!{Colors.RESET}")

def main():
    """Main function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Live API Monitoring for Demo")
    parser.add_argument("--url", default="http://34.29.29.170", help="API URL to monitor")
    parser.add_argument("--test-only", action="store_true", help="Test endpoints once and exit")
    
    args = parser.parse_args()
    
    monitor = DemoAPIMonitor(args.url)
    
    if args.test_only:
        monitor.test_api_endpoints()
    else:
        monitor.start_monitoring()

if __name__ == "__main__":
    main()
