import sys
from . import core

def main():
    if len(sys.argv) < 2:
        print("Usage: pytrk <command> [<args>]")
        return

    command = sys.argv[1]

    if command == "init":
        core.init()
    elif command == "add":
        if len(sys.argv) < 3:
            print("Usage: pytrk add <file | .>")
            return
        core.add(sys.argv[2])
    elif command == "commit":
        if len(sys.argv) < 3:
            print("Usage: pytrk commit <message>")
            return
        core.commit(sys.argv[2])
    elif command == "log":
        core.log()
    elif command == "status":
        core.status()
    elif command == "diff":
        core.diff()
    elif command == "checkout":
        if len(sys.argv) < 3:
            print("Usage: pytrk checkout <branch | commit>")
            return
        core.checkout(sys.argv[2])
    elif command == "branch":
        if len(sys.argv) < 3:
            print("Usage: pytrk branch <name>")
            return
        core.branch(sys.argv[2])
    elif command == "list-branches":
        core.list_branches()
    elif command == "list-files":
        core.list_files()
    elif command == "merge":
        if len(sys.argv) < 3:
            print("Usage: pytrk merge <branch>")
            return
        core.merge(sys.argv[2])
    elif command == "cat-file":
        if len(sys.argv) < 3:
            print("Usage: pytrk cat-file <hash>")
            return
        core.cat_file(sys.argv[2])
    elif command == "hash-object":
        if len(sys.argv) < 3:
            print("Usage: pytrk hash-object <file>")
            return
        core.hash_object(sys.argv[2])
    elif command == "write-tree":
        core.write_tree()
    elif command == "help":
        print("""
pytrk commands:
  init                Initialize a new repository
  add <file|.>        Add file(s) to the index (staging area)
  commit <msg>        Commit staged changes with a message
  status              Show status of working directory and index
  diff                Show differences between index and working directory
  log                 Show commit history
  checkout <branch|commit>  Switch to branch or commit
  branch <name>       Create a new branch
  list-branches       List all branches
  list-files          List files in the latest commit
  merge <branch>      Merge branch into current branch (fast-forward or detect conflict)
  cat-file <hash>     Show contents of a blob object
  hash-object <file>  Hash and store a file as a blob
  write-tree          Write the current index as a tree object
  help                Show this help message
""")
    else:
        print(f"Unknown command: {command}")
        print("Use 'pytrk help' to see available commands.")