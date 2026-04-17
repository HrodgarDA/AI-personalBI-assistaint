import subprocess
import logging
from typing import List

logger = logging.getLogger(__name__)

def get_installed_models() -> List[str]:
    """Returns a list of names of models installed in Ollama."""
    try:
        # Detect ollama binary path
        possible_paths = ["ollama", "/usr/local/bin/ollama", "/opt/homebrew/bin/ollama", "/usr/bin/ollama"]
        ollama_bin = "ollama"
        for path in possible_paths:
            try:
                subprocess.run([path, "list"], capture_output=True, text=True, timeout=2)
                ollama_bin = path
                break
            except (subprocess.SubprocessError, FileNotFoundError):
                continue

        result = subprocess.run([ollama_bin, "list"], capture_output=True, text=True)
        if result.returncode != 0:
            return []
        
        # Parse output: skip header, extract first column
        lines = result.stdout.strip().split("\n")
        if len(lines) <= 1:
            return []
            
        models = []
        for line in lines[1:]: # skip header
            cols = line.split()
            if cols:
                models.append(cols[0])
        return models
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return []

def sync_ollama_models(required_models: List[str]):
    """
    Pulls missing models and removes unused ones.
    'required_models' is a list of model names or IDs.
    """
    if not required_models:
        return

    # Normalize required models (remove :latest if present for easier matching)
    required_norm = {m.split(":")[0]: m for m in required_models if m}
    
    current_models = get_installed_models()
    # current_norm maps normalized_name -> actual_name_in_list
    current_norm = {m.split(":")[0]: m for m in current_models}

    # 1. Pull missing
    possible_paths = ["ollama", "/usr/local/bin/ollama", "/opt/homebrew/bin/ollama", "/usr/bin/ollama"]
    ollama_bin = "ollama"
    for path in possible_paths:
        try:
            subprocess.run([path, "list"], capture_output=True, text=True, timeout=2)
            ollama_bin = path
            break
        except (subprocess.SubprocessError, FileNotFoundError):
            continue

    for norm_name, full_name in required_norm.items():
        if norm_name not in current_norm:
            logger.info(f"Pulling missing model: {full_name}")
            try:
                subprocess.run([ollama_bin, "pull", full_name], check=True)
            except Exception as e:
                logger.error(f"Failed to pull {full_name}: {e}")

    # 2. Clean unused
    for norm_name, full_name in current_norm.items():
        if norm_name not in required_norm:
            logger.info(f"Removing unused model: {full_name}")
            try:
                subprocess.run([ollama_bin, "rm", full_name], check=True)
            except Exception as e:
                logger.error(f"Failed to remove {full_name}: {e}")
