import argparse
import logging
from auto_bi.core.ingestion import run_ingestion
from auto_bi.core.process import run_processing, run_excel_processing, run_certify

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

def main_cli():
    parser = argparse.ArgumentParser(description="AI-BI Expense ETL CLI")
    parser.add_argument("--ingest", action="store_true", help="Esegue lo scaricamento da Gmail")
    parser.add_argument("--process", action="store_true", help="Esegue il parsing LLM email")
    parser.add_argument("--process-excel", action="store_true", help="Esegue il parsing LLM excel")
    parser.add_argument("--certify", action="store_true", help="Converte il Silver JSON in gold_certified_data.csv")
    parser.add_argument("--batch", type=int, default=5, help="Dimensione batch processing")
    
    args = parser.parse_args()

    if not any([args.ingest, args.process, args.process_excel, args.certify]):
        parser.print_help()
    else:
        if args.ingest:
            run_ingestion()
        if args.process:
            run_processing(batch_size=args.batch)
        if args.process_excel:
            run_excel_processing(batch_size=args.batch)
        if args.certify:
            run_certify()

# --- CLI ENTRY POINT ---
if __name__ == "__main__":
    main_cli()