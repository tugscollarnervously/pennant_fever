# Project Setup Troubleshooting Guide

Reference guide for setting up new projects in the `_code` directory structure with shared virtual environment and cross-platform data paths.

---

## Problem Symptoms

When starting a new project or returning to an existing one, you may encounter:

1. **IDE shows modules not installed** - VS Code/PyCharm shows red squiggles under `import pandas`, `import pygame`, etc., even though they're installed
2. **Cannot resolve imports** - `from data_paths_pennant_fever import *` or `from common_logger import setup_logger` fails
3. **Terminal import errors** - Running `python3 -c "import pygame"` returns `ModuleNotFoundError`
4. **Hardcoded paths breaking** - Old paths like `/Users/vadim/Documents/Code/_pennant_race/` or `C:\Users\...` no longer exist

---

## Root Causes

### 1. Missing VS Code Settings
Each project needs a `.vscode/settings.json` file that points to the shared virtual environment and adds the `common` folder to the Python analysis path.

### 2. Wrong Python Interpreter
The system Python (`python3`) doesn't have your packages. The shared `.venv` at the `_code` level does.

### 3. Hardcoded Paths
Old code may have absolute paths to folders that no longer exist or use different usernames/OS paths.

---

## Architecture Overview

```
/Users/sputnik69/Documents/_code/
├── .venv/                      # SHARED virtual environment (all packages here)
├── common/                     # Shared modules for all projects
│   ├── common_logger.py
│   ├── data_paths_common.py    # Cross-platform OneDrive detection
│   ├── data_paths_football_game.py
│   ├── data_paths_pennant_fever.py
│   └── ...
├── football_game/              # Project folder
│   └── .vscode/settings.json   # Points to ../.venv
├── pennant_fever/              # Project folder
│   └── .vscode/settings.json   # Points to ../.venv
└── the_chase/                  # Project folder
    └── .vscode/settings.json   # Points to ../.venv
```

### OneDrive Data Structure
```
~/OneDrive/                     # Symlink to ~/Library/CloudStorage/OneDrive-Personal
├── BaseballProjects/
│   └── pennant_fever/
│       ├── game_data/
│       ├── game_json/
│       └── ...
├── FootballProjects/
│   └── football_game/
│       └── ...
└── GenerativeProjects/         # SHARED across all game projects
    ├── names/                  # Player name files
    ├── corp_names/             # Corporate name generation
    └── machine_learning/       # ML model artifacts
```

---

## Fix: Step-by-Step

### Step 1: Create VS Code Settings

Create `.vscode/settings.json` in your project folder:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/../.venv/bin/python",
  "python.terminal.activateEnvironment": true,

  "python.analysis.extraPaths": ["${workspaceFolder}/../common"],
  "python.createEnvironment.trigger": "off",

  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.useLibraryCodeForTypes": true,
  "python.analysis.inlayHints.functionReturnTypes": true,
  "python.analysis.inlayHints.variableTypes": true,

  "terminal.integrated.defaultProfile.osx": "bash",
  "files.exclude": { "**/__pycache__": true },
  "terminal.integrated.allowChords": false
}
```

**Key settings explained:**
- `python.defaultInterpreterPath`: Points to shared `.venv` one level up
- `python.analysis.extraPaths`: Tells Pylance where to find `common` modules

### Step 2: Reload VS Code

After creating the settings file:
- Close and reopen the project folder, OR
- `Cmd+Shift+P` → "Developer: Reload Window"

### Step 3: Verify Interpreter

Check the Python interpreter is correct:
- Look at the bottom-right of VS Code - should show `.venv` path
- If not: `Cmd+Shift+P` → "Python: Select Interpreter" → choose `../.venv`

### Step 4: Terminal Activation

When opening a new terminal in VS Code, it should auto-activate the venv. If not:

```bash
source /Users/sputnik69/Documents/_code/.venv/bin/activate
```

---

## Fix: Data Paths Setup

### Pattern for New Projects

1. **Create a data_paths file** in `common/`:

```python
# common/data_paths_YOURPROJECT.py

from pathlib import Path
from data_paths_common import ONEDRIVE_BASE, LOG_TIMESTAMP

# Project-specific base
YOURPROJECT_BASE = ONEDRIVE_BASE / "YourProjectsFolder"
YOURPROJECT_DIR = YOURPROJECT_BASE / "your_project"

# Shared resources (GenerativeProjects)
GENERATIVE_BASE = ONEDRIVE_BASE / "GenerativeProjects"
GENERATIVE_NAMES_DIR = GENERATIVE_BASE / "names"
CORP_NAMES_DIR = GENERATIVE_BASE / "corp_names"
MACHINE_LEARNING_DIR = GENERATIVE_BASE / "machine_learning"

# Project-specific folders
YOURPROJECT_DATA_DIR = YOURPROJECT_DIR / "game_data"
YOURPROJECT_LOGS_DIR = YOURPROJECT_DIR / "logs"
# ... etc
```

2. **Import in your main code**:

```python
import sys
from pathlib import Path

# Add common folder to sys.path for shared modules
COMMON_PATH = Path.home() / "Documents/_code/common"
sys.path.insert(0, str(COMMON_PATH))

from data_paths_yourproject import *
from common_logger import setup_logger
```

### Cross-Platform Path Resolution

The `data_paths_common.py` handles Windows vs macOS automatically:

```python
def get_onedrive_path():
    system = platform.system()
    home = Path.home()
    if system == "Windows":
        return Path(os.environ.get("OneDrive", home / "OneDrive"))
    elif system == "Darwin":  # macOS
        return home / "OneDrive"  # Symlink to CloudStorage location
```

**Important:** On macOS, create a symlink for cleaner paths:
```bash
ln -s ~/Library/CloudStorage/OneDrive-Personal ~/OneDrive
```

---

## Verification Commands

### Check shared venv exists and has packages:
```bash
ls -la /Users/sputnik69/Documents/_code/.venv/bin/python
/Users/sputnik69/Documents/_code/.venv/bin/python -c "import pygame; print('OK')"
/Users/sputnik69/Documents/_code/.venv/bin/python -c "import pandas; print('OK')"
```

### Test imports from a project:
```bash
/Users/sputnik69/Documents/_code/.venv/bin/python -c "
import sys
sys.path.insert(0, '/Users/sputnik69/Documents/_code/common')
from data_paths_pennant_fever import PENNANT_FEVER_DIR
print(f'Path: {PENNANT_FEVER_DIR}')
print(f'Exists: {PENNANT_FEVER_DIR.exists()}')
"
```

### Check VS Code settings exist:
```bash
cat /Users/sputnik69/Documents/_code/YOUR_PROJECT/.vscode/settings.json
```

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: pygame` | Wrong Python interpreter | Select `.venv` interpreter in VS Code |
| `cannot import data_paths_*` | Missing `sys.path` setup | Add `COMMON_PATH` to `sys.path` at top of file |
| Pylance red squiggles | Missing `extraPaths` | Add `../common` to `python.analysis.extraPaths` |
| `FileNotFoundError` for data files | Hardcoded old paths | Use centralized `data_paths_*.py` constants |
| Path works on Mac but not Windows | Hardcoded OS-specific path | Use `data_paths_common.py` cross-platform detection |

---

## Files Modified for pennant_fever Fix

1. **Created:** `/pennant_fever/.vscode/settings.json`
2. **Updated:** `/common/data_paths_pennant_fever.py`
   - Changed `CORP_NAMES_DIR` → `GenerativeProjects/corp_names`
   - Changed `MACHINE_LEARNING_DIR` → `GenerativeProjects/machine_learning`
   - Changed `FIRST_NAMES_FILE` → `GenerativeProjects/names/first_names_weighted_baseball.xlsx`
   - Changed `SURNAMES_FILE` → `GenerativeProjects/names/surnames_weighted_master.xlsx`
   - Fixed `SCHOOLS_REGISTER_FILE` → `game_data/schools/schools_register.xlsx`
3. **Updated:** `/pennant_fever/pennant_fever_game.py`
   - Removed hardcoded `BASE_DIRECTORY`
   - Uses centralized paths
4. **Updated:** `/pennant_fever/pennant_fever_generator.py`
   - Added `sys.path` setup and centralized imports
   - Replaced all hardcoded Windows paths

---

*Document created: 2024-12-21*
