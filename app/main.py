import os
import sys
import hashlib
import zlib

def init():
    os.makedirs(".pytrk/objects",exist_ok=True)
    os.makedirs(".pytrk/refs/heads",exist_ok=True)
    with open(".pytrk/HEAD","w") as f:
        f.write("ref: refs/heads/main\n")
    print("initialiszed pytrk repo")


def hash_object(filename):
    with open(filename,"rb") as f:
        # print(f.read())
        data = f.read()
        data = f"blob {len(data)}\0".encode()+data
        hash_data = hashlib.sha1(data).hexdigest()
        data = zlib.compress(data)
        os.makedirs(f".pytrk/objects/{hash_data[:2]}",exist_ok=True)
        with open(f".pytrk/objects/{hash_data[:2]}/{hash_data[2:]}","wb") as f:
            f.write(data)       
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

def main():
    if len(sys.argv)<2:
        print("no command provided")
        return
    
    command = sys.argv[1]
    fname = sys.argv[2]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fpath = os.path.join(script_dir,fname)
    print(command,fname,fpath)
    if command == "init":
        init()
    elif command == "hash-object":
        hash_object(fpath)
    elif command == "cat-file":
        cat_file(fname)
    elif command == "add":
        add(fpath)
    else:
        print("unknown command")

if __name__=="__main__":
    main()
