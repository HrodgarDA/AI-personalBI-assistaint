import argparse
import logging
from auto_bi.core.process import run_processing, run_certify

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

def main_cli():
    parser = argparse.ArgumentParser(description="AI-BI Expense ETL CLI")
    parser.add_argument("--process", action="store_true", help="Categorizza le transazioni tramite AI")
    parser.add_argument("--certify", action="store_true", help="Esporta i dati certificati in formato CSV")
    parser.add_argument("--batch", type=int, default=5, help="Dimensione batch processing")
    
    args = parser.parse_args()

    if not any([args.process, args.certify]):
        parser.print_help()
    else:
        if args.process:
            run_processing(batch_size=args.batch)
        if args.certify:
            run_certify()

# --- CLI ENTRY POINT ---
if __name__ == "__main__":
    main_cli()