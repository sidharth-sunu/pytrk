import os
import fnmatch

def load_ignore_patterns():
    """Load ignore patterns from .pytrkignore file."""
    patterns = set()
    if os.path.exists('.pytrkignore'):
        with open('.pytrkignore') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.add(line)
    return patterns

def is_ignored(path, patterns):
    """Check if a file path matches any ignore pattern."""
    for pat in patterns:
        if fnmatch.fnmatch(path, pat):
            return True
    return False

def get_user_info():
    """Get user name and email from .pytrkconfig or environment variables."""
    name = os.environ.get("PYTRK_NAME")
    email = os.environ.get("PYTRK_EMAIL")
    if not name or not email:
        if os.path.exists('.pytrkconfig'):
            with open('.pytrkconfig') as f:
                for line in f:
                    if line.startswith('name='):
                        name = line.split('=',1)[1].strip()
                    elif line.startswith('email='):
                        email = line.split('=',1)[1].strip()
    return name or "Unknown", email or "unknown@example.com"