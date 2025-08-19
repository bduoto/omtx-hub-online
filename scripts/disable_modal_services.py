#!/usr/bin/env python3
"""
Disable Modal Services - CRITICAL FOR CLOUD RUN MIGRATION
Moves Modal services to backup and creates stub files to prevent import errors
"""

import os
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def disable_modal_services():
    """Move Modal services to backup directory and create stubs"""
    
    print("🔄 Disabling Modal services for Cloud Run migration...")
    
    modal_files = [
        "backend/services/modal_batch_executor.py",
        "backend/services/modal_execution_service.py", 
        "backend/services/modal_subprocess_runner.py",
        "backend/services/modal_monitor.py",
        "backend/services/production_modal_service.py",
        "backend/services/modal_auth_service.py",
        "backend/services/modal_completion_checker.py",
        "backend/services/modal_job_status_service.py",
        "backend/services/webhook_completion_checker.py",
        "backend/services/modal_batch_service.py"
    ]
    
    # Create backup directory
    backup_dir = Path("backend/services/modal_backup")
    backup_dir.mkdir(exist_ok=True)
    
    disabled_count = 0
    
    for file_path in modal_files:
        file_path = Path(file_path)
        
        if file_path.exists():
            # Move to backup
            filename = file_path.name
            backup_path = backup_dir / filename
            
            try:
                shutil.move(str(file_path), str(backup_path))
                
                # Create stub file to prevent import errors
                stub_content = f'''"""
{filename} - DISABLED FOR CLOUD RUN MIGRATION
Original file moved to {backup_dir}

This service has been replaced by Cloud Run equivalents:
- modal_batch_executor.py → cloud_run_batch_processor.py
- modal_execution_service.py → cloud_run_service.py
- modal_job_status_service.py → firestore real-time updates
"""

import logging

logger = logging.getLogger(__name__)

class DisabledModalService:
    """Stub class for disabled Modal service"""
    
    def __init__(self):
        logger.warning(f"⚠️ {{self.__class__.__name__}} has been disabled for Cloud Run migration")
        logger.warning("   Use Cloud Run equivalents instead")
    
    def __getattr__(self, name):
        raise NotImplementedError(
            f"Modal service method '{{name}}' is disabled. "
            f"Use Cloud Run batch processor instead."
        )

# Create stub instances for common Modal services
modal_batch_executor = DisabledModalService()
modal_execution_service = DisabledModalService()
modal_job_status_service = DisabledModalService()
production_modal_service = DisabledModalService()

# Legacy compatibility
class ModalBatchExecutor(DisabledModalService):
    pass

class ModalExecutionService(DisabledModalService):
    pass

class ModalJobStatusService(DisabledModalService):
    pass
'''
                
                with open(file_path, 'w') as f:
                    f.write(stub_content)
                
                print(f"✅ Disabled: {file_path}")
                disabled_count += 1
                
            except Exception as e:
                print(f"❌ Failed to disable {file_path}: {str(e)}")
        else:
            print(f"⚠️ File not found: {file_path}")
    
    # Also disable Modal imports in other files
    disable_modal_imports()
    
    print(f"\n✅ Disabled {disabled_count} Modal services")
    print(f"📁 Backup files stored in: {backup_dir}")
    print("🔄 Cloud Run services are now active")

def disable_modal_imports():
    """Replace Modal imports with Cloud Run equivalents"""
    
    print("\n🔄 Updating Modal imports...")
    
    import_replacements = [
        # Main application files
        ("backend/main.py", [
            ("from services.modal_", "# from services.modal_"),
            ("modal_", "# modal_")
        ]),
        
        # API endpoints
        ("backend/api/unified_endpoints.py", [
            ("from services.modal_execution_service", "from services.cloud_run_service"),
            ("modal_execution_service", "cloud_run_service")
        ]),
        
        # Other service files
        ("backend/services/user_management_service.py", [
            ("from services.modal_", "# from services.modal_"),
        ])
    ]
    
    for file_path, replacements in import_replacements:
        file_path = Path(file_path)
        
        if file_path.exists():
            try:
                # Read file content
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Apply replacements
                modified = False
                for old_text, new_text in replacements:
                    if old_text in content:
                        content = content.replace(old_text, new_text)
                        modified = True
                
                # Write back if modified
                if modified:
                    with open(file_path, 'w') as f:
                        f.write(content)
                    print(f"✅ Updated imports in: {file_path}")
                
            except Exception as e:
                print(f"❌ Failed to update {file_path}: {str(e)}")

def create_cloud_run_migration_flag():
    """Create flag file to indicate Cloud Run migration is complete"""
    
    flag_file = Path("backend/.cloud_run_migration_complete")
    
    with open(flag_file, 'w') as f:
        f.write(f"""# Cloud Run Migration Complete
# Generated: {datetime.now().isoformat()}
# 
# This file indicates that Modal services have been disabled
# and Cloud Run services are active.
#
# Services migrated:
# - Batch processing: modal_batch_executor → cloud_run_batch_processor
# - Job execution: modal_execution_service → cloud_run_service  
# - Status monitoring: modal_job_status_service → firestore real-time
# - Authentication: modal_auth_service → auth_middleware
#
# To rollback migration:
# 1. Delete this file
# 2. Restore files from backend/services/modal_backup/
# 3. Update imports back to Modal services
""")
    
    print(f"✅ Created migration flag: {flag_file}")

def verify_cloud_run_services():
    """Verify that Cloud Run services exist and are importable"""
    
    print("\n🔍 Verifying Cloud Run services...")
    
    required_services = [
        "backend/services/cloud_run_service.py",
        "backend/services/cloud_run_batch_processor.py",
        "backend/api/health_checks.py",
        "backend/middleware/security_middleware.py"
    ]
    
    missing_services = []
    
    for service_path in required_services:
        if not Path(service_path).exists():
            missing_services.append(service_path)
        else:
            print(f"✅ Found: {service_path}")
    
    if missing_services:
        print(f"\n❌ Missing Cloud Run services:")
        for service in missing_services:
            print(f"   - {service}")
        print("\n⚠️ Please ensure all Cloud Run services are implemented before disabling Modal")
        return False
    else:
        print("\n✅ All Cloud Run services are available")
        return True

def main():
    """Main function"""
    
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Disable Modal Services for Cloud Run Migration")
    parser.add_argument("--verify-only", action="store_true", help="Only verify Cloud Run services exist")
    parser.add_argument("--force", action="store_true", help="Force disable even if Cloud Run services missing")
    
    args = parser.parse_args()
    
    print("🚀 Modal to Cloud Run Migration Tool")
    print("=" * 50)
    
    if args.verify_only:
        success = verify_cloud_run_services()
        return 0 if success else 1
    
    # Verify Cloud Run services exist
    if not verify_cloud_run_services() and not args.force:
        print("\n❌ Cannot disable Modal services - Cloud Run services missing")
        print("   Use --force to disable anyway, or implement missing services first")
        return 1
    
    # Confirm action
    if not args.force:
        print("\n⚠️ WARNING: This will disable all Modal services!")
        print("   Make sure you have:")
        print("   1. Implemented Cloud Run batch processor")
        print("   2. Updated all API endpoints")
        print("   3. Tested the new system")
        print("")
        confirm = input("Type 'DISABLE' to confirm: ")
        if confirm != "DISABLE":
            print("❌ Operation cancelled")
            return 1
    
    # Perform migration
    try:
        disable_modal_services()
        create_cloud_run_migration_flag()
        
        print("\n🎉 Modal services successfully disabled!")
        print("🔄 Cloud Run services are now active")
        print("\n📋 Next steps:")
        print("1. Test batch processing with Cloud Run")
        print("2. Verify real-time updates work")
        print("3. Run integration tests")
        print("4. Deploy to production")
        
        return 0
        
    except Exception as e:
        print(f"\n💥 Migration failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
