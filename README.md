# pytrk - A Minimal Version Control System (Like Git, but Simpler)

**pytrk** is a lightweight, educational version control system written in Python — built from scratch to help understand how Git works under the hood.

Inspired by the internals of Git, `pytrk` provides core version control features such as commits, branches, diffs, logs, and checkouts, using a custom object database and reference system.

This is a side project I built to deeply understand how Git works internally. If you're interested in learning how Git functions under the hood, Check out my blog: https://gitinternals.hashnode.dev/how-does-git-work-internally — it will walk you through the codebase and help you build something like this yourself.

---

## 🔧 Features

- `init`: Initialize a new pytrk repository
- `add <file|.>`: Stage files for commit
- `commit <message>`: Save a snapshot of staged files
- `status`: Show changes in working directory
- `diff`: View changes not yet committed
- `log`: View commit history
- `checkout <branch|commit>`: Switch versions
- `branch <name>`: Create a new branch
- `list-branches`: List all branches
- `list-files`: View files in the latest commit
- `merge <branch>`: Merge a branch into the current one
- `hash-object <file>`: Hash and store a file as a blob
- `cat-file <hash>`: Show contents of a blob object
- `write-tree`: Write the current index as a tree

---

## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/your-username/pytrk.git
cd pytrk
```
Install it locally:
`pip install .`

or run it directly:
`./pytrk <command>`



