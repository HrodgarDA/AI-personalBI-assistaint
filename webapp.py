import csv
from pathlib import Path

import streamlit as st

DATA_PATH = Path(__file__).resolve().parent / "data" / "gold_certified_data.csv"


def load_data(path: Path):
    with path.open(newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        rows = list(reader)

    for row in rows:
        if "amount" in row:
            try:
                row["amount"] = float(row["amount"])
            except (ValueError, TypeError):
                pass
        if "confidence" in row:
            try:
                row["confidence"] = float(row["confidence"])
            except (ValueError, TypeError):
                pass
    return rows


def main():
    st.set_page_config(page_title="Gold Certified Data", layout="wide")
    st.title("Visualizzazione dati gold_certified_data")
    st.markdown(
        "Questa app mostra i dati certificati contenuti nel file `data/gold_certified_data.csv`."
    )

    if not DATA_PATH.exists():
        st.error(f"File non trovato: {DATA_PATH}")
        return

    data = load_data(DATA_PATH)
    if not data:
        st.warning("Il file esiste ma non contiene righe da visualizzare.")
        return

    categories = sorted({row.get("category", "") for row in data if row.get("category", "")})
    categories.insert(0, "Tutte")

    selected = st.multiselect("Filtra per categoria", categories, default=["Tutte"])
    filtered = data
    if selected and "Tutte" not in selected:
        filtered = [row for row in data if row.get("category") in selected]

    st.sidebar.header("Filtri e statistiche")
    st.sidebar.write("Righe totali:", len(filtered))

    numeric_amounts = [row["amount"] for row in filtered if isinstance(row.get("amount"), float)]
    if numeric_amounts:
        st.sidebar.write("Totale importi:", sum(numeric_amounts))
        st.sidebar.write("Importo medio:", round(sum(numeric_amounts) / len(numeric_amounts), 2))

    st.dataframe(filtered, use_container_width=True)

    if st.checkbox("Mostra anteprima raw del file CSV"):
        raw_text = DATA_PATH.read_text(encoding="utf-8")
        st.code(raw_text[:10000], language="csv")


if __name__ == "__main__":
    main()
