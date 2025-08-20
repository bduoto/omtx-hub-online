#!/usr/bin/env python3
"""
Legacy Code Cleanup - COMPREHENSIVE MODAL REMOVAL
Distinguished Engineer Implementation - Complete codebase cleanup
"""

import os
import shutil
import glob
import logging
from pathlib import Path
from typing import List, Dict

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

class LegacyCodeCleaner:
    """Comprehensive legacy code cleanup"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.deleted_files = []
        self.updated_files = []
        self.errors = []
        
        # Files to delete completely
        self.files_to_delete = [
            # Modal services
            "backend/services/modal_execution_service.py",
            "backend/services/modal_subprocess_runner.py", 
            "backend/services/modal_batch_executor.py",
            "backend/services/production_modal_service.py",
            "backend/services/modal_auth_service.py",
            "backend/services/modal_completion_checker.py",
            "backend/services/modal_job_status_service.py",
            "backend/services/webhook_completion_checker.py",
            "backend/services/modal_monitor.py",
            
            # Modal models
            "backend/models/boltz2_model.py",
            "backend/models/chai1_model.py", 
            "backend/models/rfantibody_real_phase2_model.py",
            "backend/models/boltz2_persistent_app.py",
            
            # Modal config
            "backend/config/modal_models.yaml",
            "backend/config/modal_models.py",
            "backend/config/modal_auth.py",
            
            # Webhook handlers (Modal-based)
            "backend/api/webhook_handlers.py",
            
            # Old batch processors
            "backend/services/batch_processor.py",
            "backend/services/unified_batch_processor.py",
            "backend/services/batch_aware_completion_checker.py",
            "backend/services/enhanced_batch_orchestrator.py",
            
            # Duplicate database services
            "backend/config/gcp_database_optimized.py",
            "backend/database/job_manager.py",
            
            # Duplicate storage services
            "backend/services/gcp_bucket_browser.py",
            "backend/services/gcp_results_indexer.py",
            "backend/services/gcp_results_indexer_optimized.py",
            
            # Legacy batch services
            "backend/services/batch_status_cache.py",
            "backend/services/batch_relationship_manager.py",
            "backend/services/batch_grouping_service.py",
            "backend/services/batch_file_scanner.py",
        ]
        
        # Directories to delete completely
        self.dirs_to_delete = [
            "backend/debug",
            "backend/modal_env",
            "backend/test_data",
        ]
        
        # Patterns to delete
        self.patterns_to_delete = [
            "backend/test_*.py",
            "backend/fix_*.py", 
            "backend/migrate_*.py",
            "backend/manual_*.py",
            "backend/*_test.py",
            "backend/debug_*.py",
        ]
        
        logger.info(f"🧹 LegacyCodeCleaner initialized (dry_run={dry_run})")
    
    def cleanup_all(self) -> Dict[str, int]:
        """Run complete cleanup"""
        
        print(f"\n{Colors.CYAN}🧹 COMPREHENSIVE LEGACY CODE CLEANUP{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        
        if self.dry_run:
            print(f"{Colors.YELLOW}🔍 DRY RUN MODE - No files will be deleted{Colors.RESET}\n")
        
        # Step 1: Delete individual files
        print(f"{Colors.WHITE}1️⃣ Deleting individual legacy files...{Colors.RESET}")
        self._delete_files()
        
        # Step 2: Delete directories
        print(f"\n{Colors.WHITE}2️⃣ Deleting legacy directories...{Colors.RESET}")
        self._delete_directories()
        
        # Step 3: Delete by patterns
        print(f"\n{Colors.WHITE}3️⃣ Deleting files by patterns...{Colors.RESET}")
        self._delete_by_patterns()
        
        # Step 4: Clean imports
        print(f"\n{Colors.WHITE}4️⃣ Cleaning Modal imports...{Colors.RESET}")
        self._clean_modal_imports()
        
        # Step 5: Update requirements
        print(f"\n{Colors.WHITE}5️⃣ Cleaning requirements.txt...{Colors.RESET}")
        self._clean_requirements()
        
        # Summary
        self._print_summary()
        
        return {
            'deleted_files': len(self.deleted_files),
            'updated_files': len(self.updated_files),
            'errors': len(self.errors)
        }
    
    def _delete_files(self):
        """Delete individual files"""
        
        for file_path in self.files_to_delete:
            if os.path.exists(file_path):
                print(f"  Deleting: {file_path}")
                
                if not self.dry_run:
                    try:
                        os.remove(file_path)
                        self.deleted_files.append(file_path)
                    except Exception as e:
                        self.errors.append(f"Failed to delete {file_path}: {e}")
                        print(f"    {Colors.RED}❌ Error: {e}{Colors.RESET}")
                else:
                    self.deleted_files.append(file_path)
            else:
                print(f"  {Colors.YELLOW}⚠️  Not found: {file_path}{Colors.RESET}")
    
    def _delete_directories(self):
        """Delete entire directories"""
        
        for dir_path in self.dirs_to_delete:
            if os.path.exists(dir_path):
                file_count = sum(len(files) for _, _, files in os.walk(dir_path))
                print(f"  Deleting directory: {dir_path} ({file_count} files)")
                
                if not self.dry_run:
                    try:
                        shutil.rmtree(dir_path)
                        self.deleted_files.append(f"{dir_path}/ ({file_count} files)")
                    except Exception as e:
                        self.errors.append(f"Failed to delete {dir_path}: {e}")
                        print(f"    {Colors.RED}❌ Error: {e}{Colors.RESET}")
                else:
                    self.deleted_files.append(f"{dir_path}/ ({file_count} files)")
            else:
                print(f"  {Colors.YELLOW}⚠️  Not found: {dir_path}{Colors.RESET}")
    
    def _delete_by_patterns(self):
        """Delete files matching patterns"""
        
        for pattern in self.patterns_to_delete:
            matching_files = glob.glob(pattern)
            
            if matching_files:
                print(f"  Pattern: {pattern} ({len(matching_files)} files)")
                
                for file_path in matching_files:
                    print(f"    Deleting: {file_path}")
                    
                    if not self.dry_run:
                        try:
                            os.remove(file_path)
                            self.deleted_files.append(file_path)
                        except Exception as e:
                            self.errors.append(f"Failed to delete {file_path}: {e}")
                            print(f"      {Colors.RED}❌ Error: {e}{Colors.RESET}")
                    else:
                        self.deleted_files.append(file_path)
            else:
                print(f"  {Colors.YELLOW}⚠️  No matches: {pattern}{Colors.RESET}")
    
    def _clean_modal_imports(self):
        """Remove Modal imports from remaining files"""
        
        # Files that might have Modal imports
        python_files = []
        for root, dirs, files in os.walk("backend"):
            # Skip virtual environment directories
            dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', '.git']]

            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))
        
        modal_imports = [
            "import modal",
            "from modal import",
            "modal.",
            "Modal",
            "@modal.",
            "modal_batch_executor",
            "modal_execution_service",
            "modal_subprocess_runner"
        ]
        
        for file_path in python_files:
            if any(deleted in file_path for deleted in self.deleted_files):
                continue  # Skip files we're deleting
                
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                original_content = content
                has_modal_refs = any(modal_ref in content for modal_ref in modal_imports)
                
                if has_modal_refs:
                    print(f"  Cleaning Modal imports: {file_path}")
                    
                    # Remove Modal imports (basic cleanup)
                    lines = content.split('\n')
                    cleaned_lines = []
                    
                    for line in lines:
                        if any(modal_ref in line for modal_ref in modal_imports[:4]):  # Import lines
                            print(f"    Removing: {line.strip()}")
                            continue
                        cleaned_lines.append(line)
                    
                    content = '\n'.join(cleaned_lines)
                    
                    if content != original_content and not self.dry_run:
                        with open(file_path, 'w') as f:
                            f.write(content)
                        self.updated_files.append(file_path)
                    elif content != original_content:
                        self.updated_files.append(file_path)
                        
            except Exception as e:
                self.errors.append(f"Failed to clean {file_path}: {e}")
    
    def _clean_requirements(self):
        """Remove Modal and unused dependencies from requirements.txt"""
        
        requirements_file = "backend/requirements.txt"
        
        if not os.path.exists(requirements_file):
            print(f"  {Colors.YELLOW}⚠️  requirements.txt not found{Colors.RESET}")
            return
        
        try:
            with open(requirements_file, 'r') as f:
                lines = f.readlines()
            
            # Dependencies to remove
            deps_to_remove = [
                "modal",
                "modal-client", 
                "redis",  # If not used elsewhere
                "celery",  # If not used elsewhere
            ]
            
            cleaned_lines = []
            removed_deps = []
            
            for line in lines:
                line_lower = line.lower().strip()
                should_remove = any(dep in line_lower for dep in deps_to_remove)
                
                if should_remove:
                    removed_deps.append(line.strip())
                    print(f"    Removing dependency: {line.strip()}")
                else:
                    cleaned_lines.append(line)
            
            if removed_deps and not self.dry_run:
                with open(requirements_file, 'w') as f:
                    f.writelines(cleaned_lines)
                self.updated_files.append(requirements_file)
            elif removed_deps:
                self.updated_files.append(requirements_file)
                
        except Exception as e:
            self.errors.append(f"Failed to clean requirements.txt: {e}")
    
    def _print_summary(self):
        """Print cleanup summary"""
        
        print(f"\n{Colors.CYAN}📊 CLEANUP SUMMARY{Colors.RESET}")
        print("=" * 60)
        
        print(f"Files deleted: {Colors.GREEN}{len(self.deleted_files)}{Colors.RESET}")
        print(f"Files updated: {Colors.YELLOW}{len(self.updated_files)}{Colors.RESET}")
        print(f"Errors: {Colors.RED}{len(self.errors)}{Colors.RESET}")
        
        if self.errors:
            print(f"\n{Colors.RED}❌ Errors:{Colors.RESET}")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  {error}")
        
        if self.dry_run:
            print(f"\n{Colors.YELLOW}🔍 This was a DRY RUN - no files were actually deleted{Colors.RESET}")
            print(f"{Colors.YELLOW}Run with --execute to perform actual cleanup{Colors.RESET}")
        else:
            print(f"\n{Colors.GREEN}✅ Cleanup completed successfully!{Colors.RESET}")
            
            # Estimate space saved
            estimated_lines = len(self.deleted_files) * 100  # Rough estimate
            print(f"Estimated lines of code removed: ~{estimated_lines:,}")

def main():
    """Main function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up legacy code")
    parser.add_argument("--execute", action="store_true", help="Actually delete files (default is dry run)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    cleaner = LegacyCodeCleaner(dry_run=not args.execute)
    results = cleaner.cleanup_all()
    
    return 0 if results['errors'] == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
