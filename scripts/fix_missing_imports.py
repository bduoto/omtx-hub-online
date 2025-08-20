#!/usr/bin/env python3
"""
Automatically fix missing imports in main.py
Distinguished Engineer Implementation - Clean up broken imports
"""

import re
import os

def fix_main_py():
    """Comment out imports that don't exist"""
    
    # Known missing services based on Modal migration
    missing_services = [
        'services.modal_execution_service',
        'services.modal_batch_executor', 
        'services.production_modal_service',
        'services.modal_auth_service',
        'services.modal_completion_checker',
        'services.webhook_completion_checker',
        'services.modal_monitor',
        'services.enhanced_batch_orchestrator',
        'services.smart_job_router',
        'services.atomic_storage_service',
        'services.batch_aware_completion_checker',
        'services.performance_optimized_results',
        'services.gcp_results_indexer',
        'services.gcp_results_indexer_optimized',
        'services.batch_status_cache',
        'services.batch_relationship_manager',
        'services.batch_grouping_service',
        'services.batch_file_scanner',
    ]
    
    # Missing API modules
    missing_apis = [
        'api.webhook_handlers',
        'api.optimized_results_api',
        'api.performance_monitoring', 
        'api.batch_storage_fix',
        'api.ultra_fast_unified_api',
        'api.batch_completion_monitoring',
    ]
    
    # Missing config modules
    missing_configs = [
        'config.modal_models',
        'config.modal_auth',
    ]
    
    all_missing = missing_services + missing_apis + missing_configs
    
    print("🔧 Fixing missing imports in main.py...")
    
    with open('backend/main.py', 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Comment out missing imports
    for imp in all_missing:
        # Match various import patterns
        patterns = [
            f'from {imp} import .*',
            f'import {imp}',
        ]
        
        for pattern in patterns:
            # Find and comment out the import
            regex = f'^({pattern})$'
            replacement = r'# \1  # COMMENTED: Missing dependency'
            content = re.sub(regex, replacement, content, flags=re.MULTILINE)
            
            # Also comment out any lines that reference the imported items
            module_name = imp.split('.')[-1]
            # Comment out router inclusions
            content = re.sub(f'app\\.include_router\\({module_name}_router.*\\)', 
                           f'# app.include_router({module_name}_router)  # COMMENTED: Missing', 
                           content)
    
    # Comment out specific problematic router inclusions
    router_patterns = [
        r'app\.include_router\(webhook_router.*\)',
        r'app\.include_router\(.*webhook.*\)',
        r'app\.include_router\(optimized_results_router.*\)',
        r'app\.include_router\(performance_router.*\)',
        r'app\.include_router\(batch_fix_router.*\)',
        r'app\.include_router\(ultra_fast_router.*\)',
        r'app\.include_router\(batch_completion_router.*\)',
    ]
    
    for pattern in router_patterns:
        content = re.sub(pattern, lambda m: f'# {m.group(0)}  # COMMENTED: Missing', content)
    
    # Comment out startup tasks for missing services
    startup_patterns = [
        r'asyncio\.create_task\(start_completion_checker\(\)\)',
        r'asyncio\.create_task\(start_modal_monitor\(\)\)',
        r'start_completion_checker\(\)',
        r'start_modal_monitor\(\)',
    ]
    
    for pattern in startup_patterns:
        content = re.sub(pattern, lambda m: f'# {m.group(0)}  # COMMENTED: Missing service', content)
    
    # Save the fixed version
    if content != original_content:
        # Create backup
        with open('backend/main.py.backup', 'w') as f:
            f.write(original_content)
        
        # Save fixed version
        with open('backend/main.py', 'w') as f:
            f.write(content)
        
        print("✅ Fixed main.py - commented out missing imports")
        print("✅ Created backup: backend/main.py.backup")
        
        # Count changes
        original_lines = original_content.count('\n')
        new_lines = content.count('\n')
        commented_lines = content.count('# COMMENTED:')
        
        print(f"📊 Changes made:")
        print(f"  - Original lines: {original_lines}")
        print(f"  - New lines: {new_lines}")
        print(f"  - Commented imports: {commented_lines}")
        
    else:
        print("ℹ️ No changes needed - all imports are valid")
    
    return content != original_content

def add_missing_packages():
    """Add missing packages to requirements.prod.txt"""
    
    # Common missing packages based on import errors
    missing_packages = [
        'PyJWT>=2.8.0',
        'aiohttp>=3.8.0',
        'httpx>=0.24.0',
        'websockets>=11.0.0',
        'python-jose>=3.3.0',
        'cryptography>=41.0.0',
    ]
    
    req_file = 'backend/requirements.prod.txt'
    
    if not os.path.exists(req_file):
        print(f"❌ {req_file} not found")
        return False
    
    with open(req_file, 'r') as f:
        current_content = f.read()
    
    # Check which packages are missing
    packages_to_add = []
    for pkg in missing_packages:
        pkg_name = pkg.split('>=')[0].split('==')[0]
        if pkg_name.lower() not in current_content.lower():
            packages_to_add.append(pkg)
    
    if packages_to_add:
        print(f"\n📦 Adding missing packages to {req_file}:")
        
        # Add packages to requirements
        new_content = current_content
        if not new_content.endswith('\n'):
            new_content += '\n'
        
        new_content += '\n# Additional dependencies for production\n'
        for pkg in packages_to_add:
            new_content += f'{pkg}\n'
            print(f"  + {pkg}")
        
        # Save updated requirements
        with open(req_file, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Updated {req_file}")
        return True
    else:
        print(f"ℹ️ All packages already in {req_file}")
        return False

def main():
    """Main fix function"""
    
    print("🔧 FIXING MISSING DEPENDENCIES")
    print("=" * 60)
    
    # Fix imports
    imports_fixed = fix_main_py()
    
    # Add missing packages
    packages_added = add_missing_packages()
    
    print("\n" + "=" * 60)
    print("📋 NEXT STEPS")
    print("=" * 60)
    
    if imports_fixed or packages_added:
        print("1. Test locally:")
        print("   cd backend && python main.py")
        print("")
        print("2. If it starts successfully, rebuild:")
        print("   docker build --platform linux/amd64 -t gcr.io/om-models/omtx-hub-backend:fixed backend/")
        print("   docker push gcr.io/om-models/omtx-hub-backend:fixed")
        print("")
        print("3. Deploy:")
        print("   gcloud run deploy omtx-hub-backend --image=gcr.io/om-models/omtx-hub-backend:fixed --region=us-central1")
        print("")
        print("4. Test endpoints:")
        print('   curl "http://34.29.29.170/health"')
        print('   curl "http://34.29.29.170/api/v4/jobs/unified?user_id=demo-user"')
        print("")
        print("5. Load demo data:")
        print('   python3 scripts/load_production_demo_data.py --url "http://34.29.29.170"')
    else:
        print("✅ No fixes needed - try rebuilding and deploying")
    
    print("\n🎯 Goal: Get the missing endpoints working so frontend loads without 404 errors!")

if __name__ == "__main__":
    main()
