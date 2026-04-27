import psutil
import os
import math

def get_recommended_concurrency():
    """
    Evaluates system hardware and returns recommended Celery concurrency.
    Logic:
    - 1 worker per 4GB of RAM
    - Max 1 worker per 2 CPU cores (to leave room for the LLM)
    - Minimum 1
    """
    total_ram_gb = psutil.virtual_memory().total / (1024**3)
    cpu_cores = os.cpu_count() or 1
    
    ram_based = math.floor(total_ram_gb / 4)
    cpu_based = math.floor(cpu_cores / 2)
    
    recommended = max(1, min(ram_based, cpu_based))
    
    # Caps for local LLM usage
    # If the user has a massive rig, we still don't want to choke Ollama
    recommended = min(recommended, 4) 
    
    print(f"--- Hardware Check ---")
    print(f"Total RAM: {total_ram_gb:.2f} GB")
    print(f"CPU Cores: {cpu_cores}")
    print(f"Recommended Celery Concurrency: {recommended}")
    print(f"-----------------------")
    
    return recommended

if __name__ == "__main__":
    print(get_recommended_concurrency())
