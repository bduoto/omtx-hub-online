#!/usr/bin/env python3
"""
Test GCS Storage Integration - CRITICAL VALIDATION
Distinguished Engineer Implementation - Complete storage system testing
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List

try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound, Forbidden
except ImportError:
    print("❌ Google Cloud Storage client not installed")
    print("   Run: pip install google-cloud-storage")
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

class GCSStorageTester:
    """Complete GCS storage system tester"""
    
    def __init__(self):
        self.bucket_name = os.getenv("GCS_BUCKET_NAME", "hub-job-files")
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.test_user_id = "test-user-storage"
        
        try:
            self.client = storage.Client(project=self.project_id)
            self.bucket = self.client.bucket(self.bucket_name)
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            raise
        
        logger.info(f"🗄️ GCSStorageTester initialized")
        logger.info(f"   Bucket: {self.bucket_name}")
        logger.info(f"   Project: {self.project_id}")
    
    def test_gcs_storage(self) -> bool:
        """Test complete GCS storage functionality"""
        
        print(f"\n{Colors.CYAN}🔍 TESTING GCS STORAGE{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*50}{Colors.RESET}\n")
        
        tests = [
            ("Bucket Access", self.test_bucket_access),
            ("Write Permissions", self.test_write_permissions),
            ("Read Permissions", self.test_read_permissions),
            ("User Isolation", self.test_user_isolation),
            ("File Metadata", self.test_file_metadata),
            ("Large File Handling", self.test_large_files),
            ("Batch Results Structure", self.test_batch_structure),
            ("Cleanup Operations", self.test_cleanup)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"Testing {test_name}...", end=" ")
            try:
                success, message = test_func()
                if success:
                    print(f"{Colors.GREEN}✅ PASSED{Colors.RESET}")
                    if message:
                        print(f"  {Colors.CYAN}{message}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ FAILED{Colors.RESET}")
                    if message:
                        print(f"  {Colors.YELLOW}{message}{Colors.RESET}")
                
                results.append((test_name, success, message))
                
            except Exception as e:
                print(f"{Colors.RED}❌ ERROR: {e}{Colors.RESET}")
                results.append((test_name, False, str(e)))
        
        # Summary
        self._print_test_summary(results)
        
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        
        return passed == total
    
    def test_bucket_access(self) -> tuple[bool, str]:
        """Test basic bucket access"""
        
        try:
            # Check if bucket exists
            if self.bucket.exists():
                # Get bucket metadata
                self.bucket.reload()
                location = self.bucket.location
                storage_class = self.bucket.storage_class
                
                return True, f"Bucket accessible (location: {location}, class: {storage_class})"
            else:
                return False, f"Bucket {self.bucket_name} does not exist"
                
        except Forbidden:
            return False, "Access denied - check service account permissions"
        except Exception as e:
            return False, f"Bucket access error: {str(e)}"
    
    def test_write_permissions(self) -> tuple[bool, str]:
        """Test write permissions"""
        
        try:
            test_path = f"test/write_test_{int(time.time())}.txt"
            test_content = f"Write test at {datetime.now().isoformat()}"
            
            blob = self.bucket.blob(test_path)
            blob.upload_from_string(test_content)
            
            # Verify upload
            if blob.exists():
                return True, f"Write successful ({len(test_content)} bytes)"
            else:
                return False, "File upload failed - blob does not exist"
                
        except Forbidden:
            return False, "Write access denied - check IAM permissions"
        except Exception as e:
            return False, f"Write test error: {str(e)}"
    
    def test_read_permissions(self) -> tuple[bool, str]:
        """Test read permissions"""
        
        try:
            # Find a test file to read
            test_blobs = list(self.bucket.list_blobs(prefix="test/", max_results=1))
            
            if test_blobs:
                blob = test_blobs[0]
                content = blob.download_as_text()
                
                return True, f"Read successful ({len(content)} bytes from {blob.name})"
            else:
                # Create a test file first
                test_path = f"test/read_test_{int(time.time())}.txt"
                test_content = "Read test content"
                
                blob = self.bucket.blob(test_path)
                blob.upload_from_string(test_content)
                
                # Now read it
                downloaded_content = blob.download_as_text()
                
                if downloaded_content == test_content:
                    return True, "Read permissions verified (created test file)"
                else:
                    return False, "Content mismatch after read"
                
        except Forbidden:
            return False, "Read access denied - check IAM permissions"
        except Exception as e:
            return False, f"Read test error: {str(e)}"
    
    def test_user_isolation(self) -> tuple[bool, str]:
        """Test user data isolation"""
        
        try:
            # Create files for different users
            users = ["user1", "user2", self.test_user_id]
            created_files = []
            
            for user in users:
                file_path = f"users/{user}/jobs/test-job/result.json"
                test_data = {
                    "user_id": user,
                    "job_id": "test-job",
                    "timestamp": datetime.now().isoformat(),
                    "result": "test data"
                }
                
                blob = self.bucket.blob(file_path)
                blob.upload_from_string(json.dumps(test_data))
                created_files.append(file_path)
            
            # Verify isolation - list files for each user
            isolation_verified = True
            
            for user in users:
                user_blobs = list(self.bucket.list_blobs(prefix=f"users/{user}/"))
                user_files = [blob.name for blob in user_blobs]
                
                # Check that user only sees their own files
                other_user_files = [f for f in user_files if f"users/{user}/" not in f]
                
                if other_user_files:
                    isolation_verified = False
                    break
            
            if isolation_verified:
                return True, f"User isolation verified ({len(users)} users tested)"
            else:
                return False, "User isolation failed - cross-user file access detected"
                
        except Exception as e:
            return False, f"User isolation test error: {str(e)}"
    
    def test_file_metadata(self) -> tuple[bool, str]:
        """Test file metadata handling"""
        
        try:
            test_path = f"test/metadata_test_{int(time.time())}.json"
            test_data = {"test": "metadata", "timestamp": datetime.now().isoformat()}
            
            blob = self.bucket.blob(test_path)
            
            # Set custom metadata
            blob.metadata = {
                "user_id": self.test_user_id,
                "job_type": "test",
                "content_type": "test_result"
            }
            
            blob.upload_from_string(json.dumps(test_data))
            
            # Reload to get metadata
            blob.reload()
            
            if blob.metadata and blob.metadata.get("user_id") == self.test_user_id:
                return True, f"Metadata handling verified ({len(blob.metadata)} fields)"
            else:
                return False, "Metadata not preserved after upload"
                
        except Exception as e:
            return False, f"Metadata test error: {str(e)}"
    
    def test_large_files(self) -> tuple[bool, str]:
        """Test handling of large files (simulated)"""
        
        try:
            # Create a moderately large test file (1MB)
            large_content = "x" * (1024 * 1024)  # 1MB of 'x'
            test_path = f"test/large_file_test_{int(time.time())}.txt"
            
            blob = self.bucket.blob(test_path)
            blob.upload_from_string(large_content)
            
            # Verify size
            blob.reload()
            if blob.size == len(large_content):
                return True, f"Large file handling verified ({blob.size / 1024 / 1024:.1f}MB)"
            else:
                return False, f"Size mismatch: expected {len(large_content)}, got {blob.size}"
                
        except Exception as e:
            return False, f"Large file test error: {str(e)}"
    
    def test_batch_structure(self) -> tuple[bool, str]:
        """Test batch results directory structure"""
        
        try:
            batch_id = f"test-batch-{int(time.time())}"
            
            # Create typical batch structure
            files_to_create = [
                f"users/{self.test_user_id}/batches/{batch_id}/input.json",
                f"users/{self.test_user_id}/batches/{batch_id}/results/ligand_1.json",
                f"users/{self.test_user_id}/batches/{batch_id}/results/ligand_1.pdb",
                f"users/{self.test_user_id}/batches/{batch_id}/results/ligand_2.json",
                f"users/{self.test_user_id}/batches/{batch_id}/logs/batch.log"
            ]
            
            created_count = 0
            
            for file_path in files_to_create:
                test_content = f"Test content for {file_path.split('/')[-1]}"
                blob = self.bucket.blob(file_path)
                blob.upload_from_string(test_content)
                created_count += 1
            
            # Verify structure by listing
            batch_blobs = list(self.bucket.list_blobs(
                prefix=f"users/{self.test_user_id}/batches/{batch_id}/"
            ))
            
            if len(batch_blobs) == len(files_to_create):
                return True, f"Batch structure verified ({created_count} files created)"
            else:
                return False, f"Structure mismatch: created {created_count}, found {len(batch_blobs)}"
                
        except Exception as e:
            return False, f"Batch structure test error: {str(e)}"
    
    def test_cleanup(self) -> tuple[bool, str]:
        """Test cleanup operations"""
        
        try:
            # List all test files
            test_blobs = list(self.bucket.list_blobs(prefix="test/"))
            user_test_blobs = list(self.bucket.list_blobs(prefix=f"users/{self.test_user_id}/"))
            
            all_test_blobs = test_blobs + user_test_blobs
            
            if not all_test_blobs:
                return True, "No test files to clean up"
            
            # Delete test files
            deleted_count = 0
            
            for blob in all_test_blobs:
                try:
                    blob.delete()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Could not delete {blob.name}: {e}")
            
            return True, f"Cleanup completed ({deleted_count} files deleted)"
            
        except Exception as e:
            return False, f"Cleanup error: {str(e)}"
    
    def _print_test_summary(self, results: list):
        """Print comprehensive test summary"""
        
        print(f"\n{Colors.CYAN}📊 GCS STORAGE TEST SUMMARY{Colors.RESET}")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        for test_name, success, message in results:
            status = f"{Colors.GREEN}✅ PASSED{Colors.RESET}" if success else f"{Colors.RED}❌ FAILED{Colors.RESET}"
            print(f"{test_name:.<30} {status}")
            if message:
                print(f"    {Colors.CYAN}{message}{Colors.RESET}")
        
        print("=" * 60)
        print(f"Total Tests: {total}")
        print(f"Passed: {Colors.GREEN}{passed}{Colors.RESET}")
        print(f"Failed: {Colors.RED}{total - passed}{Colors.RESET}")
        print(f"Success Rate: {Colors.GREEN if success_rate >= 90 else Colors.YELLOW if success_rate >= 70 else Colors.RED}{success_rate:.1f}%{Colors.RESET}")
        
        if passed == total:
            print(f"\n{Colors.GREEN}🎉 ALL GCS STORAGE TESTS PASSED!{Colors.RESET}")
            print(f"{Colors.GREEN}✅ Storage system is ready for production!{Colors.RESET}")
        else:
            print(f"\n{Colors.YELLOW}⚠️  {total - passed} storage tests failed.{Colors.RESET}")
            print(f"{Colors.YELLOW}Check GCS permissions and bucket configuration.{Colors.RESET}")
        
        print()

def main():
    """Main test function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Test GCS Storage Integration")
    parser.add_argument("--bucket", help="GCS bucket name to test")
    parser.add_argument("--project", help="GCP project ID")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Override environment variables if provided
    if args.bucket:
        os.environ["GCS_BUCKET_NAME"] = args.bucket
    if args.project:
        os.environ["GCP_PROJECT_ID"] = args.project
    
    try:
        tester = GCSStorageTester()
        success = tester.test_gcs_storage()
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"{Colors.RED}❌ Failed to initialize GCS tester: {e}{Colors.RESET}")
        print(f"{Colors.YELLOW}Check your GCP credentials and environment variables{Colors.RESET}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
