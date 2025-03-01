"""Repository for managing bioinformatics jobs."""

from typing import Dict, List, Optional, Union
import uuid
from datetime import datetime

from blims.models.job import Job, JobStatus, JobType


class JobRepository:
    """Repository for managing bioinformatics jobs.
    
    This repository handles the storage and retrieval of Job objects, with
    methods for creating, updating, and querying jobs.
    """
    
    def __init__(self):
        """Initialize the job repository."""
        self.jobs: Dict[str, Job] = {}
    
    def create_job(self, job: Job) -> Job:
        """Store a new job in the repository.
        
        Args:
            job: The job to store
            
        Returns:
            The stored job with any repository-assigned fields
        """
        job_id = str(job.id)
        self.jobs[job_id] = job
        return job
    
    def get_job(self, job_id: Union[str, uuid.UUID]) -> Optional[Job]:
        """Retrieve a job by its ID.
        
        Args:
            job_id: The ID of the job to retrieve
            
        Returns:
            The job if found, None otherwise
        """
        job_id_str = str(job_id)
        return self.jobs.get(job_id_str)
    
    def update_job(self, job: Job) -> Job:
        """Update an existing job.
        
        Args:
            job: The job with updated fields
            
        Returns:
            The updated job
            
        Raises:
            ValueError: If the job doesn't exist
        """
        job_id = str(job.id)
        if job_id not in self.jobs:
            raise ValueError(f"Job with ID {job_id} not found")
        
        self.jobs[job_id] = job
        return job
    
    def update_job_status(self, job_id: Union[str, uuid.UUID], status: JobStatus) -> Job:
        """Update the status of a job.
        
        Args:
            job_id: The ID of the job to update
            status: The new status
            
        Returns:
            The updated job
            
        Raises:
            ValueError: If the job doesn't exist
        """
        job_id_str = str(job_id)
        job = self.get_job(job_id_str)
        if not job:
            raise ValueError(f"Job with ID {job_id_str} not found")
        
        job.update_status(status)
        return job
    
    def delete_job(self, job_id: Union[str, uuid.UUID]) -> bool:
        """Delete a job from the repository.
        
        Args:
            job_id: The ID of the job to delete
            
        Returns:
            True if the job was deleted, False if it didn't exist
        """
        job_id_str = str(job_id)
        if job_id_str in self.jobs:
            del self.jobs[job_id_str]
            return True
        return False
    
    def get_all_jobs(self) -> List[Job]:
        """Get all jobs in the repository.
        
        Returns:
            List of all jobs
        """
        return list(self.jobs.values())
    
    def get_jobs_by_sample(self, sample_id: Union[str, uuid.UUID]) -> List[Job]:
        """Get all jobs for a specific sample.
        
        Args:
            sample_id: The ID of the sample
            
        Returns:
            List of jobs for the sample
        """
        sample_id_str = str(sample_id)
        return [job for job in self.jobs.values() if str(job.sample_id) == sample_id_str]
    
    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get all jobs with a specific status.
        
        Args:
            status: The status to filter by
            
        Returns:
            List of jobs with the specified status
        """
        return [job for job in self.jobs.values() if job.status == status]
    
    def get_jobs_by_type(self, job_type: JobType) -> List[Job]:
        """Get all jobs of a specific type.
        
        Args:
            job_type: The job type to filter by
            
        Returns:
            List of jobs with the specified type
        """
        return [job for job in self.jobs.values() if job.job_type == job_type]
    
    def get_jobs_created_after(self, timestamp: datetime) -> List[Job]:
        """Get all jobs created after a specific time.
        
        Args:
            timestamp: The timestamp to filter by
            
        Returns:
            List of jobs created after the timestamp
        """
        return [job for job in self.jobs.values() if job.created_at > timestamp]
    
    def get_jobs_for_user(self, username: str) -> List[Job]:
        """Get all jobs created by a specific user.
        
        Args:
            username: The username to filter by
            
        Returns:
            List of jobs created by the user
        """
        return [job for job in self.jobs.values() if job.created_by == username]