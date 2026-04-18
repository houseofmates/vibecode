"""
Remote Skills tool for vibecode - accesses skills on ubuntu (.250) via SSH
"""
import json
import subprocess
from pathlib import Path

# Remote skills directory
REMOTE_HOST = "house@192.168.4.250"
REMOTE_SKILLS_DIR = "/home/house/.hermes/skills"


def _run_remote(cmd: str):
    """Run a command remotely on .250."""
    try:
        result = subprocess.run(
            ["ssh", REMOTE_HOST, cmd],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "SSH timeout"
    except Exception as e:
        return False, "", str(e)


def skills_list():
    """List all available skills from remote .250."""
    skills = []
    
    try:
        # List directories in skills folder
        ok, out, err = _run_remote(f"ls -1 {REMOTE_SKILLS_DIR}")
        
        if not ok:
            return json.dumps({
                "skills": [], 
                "error": f"Failed to list remote skills: {err}",
                "remote_host": "192.168.4.250"
            })
        
        for name in out.strip().split("\n"):
            name = name.strip()
            if not name or name.startswith("."):
                continue
                
            # Check for SKILL.md
            ok2, _, _ = _run_remote(f"test -f {REMOTE_SKILLS_DIR}/{name}/SKILL.md && echo exists")
            has_skill_file = ok2
            
            # Try to read frontmatter
            title = name
            category = "General"
            
            if has_skill_file:
                ok3, content, _ = _run_remote(f"head -30 {REMOTE_SKILLS_DIR}/{name}/SKILL.md")
                if ok3 and content:
                    # Parse frontmatter
                    if content.startswith("---"):
                        end = content.find("---", 3)
                        if end > 0:
                            fm = content[3:end]
                            for line in fm.split("\n"):
                                if ":" in line:
                                    key, val = line.split(":", 1)
                                    key = key.strip()
                                    val = val.strip().strip('"').strip("'")
                                    if key == "title":
                                        title = val
                                    elif key == "category":
                                        category = val
            
            skills.append({
                "name": name,
                "title": title,
                "category": category,
                "hasSkillFile": has_skill_file
            })
            
    except Exception as e:
        return json.dumps({"skills": [], "error": str(e), "remote_host": "192.168.4.250"})
    
    return json.dumps({"skills": skills})


def skill_view(name: str, file_path: str = None) -> str:
    """View skill content from remote .250."""
    try:
        # Validate name to prevent path injection
        if "/" in name or ".." in name or name.startswith("."):
            return json.dumps({"error": "Invalid skill name"})
        
        skill_path = f"{REMOTE_SKILLS_DIR}/{name}"
        
        # Check skill exists
        ok, _, _ = _run_remote(f"test -d {skill_path} && echo exists")
        if not ok:
            return json.dumps({"error": "Skill not found", "name": name})
        
        # If file_path specified, read that file
        if file_path:
            # Prevent directory traversal
            if ".." in file_path or file_path.startswith("/"):
                return json.dumps({"error": "Invalid file path"})
            
            full_path = f"{skill_path}/{file_path}"
            ok2, content, err = _run_remote(f"cat {full_path}")
            
            if not ok2:
                return json.dumps({"error": f"File not found: {file_path}"})
            
            return json.dumps({
                "name": name,
                "file_path": file_path,
                "content": content
            })
        
        # Otherwise read SKILL.md
        ok2, content, _ = _run_remote(f"cat {skill_path}/SKILL.md 2>/dev/null || echo ''")
        return json.dumps({
            "name": name,
            "content": content
        })
        
    except Exception as e:
        return json.dumps({"error": str(e)})


def skill_save(name: str, content: str, file_path: str = "SKILL.md") -> str:
    """Save skill content to remote .250."""
    try:
        # Validate name
        if "/" in name or ".." in name:
            return json.dumps({"error": "Invalid skill name"})
        
        # Prevent directory traversal in file_path
        if ".." in file_path or file_path.startswith("/"):
            return json.dumps({"error": "Invalid file path"})
        
        # Create directory if needed
        skill_path = f"{REMOTE_SKILLS_DIR}/{name}"
        _run_remote(f"mkdir -p {skill_path}")
        
        # Write file using heredoc
        full_path = f"{skill_path}/{file_path}"
        escaped_content = content.replace("'", "'\\''")  # Escape single quotes
        
        ok, _, err = _run_remote(f"cat > {full_path} << 'EOFREMOTE'\n{escaped_content}\nEOFREMOTE")
        
        if ok:
            return json.dumps({"ok": True, "name": name, "path": full_path})
        else:
            return json.dumps({"error": f"Failed to save: {err}"})
            
    except Exception as e:
        return json.dumps({"error": str(e)})


def skill_delete(name: str) -> str:
    """Delete a skill from remote .250."""
    try:
        if "/" in name or ".." in name or name.startswith("."):
            return json.dumps({"error": "Invalid skill name"})
        
        skill_path = f"{REMOTE_SKILLS_DIR}/{name}"
        ok, _, _ = _run_remote(f"rm -rf {skill_path}")
        
        if ok:
            return json.dumps({"ok": True, "name": name})
        else:
            return json.dumps({"error": "Failed to delete skill"})
            
    except Exception as e:
        return json.dumps({"error": str(e)})


# Keep backward compatibility with existing code
SKILLS_DIR = Path("/home/house/.hermes/skills")
