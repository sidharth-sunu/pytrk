import os
import sys
import hashlib
import zlib
import time 

def init():
    os.makedirs(".pytrk/objects",exist_ok=True)
    os.makedirs(".pytrk/refs/heads",exist_ok=True)
    with open(".pytrk/HEAD","w") as f:
        f.write("ref: refs/heads/main\n")
    print("initialiszed pytrk repo")

def hash_dir_create(data):
    hash_data = hashlib.sha1(data).hexdigest()
    data = zlib.compress(data)
    os.makedirs(f".pytrk/objects/{hash_data[:2]}",exist_ok=True)
    with open(f".pytrk/objects/{hash_data[:2]}/{hash_data[2:]}","wb") as f:
        f.write(data)       
    return(hash_data) 

def hash_object(filename):
    with open(filename,"rb") as f:
        # print(f.read())
        data = f.read()
        data = f"blob {len(data)}\0".encode()+data
        hash_data = hash_dir_create(data)     
    return(hash_data) 

def cat_file(hash_data):
    with open(f".pytrk/objects/{hash_data[:2]}/{hash_data[2:]}","rb") as f:
        data = f.read()
        data = zlib.decompress(data)
        idx = data.index(b"\x00")
        print(data[idx+1:].decode())

def add(filename):
    hash = hash_object(filename)
    with open(".pytrk/index.txt","a") as f:
        data = f"{hash} {filename}\n"
        f.write(data)
    print("added file to index")

def write_tree():
    entries = []
    with open(".pytrk/index.txt") as f:
        data = f.read().split('\n')
        for line in data:
            if len(line)>1:
                line = line.split(' ',1)
                entry = f"100644 {line[1]}".encode()+b"\x00"+bytes.fromhex(line[0])
                entries.append(entry)
    tree_content = b"".join(entries)
    header = f"tree {len(tree_content)}\x00".encode()
    tree_content = header+tree_content
    hash_data = hash_dir_create(tree_content)
    return(hash_data)

def commit(message):
    tree_hash = write_tree()
    timestamp = int(time.time())
    with open(".pytrk/HEAD") as f:
        ref = f.read().strip().split(" ")[1]
    ref_path = os.path.join(".pytrk",ref)
    print(ref_path)
    parent = None
    if os.path.exists(ref_path):
        with open(ref_path) as f:
            parent = f.read().strip()
            print(parent)
    lines = [
        f"tree {tree_hash}",
    ]
    if parent:
        lines.append(f"parent {parent}")
    lines.extend([
        f"author Sidh <you@example.com> {timestamp}",
        f"committer Sidh <you@example.com> {timestamp}",
        "",
        message
    ])
    commit_body = "\n".join(lines).encode()
    header = f"commit {len(commit_body)}\x00".encode()
    commit_data = header+commit_body
    commit_hash = hash_dir_create(commit_data)
    print(f"committed: {commit_hash}")

    with open(f".pytrk/{ref}","w") as f:
        f.write(commit_hash+"\n")

def log():
    with open(".pytrk/HEAD") as f:
        ref = f.read().strip().split(" ")[1]
    ref_path = os.path.join(".pytrk",ref)
    with open(ref_path) as f:
        current_hash = f.read().strip()
        print(current_hash)
    while current_hash:
        path = f".pytrk/objects/{current_hash[:2]}/{current_hash[2:]}"
        with open(path,"rb") as f:
            raw = f.read()
        decompressed  = zlib.decompress(raw)
        null_index = decompressed.index(b'\x00')
        commit_txt = decompressed[null_index+1:].decode()
        lines = commit_txt.split("\n")
        tree = ""
        parent = None
        author = ""
        messages = []
        reading_msgs = False
        for line in lines:
            line = line.strip()
            if reading_msgs:
                messages.append(line)
            elif line.startswith("tree "):
                tree = line[5:]
            elif line.startswith("parent "):
                parent = line[7:]
            elif line.startswith("author "):
                author = line
            elif line == "":
                reading_msgs = True
        print(f"commit {current_hash}")
        print(author)
        print()
        for line in messages:
            print(f"    {line}")
        print()
        if parent:
            current_hash = parent
        else:
            break


def main():
    if len(sys.argv)<2:
        print("no command provided")
        return
    
    command = sys.argv[1]
    if command == "init":
        init()
    elif command == "hash-object":
        fname = sys.argv[2]
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fpath = os.path.join(script_dir,fname)
        hash_object(fpath)
    elif command == "cat-file":
        fname = sys.argv[2]
        cat_file(fname)
    elif command == "add":
        fname = sys.argv[2]
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fpath = os.path.join(script_dir,fname)
        add(fpath)
    elif command == "write-tree":
        write_tree()
    elif command == "commit":
        message = sys.argv[2]
        commit(message)
    elif command == "log":
        log()
    else:
        print("unknown command")

if __name__=="__main__":
    main()
