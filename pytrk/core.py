import os
import sys
import hashlib
import zlib
import time
import difflib
from .utils import load_ignore_patterns, is_ignored, get_user_info

def init():
    """Initialize a new pytrk repository."""
    os.makedirs(".pytrk/objects", exist_ok=True)
    os.makedirs(".pytrk/refs/heads", exist_ok=True)
    with open(".pytrk/HEAD", "w") as f:
        f.write("ref: refs/heads/main\n")
    print("initialized pytrk repo")

def hash_dir_create(data):
    """Hash and compress data, store in objects directory."""
    hash_data = hashlib.sha1(data).hexdigest()
    data = zlib.compress(data)
    obj_dir = f".pytrk/objects/{hash_data[:2]}"
    os.makedirs(obj_dir, exist_ok=True)
    with open(f"{obj_dir}/{hash_data[2:]}", "wb") as f:
        f.write(data)
    return hash_data

def hash_object(filename):
    """Hash a file as a blob and store it."""
    try:
        with open(filename, "rb") as f:
            data = f.read()
    except Exception as e:
        print(f"Error reading file {filename}: {e}")
        return None
    header = f"blob {len(data)}\0".encode()
    blob = header + data
    return hash_dir_create(blob)

def cat_file(hash_data):
    """Print the contents of a blob object."""
    path = f".pytrk/objects/{hash_data[:2]}/{hash_data[2:]}"
    try:
        with open(path, "rb") as f:
            data = zlib.decompress(f.read())
        content = data[data.index(b'\x00')+1:]
        print(content.decode())
    except Exception as e:
        print(f"Error reading object {hash_data}: {e}")

def add(path_spec):
    """
    Add file contents to the index.

    If path_spec is '.', it scans the entire working directory and updates the
    index to match, staging all new, modified, and deleted files.

    If path_spec is a file, it adds or updates just that single file in the index.
    """
    patterns = load_ignore_patterns()
    index_path = ".pytrk/index.txt"

    # ======================================================
    #  Logic for 'pytrk add .'
    # ======================================================
    if path_spec == ".":
        # First, read all the files currently in the index.
        # We store them in a dictionary mapping: {file_path: hash}
        try:
            with open(index_path, 'r') as f:
                index_files = dict(line.strip().split(' ', 1) for line in f if line.strip())
        except FileNotFoundError:
            index_files = {}

        # Keep track of files that are still present in the working directory.
        updated_index = {}
        files_to_ignore = {".pytrk", ".git", ".venv", "__pycache__"}

        # Walk through the entire project directory.
        for root, dirs, files in os.walk('.', topdown=True):
            # Don't descend into ignored directories.
            dirs[:] = [d for d in dirs if d not in files_to_ignore]

            for filename in files:
                file_path = os.path.join(root, filename)
                # Normalize path separators for consistency.
                rel_path = os.path.relpath(file_path).replace("\\", "/")

                if not is_ignored(rel_path, patterns):
                    # This file is in the working dir and not ignored.
                    # Add it to our updated index with its current hash.
                    hash_val = hash_object(rel_path)
                    if hash_val:
                        updated_index[rel_path] = hash_val

        # Overwrite the old index with the updated list of files.
        # This automatically handles:
        #   - NEW files (they are in updated_index but not the old index)
        #   - MODIFIED files (their hash in updated_index is different)
        #   - DELETED files (they were in the old index but not updated_index)
        with open(index_path, "w") as f:
            for path, hash_val in sorted(updated_index.items()):
                f.write(f"{hash_val} {path}\n")

        print("Staged all changes.")
        return

    # ======================================================
    #  Logic for 'pytrk add <file>'
    # ======================================================
    # Normalize path for consistency
    rel_path = os.path.relpath(path_spec).replace("\\", "/")
    
    if is_ignored(rel_path, patterns):
        print(f"Error: '{rel_path}' is ignored by .pytrkignore.")
        return

    if not os.path.exists(rel_path):
        print(f"Error: pathspec '{rel_path}' did not match any files.")
        return

    hash_val = hash_object(rel_path)
    if not hash_val:
        return

    # Read the index to update it
    try:
        with open(index_path, 'r') as f:
            index_files = dict(line.strip().split(' ', 1) for line in f if line.strip())
    except FileNotFoundError:
        index_files = {}

    # Add or update the entry for the specific file
    index_files[rel_path] = hash_val

    # Write the modified index back to the file
    with open(index_path, "w") as f:
        for path, h in sorted(index_files.items()):
            f.write(f"{h} {path}\n")

    print(f"added '{rel_path}' to index")


def write_tree():
    """Write the current index as a tree object and return its hash."""
    entries = []
    try:
        with open(".pytrk/index.txt") as f:
            for line in f:
                if line.strip():
                    hash, path = line.strip().split(" ", 1)
                    # Use os-independent paths in tree object
                    path = path.replace("\\", "/")
                    entry = f"100644 {path}".encode() + b"\x00" + bytes.fromhex(hash)
                    entries.append(entry)
    except Exception as e:
        print(f"Error writing tree: {e}")
        return None
    tree_content = b"".join(entries)
    tree_header = f"tree {len(tree_content)}\0".encode()
    tree = tree_header + tree_content
    return hash_dir_create(tree)

def commit(message):
    """Commit the current index with a message."""
    tree_hash = write_tree()
    if not tree_hash:
        print("Failed to write tree. Is the index empty?")
        return
    timestamp = int(time.time())
    name, email = get_user_info()
    try:
        with open(".pytrk/HEAD") as f:
            head = f.read().strip()
        if not head.startswith("ref: "):
            print("HEAD is detached or corrupted.")
            return
        ref = head[5:]
        ref_path = os.path.join(".pytrk", ref)
        parent = None
        if os.path.exists(ref_path):
            with open(ref_path) as f:
                parent = f.read().strip()
        lines = [f"tree {tree_hash}"]
        if parent:
            lines.append(f"parent {parent}")
        lines += [
            f"author {name} <{email}> {timestamp}",
            f"committer {name} <{email}> {timestamp}",
            "",
            message
        ]
        body = "\n".join(lines).encode()
        commit_body = f"commit {len(body)}\0".encode() + body
        commit_hash = hash_dir_create(commit_body)
        with open(ref_path, "w") as f:
            f.write(commit_hash + "\n")
        print(f"committed: {commit_hash}")
    except Exception as e:
        print(f"Error during commit: {e}")

def log():
    """Show commit history for the current branch."""
    try:
        with open(".pytrk/HEAD") as f:
            head = f.read().strip()
        if not head.startswith("ref: "):
            print("HEAD is detached or corrupted.")
            return
        ref = head[5:]
        ref_path = os.path.join(".pytrk", ref)
        if not os.path.exists(ref_path):
            print("No commits found.")
            return
        with open(ref_path) as f:
            current = f.read().strip()
        while current:
            obj_path = f".pytrk/objects/{current[:2]}/{current[2:]}"
            with open(obj_path, "rb") as f:
                data = zlib.decompress(f.read())
            commit_txt = data[data.index(b'\x00')+1:].decode()
            lines = commit_txt.splitlines()
            tree, parent, author = "", None, ""
            message_lines, reading_msg = [], False
            for line in lines:
                if reading_msg:
                    message_lines.append(line)
                elif line.startswith("tree "):
                    tree = line[5:]
                elif line.startswith("parent "):
                    parent = line[7:]
                elif line.startswith("author "):
                    author = line
                elif line == "":
                    reading_msg = True
            print(f"commit {current}")
            print(author)
            print()
            for msg in message_lines:
                print(f"    {msg}")
            print()
            current = parent if parent else None
    except Exception as e:
        print(f"Error during log: {e}")

def list_files():
    """List files tracked by the latest commit of the current branch (supports nested directories)."""
    files = []
    try:
        with open(".pytrk/HEAD") as f:
            data = f.read()
        og_path = f".pytrk/{data[5:].strip()}"
        with open(og_path) as f:
            data = f.read().strip()
            path = f".pytrk/objects/{data[:2]}/{data[2:]}"
        with open(path,"rb") as f:
            data = f.read()
            data = zlib.decompress(data).decode().splitlines()
        for i in data:
            if i.startswith("commit "):
                i = i.split("\x00")
                commit_hash = i[1][5:]
        path = f".pytrk/objects/{commit_hash[:2]}/{commit_hash[2:]}"
        with open(path,"rb") as f:
            tree_data = f.read()
            tree_data = zlib.decompress(tree_data)
        i = tree_data.index(b'\x00')+1
        while(i<len(tree_data)):
            end = tree_data.index(b'\x00',i)
            meta = tree_data[i:end]
            mode,filename = meta.split(b" ",1)
            files.append(filename.decode())
            i = end+21
        for f in files:
            print(f)
        return files
    except Exception as e:
        print(f"Error listing files: {e}")
        return []

def checkout(name):
    """Switch to a branch or commit, restoring files from the tree object."""
    files_to_remove = list_files()
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"removed {file}")
    branch_path = f".pytrk/refs/heads/{name}"
    if os.path.exists(branch_path):
        with open(branch_path) as f:
            commit_hash = f.read().strip()
        with open(".pytrk/HEAD","w") as f:
            f.write(f"ref: refs/heads/{name}\n")
        print(f"switched to branch {name}")
    else:
        commit_hash = name
        print(f"checking out to commit {commit_hash}")
    obj_path = f".pytrk/objects/{commit_hash[:2]}/{commit_hash[2:]}"
    if not os.path.exists(obj_path):
        print("Commit not found.")
        return
    with open(obj_path, "rb") as f:
        data = zlib.decompress(f.read())
    body = data[data.index(b'\x00')+1:].decode()
    lines = body.splitlines()
    if not lines[0].startswith("tree "):
        print("Invalid commit object.")
        return
    tree_hash = lines[0].split(" ")[1]
    with open(".pytrk/HEAD") as f:
        head = f.read().strip()
    if head.startswith("ref: "):
        ref_path = os.path.join(".pytrk", head[5:])
        with open(ref_path, "w") as f:
            f.write(commit_hash + "\n")
    else:
        print("HEAD is detached or corrupted.")
        return
    # Load tree
    tree_path = f".pytrk/objects/{tree_hash[:2]}/{tree_hash[2:]}"
    with open(tree_path, "rb") as f:
        tree_data = zlib.decompress(f.read())
    null_index = tree_data.index(b'\x00')
    i = null_index + 1
    while i < len(tree_data):
        end = tree_data.index(b'\x00', i)
        meta = tree_data[i:end]
        mode, filename_bytes = meta.split(b" ", 1)
        sha = tree_data[end+1:end+21]
        hex_hash = sha.hex()
        i = end + 21
        # Recover blob and write file
        blob_path = f".pytrk/objects/{hex_hash[:2]}/{hex_hash[2:]}"
        with open(blob_path, "rb") as bf:
            blob_data = zlib.decompress(bf.read())
        blob_null = blob_data.index(b'\x00')
        content = blob_data[blob_null+1:]
        fname = filename_bytes.decode()
        # Ensure parent directory exists before writing file
        if os.path.dirname(fname):
            os.makedirs(os.path.dirname(fname), exist_ok=True)
        with open(fname, "wb") as outf:
            outf.write(content)
        print(f"Restored {fname} from blob {hex_hash}")


def status():
    """Show the status of files: staged, modified, deleted, untracked (respects .pytrkignore)."""
    patterns = load_ignore_patterns()
    try:
        with open(".pytrk/index.txt") as f:
            data = f.read().split("\n")
        current_files = set()
        staged = []
        modified = []
        untracked = []
        deleted = []
        for i in data:
            if i:
                i = i.split()
                file = i[1].lstrip("./")
                current_files.add(file)
                if os.path.exists(file):
                    with open(file,"rb") as f2:
                        file_data = f2.read()
                        header = f"blob {len(file_data)}\0".encode()
                        blob = header + file_data
                        hash_val = hashlib.sha1(blob).hexdigest()
                        if(hash_val == i[0]):
                            staged.append(file)
                        else:
                            modified.append(file)
                else:
                    deleted.append(file)
        for root, dirs, files in os.walk('.'):
            ignore_dirs = {".venv", ".pytrk", ".git", "__pycache__"}
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                f_path = os.path.join(root,file)
                rel_path = os.path.relpath(f_path).lstrip("./").replace("\\", "/")
                if rel_path not in current_files and not is_ignored(rel_path, patterns):
                    untracked.append(rel_path)
        if modified:
            print("\033[91mModified files:\033[0m")
            for file in modified:
                print(f"  {file}")
        if deleted:
            print("\033[95mDeleted files/Not in current Branch:\033[0m")
            for file in deleted:
                print(f"  {file}")
        if untracked:
            print("\033[93mUntracked files:\033[0m")
            for file in untracked:
                print(f"  {file}")
        if staged:
            print("\033[92mUnchanged (staged) files:\033[0m")
            for file in staged:
                print(f"  {file}")
    except Exception as e:
        print(f"Error during status: {e}")

def diff():
    """Show diffs between staged and working directory files."""
    try:
        with open(".pytrk/index.txt") as f:
            entries = f.read().split("\n")
        for entry in entries:
            if not entry.strip():
                continue
            hash_val, file = entry.split()
            if not os.path.exists(file):
                print(f"{file} has been deleted")
                continue
            # Read current working file
            with open(file, "rb") as f2:
                data2 = f2.read()
            header = f"blob {len(data2)}\0".encode()
            blob = header + data2
            working_hash = hashlib.sha1(blob).hexdigest()
            if hash_val != working_hash:
                # Read staged (index) version
                hash_path = f".pytrk/objects/{hash_val[:2]}/{hash_val[2:]}"
                with open(hash_path, "rb") as fh:
                    staged_data_compressed = fh.read()
                staged_data_decompressed = zlib.decompress(staged_data_compressed)
                staged_content = staged_data_decompressed.split(b'\x00', 1)[1].decode(errors='ignore').splitlines()

                # Read working version content
                working_content = data2.decode(errors='ignore').splitlines()

                # Generate diff
                diff_gen = difflib.unified_diff(
                    staged_content,
                    working_content,
                    fromfile=f"{file} (staged)",
                    tofile=f"{file} (working)",
                    lineterm=""
                )
                # Print diff
                print(f"\nChanges in {file}:")
                for line in diff_gen:
                    print(line)
    except Exception as e:
        print(f"Error during diff: {e}")

def branch(name):
    """Create a new branch at the current commit."""
    try:
        with open('.pytrk/HEAD') as f:
            head = f.read().strip()
        if not head.startswith("ref: "):
            print("HEAD is detached. Cannot create branch from a detached state.")
            return
        current_ref = head[5:]
        current_ref_path = f".pytrk/{current_ref}"
        if not os.path.exists(current_ref_path):
            print("Current branch has no commits yet. Commit something first.")
            return
        with open(current_ref_path) as f:
            commit_hash = f.read().strip()
        new_branch_path = f".pytrk/refs/heads/{name}"
        if os.path.exists(new_branch_path):
            print(f"Branch '{name}' already exists.")
            return
        os.makedirs(os.path.dirname(new_branch_path), exist_ok=True)
        with open(new_branch_path, "w") as f:
            f.write(commit_hash + "\n")
        print(f"Created branch '{name}' at {commit_hash}")
    except Exception as e:
        print(f"Error during branch creation: {e}")

def list_branches():
    """List all branches, marking the current one."""
    try:
        path = ".pytrk/refs/heads"
        branches = os.listdir(path)
        with open(".pytrk/HEAD") as f:
            data = f.read().strip()
        current_branch = data.split('/')[-1]
        for i in branches:
            if i == current_branch:
                print(f"{i} *") 
            else:
                print(i)
    except Exception as e:
        print(f"Error listing branches: {e}")

def merge(target_branch):
    """Fast-forward merge if possible, else detect conflicts (basic)."""
    try:
        with open(".pytrk/HEAD") as f:
            ref_path = f.read().strip()[5:]
        branch_ref = f".pytrk/{ref_path}"
        if not os.path.exists(branch_ref):
            print("Current branch ref not found.")
            return
        with open(branch_ref) as f:
            current_commit = f.read().strip()
        # Get target branch commit hash
        target_ref = f".pytrk/refs/heads/{target_branch}"
        if not os.path.exists(target_ref):
            print(f"Target branch '{target_branch}' does not exist.")
            return
        with open(target_ref) as f:
            target_commit = f.read().strip()
        # Walk the parent chain of the target branch
        hash_to_check = target_commit
        found = False
        while hash_to_check:
            if hash_to_check == current_commit:
                found = True
                break
            obj_path = f".pytrk/objects/{hash_to_check[:2]}/{hash_to_check[2:]}"
            if not os.path.exists(obj_path):
                break
            with open(obj_path, "rb") as f:
                data = zlib.decompress(f.read()).decode().splitlines()
            # Find parent
            parent_hash = None
            for line in data:
                if line.startswith("parent "):
                    parent_hash = line.split(" ", 1)[1]
                    break
            hash_to_check = parent_hash
        if found:
            print(f"Fast-forward merge possible. Updating branch to {target_commit}")
            with open(branch_ref, "w") as f:
                f.write(target_commit)
            checkout(target_commit)
        else:
            # Basic conflict detection: compare tree objects for both commits
            print(f"Cannot fast-forward: {target_branch} has diverged.")
            # Get tree hashes for both commits
            def get_tree_hash(commit_hash):
                obj_path = f".pytrk/objects/{commit_hash[:2]}/{commit_hash[2:]}"
                with open(obj_path, "rb") as f:
                    data = zlib.decompress(f.read())
                body = data[data.index(b'\x00')+1:].decode()
                lines = body.splitlines()
                if lines and lines[0].startswith("tree "):
                    return lines[0].split(" ")[1]
                return None
            tree1 = get_tree_hash(current_commit)
            tree2 = get_tree_hash(target_commit)
            # Parse tree objects into {filename: hash}
            def parse_tree(tree_hash):
                tree_path = f".pytrk/objects/{tree_hash[:2]}/{tree_hash[2:]}"
                with open(tree_path, "rb") as f:
                    tree_data = zlib.decompress(f.read())
                files = {}
                i = tree_data.index(b'\x00')+1
                while i < len(tree_data):
                    end = tree_data.index(b'\x00', i)
                    meta = tree_data[i:end]
                    mode, filename = meta.split(b" ", 1)
                    sha = tree_data[end+1:end+21]
                    files[filename.decode()] = sha.hex()
                    i = end + 21
                return files
            files1 = parse_tree(tree1) if tree1 else {}
            files2 = parse_tree(tree2) if tree2 else {}
            # Detect conflicts: file in both trees with different hashes
            for fname in files1:
                if fname in files2 and files1[fname] != files2[fname]:
                    print(f"Conflict: {fname} changed in both branches. Aborting merge.")
                    return
            print("No fast-forward possible, but no direct file conflicts detected (manual merge needed).")
    except Exception as e:
        print(f"Error during merge: {e}")