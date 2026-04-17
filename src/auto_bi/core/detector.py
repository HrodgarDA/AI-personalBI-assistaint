import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Engine to identify unusual patterns in transaction data."""

    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        self.df = pd.DataFrame(data)
        
        # Ensure 'id' exists by aliasing 'original_msg_id' if necessary
        if 'id' not in self.df.columns and 'original_msg_id' in self.df.columns:
            self.df['id'] = self.df['original_msg_id']

        if not self.df.empty and 'parsed_date' in self.df.columns:
            self.df['parsed_date'] = pd.to_datetime(self.df['parsed_date'])

    def run_all_checks(self) -> List[Dict[str, Any]]:
        """Runs all detection strategies and returns a list of alerts."""
        if self.df.empty:
            return []
        
        alerts = []
        alerts.extend(self.check_spikes())
        alerts.extend(self.check_duplicates())
        alerts.extend(self.check_novelties())
        alerts.extend(self.check_low_confidence())
        
        return sorted(alerts, key=lambda x: x['severity'], reverse=True)

    def check_spikes(self) -> List[Dict[str, Any]]:
        """Finds transactions with unusually high amounts inside their category using IQR."""
        alerts = []
        if 'category' not in self.df.columns or 'amount' not in self.df.columns:
            return alerts

        # We only analyze expenses (amount < 0) for spikes usually
        temp_df = self.df.copy()
        temp_df['abs_amount'] = pd.to_numeric(temp_df['amount'], errors='coerce').abs()
        temp_df = temp_df.dropna(subset=['abs_amount', 'category'])

        for category, group in temp_df.groupby('category'):
            if len(group) < 5:  # Need at least 5 points for meaningful IQR
                continue
                
            q1 = group['abs_amount'].quantile(0.25)
            q3 = group['abs_amount'].quantile(0.75)
            iqr = q3 - q1
            upper_bound = q3 + 1.5 * iqr
            
            # Identify outliers
            outliers = group[group['abs_amount'] > upper_bound]
            
            for _, row in outliers.iterrows():
                alerts.append({
                    "id": row.get("id", "unknown"),
                    "type": "Spike",
                    "merchant": str(row.get("merchant", "Unknown")),
                    "category": category,
                    "amount": row.get("amount"),
                    "message": f"Spesa insolita per {category} (€{abs(row['abs_amount']):.2f} vs soglia €{upper_bound:.2f})",
                    "severity": 2 if abs(row['abs_amount']) > upper_bound * 2 else 1
                })
        return alerts

    def check_duplicates(self) -> List[Dict[str, Any]]:
        """Finds potential duplicate transactions (same merchant, amount, and date)."""
        alerts = []
        if 'merchant' not in self.df.columns or 'amount' not in self.df.columns or 'date' not in self.df.columns:
            return alerts

        # Clean data for comparison
        temp_df = self.df.copy()
        temp_df['merchant_clean'] = temp_df['merchant'].fillna("Unknown").astype(str).str.lower()
        
        # Group by merchant, amount and date
        duplicates = temp_df[temp_df.duplicated(subset=['merchant_clean', 'amount', 'date'], keep=False)]
        
        # Group duplicates to create a single alert per "set" of duplicates
        for (merchant_clean, amount, date), group in duplicates.groupby(['merchant_clean', 'amount', 'date']):
            if merchant_clean == "unknown": continue
            
            ids = group['id'].tolist()
            alerts.append({
                "id": ids[0], # Reference the first one
                "type": "Duplicate",
                "merchant": group.iloc[0].get("merchant", "Unknown"),
                "category": group.iloc[0].get("category"),
                "amount": amount,
                "message": f"Trovate {len(group)} transazioni identiche per {group.iloc[0].get('merchant')} il {date}. Possibile duplicato?",
                "severity": 3 # High severity for duplicates
            })
        return alerts

    def check_novelties(self) -> List[Dict[str, Any]]:
        """Identifies high spending at merchants seen for the first time."""
        alerts = []
        if 'merchant' not in self.df.columns or 'amount' not in self.df.columns:
            return alerts

        # Clean merchants
        temp_df = self.df.copy()
        temp_df['merchant_str'] = temp_df['merchant'].fillna("Unknown").astype(str)
        
        threshold = 50.0
        m_counts = temp_df['merchant_str'].value_counts()
        new_merchants = m_counts[m_counts == 1].index.tolist()
        
        for merchant in new_merchants:
            if merchant.lower() == "unknown": continue
            
            row = temp_df[temp_df['merchant_str'] == merchant].iloc[0]
            try:
                amt = float(row['amount'])
                if abs(amt) > threshold:
                    alerts.append({
                        "id": row.get("id"),
                        "type": "Novelty",
                        "merchant": merchant,
                        "category": row.get("category"),
                        "amount": amt,
                        "message": f"Nuovo merchant rilevante: spesi €{abs(amt):.2f} presso {merchant}.",
                        "severity": 1
                    })
            except (ValueError, TypeError):
                continue
        return alerts

    def check_low_confidence(self) -> List[Dict[str, Any]]:
        """Flags transactions where the AI had low confidence (existing logic integrated here)."""
        alerts = []
        if 'confidence' not in self.df.columns:
            return alerts
            
        low_conf = self.df[self.df['confidence'] < 0.7]
        for _, row in low_conf.iterrows():
             alerts.append({
                "id": row.get("id"),
                "type": "Low Confidence",
                "merchant": row.get("merchant"),
                "category": row.get("category"),
                "amount": row.get("amount"),
                "message": f"L'AI non è sicura della categoria ({int(row['confidence']*100)}%). Controlla {row['merchant']}.",
                "severity": 1
            })
        return alerts
