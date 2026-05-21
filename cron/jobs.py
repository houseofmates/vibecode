"""
Cron job management for Hermes WebUI.
Provides CRUD operations for scheduled tasks.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Lock for thread-safe job operations
_jobs_lock = threading.Lock()

# State directory
HOME = Path.home()
STATE_DIR = Path(os.getenv("HERMES_WEBUI_STATE_DIR", str(HOME / ".hermes" / "webui"))).expanduser().resolve()
JOBS_FILE = STATE_DIR / "cron_jobs.json"
JOB_RUNS_DIR = STATE_DIR / "cron_runs"

# Alias for backwards compatibility with API routes
OUTPUT_DIR = JOB_RUNS_DIR


def _ensure_dirs():
    """Ensure required directories exist."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    JOB_RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _load_jobs() -> list[dict]:
    """Load jobs from disk."""
    _ensure_dirs()
    if JOBS_FILE.exists():
        try:
            data = json.loads(JOBS_FILE.read_text())
            if isinstance(data, dict) and 'jobs' in data:
                return data['jobs']
            if isinstance(data, list):
                return data
            return []
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _save_jobs(jobs: list[dict]) -> bool:
    """Save jobs to disk."""
    _ensure_dirs()
    try:
        JOBS_FILE.write_text(json.dumps(jobs, indent=2))
        return True
    except IOError:
        return False


def list_jobs(include_disabled: bool = False) -> list[dict]:
    """Get all scheduled jobs.
    
    Args:
        include_disabled: If True, include disabled jobs
        
    Returns:
        List of job dictionaries
    """
    jobs = _load_jobs()
    if not include_disabled:
        jobs = [j for j in jobs if j.get("enabled", True)]
    return jobs


def get_job(job_id: str) -> Optional[dict]:
    """Get a specific job by ID."""
    jobs = _load_jobs()
    for job in jobs:
        if job.get("id") == job_id:
            return job
    return None


def create_job(
    name: str,
    schedule: str,
    command: str,
    enabled: bool = True,
    description: str = "",
    skills: Optional[list] = None
) -> Optional[dict]:
    """Create a new job.
    
    Args:
        name: Human-readable job name
        schedule: Cron expression or interval (e.g., "0 9 * * *")
        command: Command to execute
        enabled: Whether job is active
        description: Optional description
        skills: Optional skills to apply
        
    Returns:
        Created job dict or None on failure
    """
    with _jobs_lock:
        jobs = _load_jobs()
        
        # Generate unique ID
        job_id = f"job_{int(time.time() * 1000)}_{os.urandom(4).hex()[:8]}"
        
        job = {
            "id": job_id,
            "name": name,
            "schedule": schedule,
            "command": command,
            "enabled": enabled,
            "description": description,
            "skills": skills or [],
            "created_at": time.time(),
            "updated_at": time.time(),
            "last_run": None,
            "next_run": None,
            "run_count": 0
        }
        
        jobs.append(job)
        if _save_jobs(jobs):
            return job
        return None


def update_job(job_id: str, updates: dict) -> Optional[dict]:
    """Update an existing job.
    
    Args:
        job_id: ID of job to update
        updates: Dict of fields to update
        
    Returns:
        Updated job dict or None if not found
    """
    with _jobs_lock:
        jobs = _load_jobs()
        for i, job in enumerate(jobs):
            if job.get("id") == job_id:
                # Apply updates
                for key, value in updates.items():
                    if key not in ("id", "created_at"):
                        job[key] = value
                job["updated_at"] = time.time()
                if _save_jobs(jobs):
                    return job
                return None
        return None


def delete_job(job_id: str) -> bool:
    """Delete a job.
    
    Args:
        job_id: ID of job to delete
        
    Returns:
        True if deleted, False if not found
    """
    with _jobs_lock:
        jobs = _load_jobs()
        original_len = len(jobs)
        jobs = [j for j in jobs if j.get("id") != job_id]
        if len(jobs) == original_len:
            return False
        return _save_jobs(jobs)


def run_job_now(job_id: str) -> Optional[dict]:
    """Mark a job as run and update last_run time.
    
    Args:
        job_id: ID of job that ran
        
    Returns:
        Updated job dict or None
    """
    with _jobs_lock:
        jobs = _load_jobs()
        for job in jobs:
            if job.get("id") == job_id:
                job["last_run"] = time.time()
                job["run_count"] = job.get("run_count", 0) + 1
                if _save_jobs(jobs):
                    return job
                return None
        return None


def pause_job(job_id: str) -> Optional[dict]:
    """Pause (disable) a job."""
    return update_job(job_id, {"enabled": False})


def resume_job(job_id: str) -> Optional[dict]:
    """Resume (enable) a job."""
    return update_job(job_id, {"enabled": True})


def get_recent_output(limit: int = 50) -> list[dict]:
    """Get recent job output from log files.
    
    Args:
        limit: Maximum number of entries
        
    Returns:
        List of output entries
    """
    _ensure_dirs()
    outputs = []
    
    # Look for recent run logs
    for run_file in sorted(JOB_RUNS_DIR.glob("*.jsonl"), reverse=True):
        try:
            lines = run_file.read_text().strip().split("\n")
            for line in lines[-limit:]:
                if line:
                    try:
                        entry = json.loads(line)
                        outputs.append(entry)
                    except json.JSONDecodeError:
                        continue
        except IOError:
            continue
        
        if len(outputs) >= limit:
            break
    
    return outputs[:limit]


def get_job_output(job_id: str, limit: int = 100) -> list[dict]:
    """Get output for a specific job.
    
    Args:
        job_id: Job ID
        limit: Maximum entries
        
    Returns:
        List of output entries
    """
    _ensure_dirs()
    run_file = JOB_RUNS_DIR / f"{job_id}.jsonl"
    
    if not run_file.exists():
        return []
    
    try:
        lines = run_file.read_text().strip().split("\n")
        outputs = []
        for line in lines[-limit:]:
            if line:
                try:
                    entry = json.loads(line)
                    outputs.append(entry)
                except json.JSONDecodeError:
                    continue
        return outputs
    except IOError:
        return []



def parse_schedule(schedule_str: str) -> str:
    """Parse a schedule string into a cron expression.
    
    Supports human-readable strings like 'every 5 minutes', '30m', '2h', etc.
    Returns a cron expression string.
    """
    import re
    schedule_str = schedule_str.strip().lower()
    
    # Handle common formats
    if schedule_str.endswith('m') and schedule_str[:-1].isdigit():
        minutes = int(schedule_str[:-1])
        return f"*/{minutes} * * * *"
    elif schedule_str.endswith('h') and schedule_str[:-1].isdigit():
        hours = int(schedule_str[:-1])
        return f"0 */{hours} * * *"
    elif schedule_str.endswith('d') and schedule_str[:-1].isdigit():
        days = int(schedule_str[:-1])
        return f"0 0 */{days} * *"
    elif re.match(r'every (\d+) minutes?', schedule_str):
        match = re.match(r'every (\d+) minutes?', schedule_str)
        minutes = int(match.group(1))
        return f"*/{minutes} * * * *"
    elif re.match(r'every (\d+) hours?', schedule_str):
        match = re.match(r'every (\d+) hours?', schedule_str)
        hours = int(match.group(1))
        return f"0 */{hours} * * *"
    elif re.match(r'every (\d+) days?', schedule_str):
        match = re.match(r'every (\d+) days?', schedule_str)
        days = int(match.group(1))
        return f"0 0 */{days} * *"
    else:
        # Assume it's already a cron expression
        return schedule_str
remove_job = delete_job

# Alias functions for compatibility with cronjob_tools
def save_job(job_id=None, schedule=None, name=None, prompt=None, repeat=None, deliver=None, skills=None, model=None, script=None, no_agent=None, context_from=None, enabled_toolsets=None, workdir=None, profile=None, status=None):
    """Create or update a cron job. Alias for create_job/update_job compatibility."""
    from cron.jobs import create_job, update_job
    if job_id and get_job(job_id):
        return update_job(job_id, {'schedule': schedule, 'name': name, 'prompt': prompt, 'repeat': repeat, 'deliver': deliver, 'skills': skills, 'model': model, 'script': script, 'no_agent': no_agent, 'context_from': context_from, 'enabled_toolsets': enabled_toolsets, 'workdir': workdir, 'profile': profile, 'status': status})
    else:
        return create_job(schedule, name, prompt, repeat, deliver, skills, model, script, no_agent, context_from, enabled_toolsets, workdir, profile, status)

def resolve_job_ref(job_ref):
    """Resolve a job reference (ID or name) to a job dictionary."""
    job = get_job(job_ref)
    if job:
        return job
    # Try matching by name
    for j in list_jobs():
        if j.get('name') == job_ref:
            return j
    return None

def remove_job(job_id):
    """Remove a job by ID. Alias for delete_job compatibility."""
    return delete_job(job_id)

def get_recent_job_runs(limit=50):
    """Get recent job runs. Alias for get_recent_output compatibility."""
    return get_recent_output(limit)

class AmbiguousJobReference(Exception):
    """Exception raised when a job reference matches multiple jobs."""
    pass

def trigger_job(job_id):
    """Trigger a job run immediately. Alias for run_job_now compatibility."""
    return run_job_now(job_id)
