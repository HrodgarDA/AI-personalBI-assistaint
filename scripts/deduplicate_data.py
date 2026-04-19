import os
import json
import csv
from pathlib import Path

DATA_DIR = "data"
BRONZE_RAW = os.path.join(DATA_DIR, "bronze_raw_data.jsonl")
SILVER_FILE = os.path.join(DATA_DIR, "silver_expenses.jsonl")
GOLD_FILE = os.path.join(DATA_DIR, "gold_certified_data.csv")

def deduplicate_jsonl(filepath, signature_keys):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []
    
    seen = {} # signature -> record
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
                # Normalize values for signature
                sig = tuple(str(record.get(k, "")).strip() for k in signature_keys)
                
                if sig not in seen:
                    seen[sig] = record
                else:
                    # If duplicate, keep the one with more information (e.g. higher confidence)
                    existing = seen[sig]
                    new_conf = float(record.get("confidence", 0))
                    old_conf = float(existing.get("confidence", 0))
                    if new_conf > old_conf:
                        seen[sig] = record
            except Exception as e:
                print(f"Error parsing line in {filepath}: {e}")
                
    return list(seen.values())

def run():
    print("🚀 Starting Deduplication...")
    
    # 1. Deduplicate Bronze
    # Bronze keys: date, operation, details, amount
    bronze_records = deduplicate_jsonl(BRONZE_RAW, ["date", "operation", "details", "amount"])
    print(f"✅ Bronze cleaned: {len(bronze_records)} records remaining.")
    
    # 2. Deduplicate Silver
    # Silver keys: date, original_operation, original_details, amount
    silver_records = deduplicate_jsonl(SILVER_FILE, ["date", "original_operation", "original_details", "amount"])
    print(f"✅ Silver cleaned: {len(silver_records)} records remaining.")
    
    # 3. Write back
    with open(BRONZE_RAW, "w", encoding="utf-8") as f:
        for r in bronze_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    with open(SILVER_FILE, "w", encoding="utf-8") as f:
        for r in silver_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
def run_standalone_certify():
    """Simplified version of run_certify to regenerate CSV without external dependencies."""
    print("🏅 Regenerating Gold CSV...")
    if not os.path.exists(SILVER_FILE):
        print("Silver file missing.")
        return

    records = []
    with open(SILVER_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except Exception: continue

    if not records:
        print("No records to certify.")
        return

    # Basic normalization
    for r in records:
        if "time" not in r or not r["time"]:
            r["time"] = "00:00"
        
        tip = r.get("tipology", "").lower()
        if tip in ["expense", "refund"]:
            r["tipology"] = "Outgoing"
        elif tip == "salary":
            r["tipology"] = "Incoming"

    records.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))

    # Export to CSV
    fieldnames = sorted({key for record in records for key in record.keys()})
    with open(GOLD_FILE, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({k: record.get(k, "") for k in fieldnames})
    print(f"✅ CSV Generated: {GOLD_FILE} ({len(records)} rows)")

def run():
    print("🚀 Starting Deduplication...")
    
    # 1. Deduplicate Bronze
    bronze_records = deduplicate_jsonl(BRONZE_RAW, ["date", "operation", "details", "amount"])
    print(f"✅ Bronze cleaned: {len(bronze_records)} records remaining.")
    
    # 2. Deduplicate Silver
    silver_records = deduplicate_jsonl(SILVER_FILE, ["date", "original_operation", "original_details", "amount"])
    print(f"✅ Silver cleaned: {len(silver_records)} records remaining.")
    
    # 3. Write back
    with open(BRONZE_RAW, "w", encoding="utf-8") as f:
        for r in bronze_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    with open(SILVER_FILE, "w", encoding="utf-8") as f:
        for r in silver_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    print("💾 Files saved. Now regenerating Gold CSV...")
    
    # 4. Standalone certify
    run_standalone_certify()
    
    print("✨ Deduplication complete!")

if __name__ == "__main__":
    run()
