import os
import shutil
from pathlib import Path
import re

base_dir = Path(__file__).parent.resolve()
jarvis_dir = base_dir / "jarvis"

# 1. Create jarvis directory
jarvis_dir.mkdir(exist_ok=True)
(jarvis_dir / "__init__.py").touch(exist_ok=True)

# 2. Files to move
files_to_move = [
    "brain.py",
    "config.py",
    "hud.py",
    "memory.py",
    "orchestrator.py",
    "vision.py",
    "voice_in.py",
    "voice_out.py",
    "web_hud.py",
]

for f in files_to_move:
    src = base_dir / f
    if src.exists():
        dst = jarvis_dir / f
        shutil.move(str(src), str(dst))

# Move tools dir
tools_src = base_dir / "tools"
if tools_src.exists():
    tools_dst = jarvis_dir / "tools"
    # remove dst if exists to avoid shutil.move error
    if tools_dst.exists():
        shutil.rmtree(str(tools_dst))
    shutil.move(str(tools_src), str(tools_dst))

print("Files moved to jarvis/ successfully.")

# 3. Update imports in jarvis/ files
for root, _, files in os.walk(str(jarvis_dir)):
    for file in files:
        if file.endswith(".py"):
            filepath = Path(root) / file
            content = filepath.read_text(encoding="utf-8")
            
            # Replace 'from config import' with 'from jarvis.config import'
            content = re.sub(r"^from config import", "from jarvis.config import", content, flags=re.MULTILINE)
            content = re.sub(r"^import config", "import jarvis.config", content, flags=re.MULTILINE)
            
            # Replace 'from tools.' with 'from jarvis.tools.'
            content = re.sub(r"^from tools\.", "from jarvis.tools.", content, flags=re.MULTILINE)
            content = re.sub(r"^import tools\.", "import jarvis.tools.", content, flags=re.MULTILINE)
            
            filepath.write_text(content, encoding="utf-8")

# 4. Update main.py
main_py = base_dir / "main.py"
if main_py.exists():
    content = main_py.read_text(encoding="utf-8")
    content = re.sub(r"^from config import", "from jarvis.config import", content, flags=re.MULTILINE)
    content = re.sub(r"^from memory import", "from jarvis.memory import", content, flags=re.MULTILINE)
    content = re.sub(r"^from brain import", "from jarvis.brain import", content, flags=re.MULTILINE)
    content = re.sub(r"^from voice_out import", "from jarvis.voice_out import", content, flags=re.MULTILINE)
    content = re.sub(r"^from orchestrator import", "from jarvis.orchestrator import", content, flags=re.MULTILINE)
    content = re.sub(r"^from voice_in import", "from jarvis.voice_in import", content, flags=re.MULTILINE)
    content = re.sub(r"^from vision import", "from jarvis.vision import", content, flags=re.MULTILINE)
    content = re.sub(r"^from hud import", "from jarvis.hud import", content, flags=re.MULTILINE)
    content = re.sub(r"^from web_hud import", "from jarvis.web_hud import", content, flags=re.MULTILINE)
    main_py.write_text(content, encoding="utf-8")

# 5. Fix BASE_DIR in config.py
config_py = jarvis_dir / "config.py"
if config_py.exists():
    content = config_py.read_text(encoding="utf-8")
    # Change BASE_DIR to point to parent of jarvis folder
    content = content.replace('BASE_DIR = Path(__file__).parent.resolve()', 'BASE_DIR = Path(__file__).parent.parent.resolve()')
    config_py.write_text(content, encoding="utf-8")

print("Imports updated successfully.")
print("Repository restructuring complete!")
