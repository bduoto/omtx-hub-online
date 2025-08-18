#!/usr/bin/env python3
"""
Manually run modal monitor to process stuck jobs
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to the Python path
sys.path.insert(0, '/Users/bryanduoto/Desktop/omtx-hub/backend')

from services.modal_monitor import ModalJobMonitor

async def run_modal_monitor():
    """Run modal monitor once to process stuck jobs"""
    print("🚀 Starting modal monitor to process stuck jobs...\n")
    
    try:
        monitor = ModalJobMonitor()
        
        # Run one check cycle
        print("1️⃣ Running job check cycle...")
        await monitor.check_running_jobs()
        
        print("\n✅ Modal monitor check completed!")
        
    except Exception as e:
        print(f"❌ Error running modal monitor: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(run_modal_monitor())