import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.append(str(BASE_DIR))

try:
    from jarvis.orchestrator import Orchestrator
    from jarvis.config import OLLAMA_MODEL, GROQ_MODEL
    
    print(f"--- JARVIS Diagnostic ---")
    print(f"Ollama Model: {OLLAMA_MODEL}")
    print(f"Groq Model:   {GROQ_MODEL}")
    
    orch = Orchestrator()
    print(f"Loaded Tools: {list(orch._tools.keys())}")
    
    if 'messaging' in orch._tools:
        print("✓ Messaging tool registered successfully.")
    else:
        print("✗ Messaging tool NOT found.")
        
    if 'system_control' in orch._tools:
        sc = orch._tools['system_control']
        if hasattr(sc, '_open_url'):
            print("✓ System control has 'open_url' action.")
        else:
            print("✗ System control is missing 'open_url'.")
            
    print("------------------------")
    
except Exception as e:
    print(f"Diagnostic failed: {e}")
    import traceback
    traceback.print_exc()
