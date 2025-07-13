import os
import sys
import hashlib
import zlib
import time
import difflib

def init():
    os.makedirs(".pytrk/objects", exist_ok=True)
    os.makedirs(".pytrk/refs/heads", exist_ok=True)
    with open(".pytrk/HEAD", "w") as f:
        f.write("ref: refs/heads/main\n")
    print("initialized pytrk repo")

def hash_dir_create(data):
    hash_data = hashlib.sha1(data).hexdigest()
    data = zlib.compress(data)
    obj_dir = f".pytrk/objects/{hash_data[:2]}"
    os.makedirs(obj_dir, exist_ok=True)
    with open(f"{obj_dir}/{hash_data[2:]}", "wb") as f:
        f.write(data)
    return hash_data

def hash_object(filename):
    with open(filename, "rb") as f:
        data = f.read()
    header = f"blob {len(data)}\0".encode()
    blob = header + data
    return hash_dir_create(blob)

def cat_file(hash_data):
    path = f".pytrk/objects/{hash_data[:2]}/{hash_data[2:]}"
    with open(path, "rb") as f:
        data = zlib.decompress(f.read())
    content = data[data.index(b'\x00')+1:]
    print(content.decode())

def add(filename):
    hash = hash_object(filename)
    rel_path = os.path.relpath(filename).lstrip("./")
    # Avoid duplicate entries
    if os.path.exists(".pytrk/index.txt"):
        with open(".pytrk/index.txt") as f:
            if any(line.strip().endswith(f" {rel_path}") for line in f):
                print(f"{rel_path} already added.")
                return

    with open(".pytrk/index.txt", "a") as f:
        f.write(f"{hash} {rel_path}\n")
    print(f"added {rel_path} to index")

def write_tree():
    entries = []
    with open(".pytrk/index.txt") as f:
        for line in f:
            if line.strip():
                hash, path = line.strip().split(" ", 1)
                entry = f"100644 {path}".encode() + b"\x00" + bytes.fromhex(hash)
                entries.append(entry)
    tree_content = b"".join(entries)
    tree_header = f"tree {len(tree_content)}\0".encode()
    tree = tree_header + tree_content
    return hash_dir_create(tree)

def commit(message):
    tree_hash = write_tree()
    timestamp = int(time.time())
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
        f"author Sidh <you@example.com> {timestamp}",
        f"committer Sidh <you@example.com> {timestamp}",
        "",
        message
    ]

    body = "\n".join(lines).encode()
    commit = f"commit {len(body)}\0".encode() + body
    commit_hash = hash_dir_create(commit)
    with open(ref_path, "w") as f:
        f.write(commit_hash + "\n")
    print(f"committed: {commit_hash}")

def log():
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

def checkout(name):
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
        mode, filename = meta.split(b" ", 1)
        sha = tree_data[end+1:end+21]
        hex_hash = sha.hex()
        i = end + 21

        # Recover blob and write file
        blob_path = f".pytrk/objects/{hex_hash[:2]}/{hex_hash[2:]}"
        with open(blob_path, "rb") as bf:
            blob_data = zlib.decompress(bf.read())
        blob_null = blob_data.index(b'\x00')
        content = blob_data[blob_null+1:]

        fname = filename.decode()
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        with open(fname, "wb") as outf:
            outf.write(content)
        print(f"Restored {fname} from blob {hex_hash}")

def status():
    with open(".pytrk/index.txt") as f:
        data = f.read()
        data = data.split("\n")
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
                        data = f2.read()
                        header = f"blob {len(data)}\0".encode()
                        blob = header + data
                        hash = hashlib.sha1(blob).hexdigest()
                        if(hash == i[0]):
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
            rel_path = os.path.relpath(f_path).lstrip("./")
            if(rel_path not in current_files):
                untracked.append(rel_path)
    if modified:
        print("\033[91mModified files:\033[0m")
        for file in modified:
            print(f"  {file}")

    if deleted:
        print("\033[95mDeleted files:\033[0m")
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

def diff():
    with open(".pytrk/index.txt") as f:
        entries = f.read().split("\n")

    for entry in entries:
        if not entry.strip():
            continue
        hash, file = entry.split()
        
        if not os.path.exists(file):
            print(f"{file} has been deleted")
            continue

        # Read current working file
        with open(file, "rb") as f2:
            data2 = f2.read()
        header = f"blob {len(data2)}\0".encode()
        blob = header + data2
        working_hash = hashlib.sha1(blob).hexdigest()

        if hash != working_hash:
            # Read staged (index) version
            hash_path = f".pytrk/objects/{hash[:2]}/{hash[2:]}"
            with open(hash_path, "rb") as fh:
                staged_data = zlib.decompress(fh.read()).decode()
            staged_content = staged_data.split('\x00', 1)[1].splitlines()

            # Read working version
            working_content = blob.decode().split('\x00', 1)[1].splitlines()

            # Generate diff
            diff = difflib.unified_diff(
                staged_content,
                working_content,
                fromfile=f"{file} (staged)",
                tofile=f"{file} (working)",
                lineterm=""
            )

            # Print diff
            print(f"\nChanges in {file}:")
            for line in diff:
                print(line)

def branch(name):
    # Read HEAD to get current branch
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

    with open(new_branch_path, "w") as f:
        f.write(commit_hash + "\n")

    print(f"Created branch '{name}' at {commit_hash}")

def list_branches():
    path = ".pytrk/refs/heads"
    branches = os.listdir(path)
    with open(".pytrk/HEAD") as f:
        data = f.read().strip()
    current_branch = data[16:]
    for i in branches:
        if i == current_branch:
            print(f"{i} *") 
        else:
            print(i)
                    
def main():
    if len(sys.argv) < 2:
        print("No command provided")
        return

    command = sys.argv[1]
    if command == "init":
        init()
    elif command == "hash-object":
        fname = sys.argv[2]
        fpath = os.path.join(os.getcwd(), fname)
        hash_object(fpath)
    elif command == "cat-file":
        fname = sys.argv[2]
        cat_file(fname)
    elif command == "add":
        fname = sys.argv[2]
        fpath = os.path.join(os.getcwd(), fname)
        add(fpath)
    elif command == "write-tree":
        write_tree()
    elif command == "commit":
        commit(sys.argv[2])
    elif command == "log":
        log()
    elif command == "checkout":
        checkout(sys.argv[2])
    elif command == "status":
        status()
    elif command == "diff":
        diff()
    elif command == "branch":
        name = sys.argv[2]
        branch(name)
    elif command == "list-branches":
        list_branches()
    else:
        print("Unknown command")

if __name__ == "__main__":
    main()
