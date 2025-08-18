"""
Test Job Classifier Service
Comprehensive tests for job type classification
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.job_classifier import JobClassifier, JobType

class TestJobClassifier:
    """Test suite for JobClassifier"""
    
    def test_identify_individual_job(self):
        """Test identification of individual jobs"""
        
        # Standard individual job
        job = {
            'task_type': 'protein_ligand_binding',
            'job_id': 'test123',
            'status': 'completed'
        }
        assert JobClassifier.classify_job(job) == JobType.INDIVIDUAL
        assert not JobClassifier.is_batch_job(job)
        assert not JobClassifier.is_batch_child(job)
        
        # Another individual task type
        job2 = {
            'task_type': 'nanobody_design',
            'job_id': 'test456'
        }
        assert JobClassifier.classify_job(job2) == JobType.INDIVIDUAL
    
    def test_identify_batch_parent(self):
        """Test identification of batch parent jobs"""
        
        # Batch job by task type
        job = {
            'task_type': 'batch_protein_ligand_screening',
            'total_children': 100,
            'job_id': 'batch123'
        }
        assert JobClassifier.classify_job(job) == JobType.BATCH_PARENT
        assert JobClassifier.is_batch_job(job)
        assert not JobClassifier.is_batch_child(job)
        
        # Batch job by explicit flag
        job2 = {
            'task_type': 'protein_ligand_binding',
            'is_batch_job': True,
            'individual_job_ids': ['job1', 'job2', 'job3']
        }
        assert JobClassifier.classify_job(job2) == JobType.BATCH_PARENT
        
        # Batch job by child job IDs
        job3 = {
            'task_type': 'protein_structure',
            'child_job_ids': ['child1', 'child2', 'child3', 'child4', 'child5']
        }
        assert JobClassifier.classify_job(job3) == JobType.BATCH_PARENT
        
        # Batch job by batch_info
        job4 = {
            'task_type': 'protein_ligand_binding',
            'batch_info': {
                'is_batch': True,
                'total_ligands': 50
            }
        }
        assert JobClassifier.classify_job(job4) == JobType.BATCH_PARENT
    
    def test_identify_batch_child(self):
        """Test identification of batch child jobs"""
        
        # Child by batch_id reference
        job = {
            'task_type': 'protein_ligand_binding',
            'batch_id': 'batch123',
            'batch_index': 5
        }
        assert JobClassifier.classify_job(job) == JobType.BATCH_CHILD
        assert not JobClassifier.is_batch_job(job)
        assert JobClassifier.is_batch_child(job)
        
        # Child by parent_batch_id
        job2 = {
            'task_type': 'protein_ligand_binding',
            'parent_batch_id': 'batch456'
        }
        assert JobClassifier.classify_job(job2) == JobType.BATCH_CHILD
        
        # Child by explicit flag
        job3 = {
            'task_type': 'protein_structure',
            'is_batch_child': True
        }
        assert JobClassifier.classify_job(job3) == JobType.BATCH_CHILD
    
    def test_extract_batch_metadata(self):
        """Test extraction of batch metadata"""
        
        # Batch with all metadata
        batch_job = {
            'id': 'batch123',
            'task_type': 'batch_protein_ligand_screening',
            'total_children': 100,
            'completed_children': 85,
            'failed_children': 5,
            'individual_job_ids': ['job1', 'job2', 'job3']
        }
        
        metadata = JobClassifier.extract_batch_metadata(batch_job)
        assert metadata['batch_id'] == 'batch123'
        assert metadata['batch_type'] == 'batch_protein_ligand_screening'
        assert metadata['total_children'] == 100
        assert metadata['completed_children'] == 85
        assert metadata['failed_children'] == 5
        assert len(metadata['child_job_ids']) == 3
        
        # Batch with individual_jobs array
        batch_job2 = {
            'job_id': 'batch456',
            'task_type': 'batch_protein_ligand_screening',
            'individual_jobs': [
                {'job_id': 'child1'},
                {'job_id': 'child2'},
                {'job_id': 'child3'}
            ]
        }
        
        metadata2 = JobClassifier.extract_batch_metadata(batch_job2)
        assert metadata2['batch_id'] == 'batch456'
        assert metadata2['total_children'] == 3
        assert 'child1' in metadata2['child_job_ids']
        
        # Non-batch job should return empty metadata
        individual_job = {'task_type': 'protein_ligand_binding'}
        metadata3 = JobClassifier.extract_batch_metadata(individual_job)
        assert metadata3 == {}
    
    def test_filter_jobs_by_type(self):
        """Test filtering jobs by type"""
        
        jobs = [
            {'task_type': 'protein_ligand_binding', 'id': '1'},  # Individual
            {'task_type': 'batch_protein_ligand_screening', 'id': '2'},  # Batch parent
            {'task_type': 'protein_ligand_binding', 'batch_id': 'batch123', 'id': '3'},  # Batch child
            {'task_type': 'nanobody_design', 'id': '4'},  # Individual
            {'task_type': 'protein_structure', 'is_batch_job': True, 'id': '5'},  # Batch parent
        ]
        
        # Filter individual jobs
        individuals = JobClassifier.filter_jobs_by_type(jobs, JobType.INDIVIDUAL)
        assert len(individuals) == 2
        assert individuals[0]['id'] == '1'
        assert individuals[1]['id'] == '4'
        
        # Filter batch parents
        batch_parents = JobClassifier.filter_jobs_by_type(jobs, JobType.BATCH_PARENT)
        assert len(batch_parents) == 2
        assert batch_parents[0]['id'] == '2'
        assert batch_parents[1]['id'] == '5'
        
        # Filter batch children
        batch_children = JobClassifier.filter_jobs_by_type(jobs, JobType.BATCH_CHILD)
        assert len(batch_children) == 1
        assert batch_children[0]['id'] == '3'
    
    def test_separate_jobs(self):
        """Test separating jobs into categories"""
        
        jobs = [
            {'task_type': 'protein_ligand_binding', 'id': '1'},
            {'task_type': 'batch_protein_ligand_screening', 'total_children': 50, 'id': '2'},
            {'task_type': 'protein_ligand_binding', 'batch_id': 'b1', 'id': '3'},
            {'task_type': 'protein_ligand_binding', 'batch_id': 'b1', 'id': '4'},
            {'task_type': 'nanobody_design', 'id': '5'},
        ]
        
        separated = JobClassifier.separate_jobs(jobs)
        
        assert len(separated[JobType.INDIVIDUAL]) == 2
        assert len(separated[JobType.BATCH_PARENT]) == 1
        assert len(separated[JobType.BATCH_CHILD]) == 2
        
        # Check specific jobs
        assert separated[JobType.INDIVIDUAL][0]['id'] in ['1', '5']
        assert separated[JobType.BATCH_PARENT][0]['id'] == '2'
        assert separated[JobType.BATCH_CHILD][0]['id'] in ['3', '4']
    
    def test_enhance_job_with_type(self):
        """Test enhancing job with type information"""
        
        # Individual job
        job = {'task_type': 'protein_ligand_binding', 'id': 'job1'}
        enhanced = JobClassifier.enhance_job_with_type(job)
        assert enhanced['_job_classification'] == 'individual'
        assert '_batch_metadata' not in enhanced
        
        # Batch parent job
        batch_job = {
            'task_type': 'batch_protein_ligand_screening',
            'id': 'batch1',
            'total_children': 100,
            'completed_children': 50
        }
        enhanced_batch = JobClassifier.enhance_job_with_type(batch_job)
        assert enhanced_batch['_job_classification'] == 'batch_parent'
        assert '_batch_metadata' in enhanced_batch
        assert enhanced_batch['_batch_metadata']['total_children'] == 100
        
        # Batch child job
        child_job = {
            'task_type': 'protein_ligand_binding',
            'batch_id': 'batch1',
            'batch_index': 5
        }
        enhanced_child = JobClassifier.enhance_job_with_type(child_job)
        assert enhanced_child['_job_classification'] == 'batch_child'
    
    def test_get_display_name(self):
        """Test getting appropriate display names"""
        
        # Individual job
        job = {
            'task_type': 'protein_ligand_binding',
            'job_name': 'My Protein Test',
            'id': 'job123'
        }
        display_name = JobClassifier.get_display_name(job)
        assert display_name == 'My Protein Test'
        
        # Batch parent job
        batch_job = {
            'task_type': 'batch_protein_ligand_screening',
            'job_name': 'Large Screen',
            'total_children': 100
        }
        batch_display = JobClassifier.get_display_name(batch_job)
        assert batch_display == 'Large Screen (Batch of 100)'
        
        # Batch child job
        child_job = {
            'task_type': 'protein_ligand_binding',
            'job_name': 'Ligand Test',
            'batch_id': 'batch123456789',
            'batch_index': 5
        }
        child_display = JobClassifier.get_display_name(child_job)
        assert 'Child 5' in child_display
        assert 'batch123' in child_display
    
    def test_edge_cases(self):
        """Test edge cases and unusual job structures"""
        
        # Empty job
        empty_job = {}
        assert JobClassifier.classify_job(empty_job) == JobType.INDIVIDUAL
        
        # Job with conflicting indicators (batch_id but also is_batch_job)
        # Should prioritize batch_child since it has a parent reference
        conflicting_job = {
            'task_type': 'protein_ligand_binding',
            'batch_id': 'parent123',
            'is_batch_job': True
        }
        assert JobClassifier.classify_job(conflicting_job) == JobType.BATCH_CHILD
        
        # Job with zero children but batch task type
        zero_children_batch = {
            'task_type': 'batch_protein_ligand_screening',
            'total_children': 0
        }
        assert JobClassifier.classify_job(zero_children_batch) == JobType.BATCH_PARENT


if __name__ == "__main__":
    # Run tests
    test_classifier = TestJobClassifier()
    
    print("Running JobClassifier tests...")
    
    test_classifier.test_identify_individual_job()
    print("✅ Individual job identification tests passed")
    
    test_classifier.test_identify_batch_parent()
    print("✅ Batch parent identification tests passed")
    
    test_classifier.test_identify_batch_child()
    print("✅ Batch child identification tests passed")
    
    test_classifier.test_extract_batch_metadata()
    print("✅ Batch metadata extraction tests passed")
    
    test_classifier.test_filter_jobs_by_type()
    print("✅ Job filtering tests passed")
    
    test_classifier.test_separate_jobs()
    print("✅ Job separation tests passed")
    
    test_classifier.test_enhance_job_with_type()
    print("✅ Job enhancement tests passed")
    
    test_classifier.test_get_display_name()
    print("✅ Display name tests passed")
    
    test_classifier.test_edge_cases()
    print("✅ Edge case tests passed")
    
    print("\n🎉 All JobClassifier tests passed successfully!")