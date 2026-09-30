# Git and GitHub workflow

## Rules
1. The leader owns the repository and has invited everyone as collaborators.
2. Nobody commits directly to `main`. Everyone works on their own branch.
3. Work reaches `main` only through a Pull Request reviewed by another member.
4. Commit often with clear messages (e.g. "Add search to Workspace").

## First-time setup (each member)
    git clone https://github.com/sir-white58/AI_Conversational_Workspace.git
    cd AI_Conversational_Workspace
    git checkout -b your-branch-name
    git push -u origin your-branch-name

## Daily routine
    git pull origin main          # get the latest team work
    # ... edit your own files ...
    git add .
    git commit -m "Describe what you did"
    git push

## Merging your work
1. On GitHub open a Pull Request: your branch -> `main`.
2. A teammate reviews it and clicks Merge.
3. Everyone runs `git pull origin main` to update.

## Avoiding conflicts
Only edit the files you own (see README roles). If you must change someone
else's file, tell them first. Never commit `.env` or `data/saved/`.
