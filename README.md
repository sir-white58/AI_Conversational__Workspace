# AI Conversational Workspace

A desktop app (Python + Tkinter) where you chat with Google Gemini and keep
conversations organised in named workspaces. Group 24, Python Advanced, Cohort 38.

## Features
- Workspaces: create, rename (and change mode), delete
- Conversations: create, rename, delete; earlier messages are sent for context
- AI modes per workspace: General Assistant, Tutor, Coding Helper, Writing Assistant
- Everything saved to JSON after each exchange and reloaded on start
- Search a word across a workspace; export a conversation to .txt
- Clear error messages (empty message, no internet, bad API key, damaged file)

## Setup
1. Install Python 3.10+.
2. Get a free key at https://aistudio.google.com/apikey
3. Copy `.env.example` to `.env` and paste your key (never commit `.env`).
4. Run from the project folder: `python main.py`
5. Tests: `python -m unittest discover tests`

## Structure
| Path | Purpose |
|---|---|
| `main.py` | Starts the app |
| `models/` | Message, Conversation, Workspace (OOP) |
| `data/data_manager.py` | Save, load, export files (file handling) |
| `api/ai_service.py` | Gemini API + custom exceptions (external API, exceptions) |
| `gui/` | main_window, sidebar, chat_panel, dialogs (Tkinter) |
| `tests/` | Unit tests |

## Team roles and branches
| Member | Branch | Responsible for |
|---|---|---|
| Leader (Olugboye Isaac) | `leader` | `models/`, `main.py`, `gui/main_window.py`, README, merging |
| Olajide Ajao | `data-manager` | `data/data_manager.py`, export, tests for file handling |
| Muhammad Umar | `ai-service` | `api/ai_service.py`, modes, error handling, tests for API code |
| Reuben Salama | `gui-theme` |
| Chinmdindu Igwe | `tests` |
See `GIT_WORKFLOW.md` for how we use Git.
