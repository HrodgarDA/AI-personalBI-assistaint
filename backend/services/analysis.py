import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Service to identify unusual patterns in transaction data for auditing and verification."""

    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        self.df = pd.DataFrame(data)
        
        # Mapping renamed fields if necessary for backwards compatibility during transition
        if 'tipology' in self.df.columns:
            self.df.rename(columns={'tipology': 'transaction_type'}, inplace=True)

        if not self.df.empty and 'date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['date'])

    def run_all_checks(self) -> List[Dict[str, Any]]:
        """Runs all detection strategies and returns a prioritized list of alerts."""
        if self.df.empty:
            return []
        
        alerts = []
        alerts.extend(self.check_spikes())
        alerts.extend(self.check_duplicates())
        alerts.extend(self.check_novelties())
        alerts.extend(self.check_low_confidence())
        
        # Sort by severity (descending)
        return sorted(alerts, key=lambda x: x['severity'], reverse=True)

    def check_spikes(self) -> List[Dict[str, Any]]:
        """Finds transactions with unusually high amounts compared to the category average using IQR."""
        alerts = []
        if 'category_id' not in self.df.columns or 'amount' not in self.df.columns:
            return alerts

        temp_df = self.df.copy()
        temp_df['abs_amount'] = pd.to_numeric(temp_df['amount'], errors='coerce').abs()
        temp_df = temp_df.dropna(subset=['abs_amount', 'category_id'])

        for category, group in temp_df.groupby('category_id'):
            if len(group) < 5:  # Statistical significance threshold
                continue
                
            q1 = group['abs_amount'].quantile(0.25)
            q3 = group['abs_amount'].quantile(0.75)
            iqr = q3 - q1
            upper_bound = q3 + 1.5 * iqr
            
            outliers = group[group['abs_amount'] > upper_bound]
            
            for _, row in outliers.iterrows():
                alerts.append({
                    "id": row.get("id", "unknown"),
                    "type": "Spike",
                    "merchant": str(row.get("merchant_id", "Unknown")),
                    "category": category,
                    "amount": row.get("amount"),
                    "message": f"Unusual expense for {category} (€{abs(row['abs_amount']):.2f} vs expected max €{upper_bound:.2f})",
                    "severity": 2 if abs(row['abs_amount']) > upper_bound * 2 else 1
                })
        return alerts

    def check_duplicates(self) -> List[Dict[str, Any]]:
        """Identifies potential duplicate transactions based on merchant, amount, and date."""
        alerts = []
        required_cols = {'merchant_id', 'amount', 'date'}
        if not required_cols.issubset(self.df.columns):
            return alerts

        temp_df = self.df.copy()
        temp_df['merchant_clean'] = temp_df['merchant_id'].fillna("Unknown").astype(str).str.lower()
        
        # Find duplicated rows
        duplicates = temp_df[temp_df.duplicated(subset=['merchant_clean', 'amount', 'date'], keep=False)]
        
        for (merchant_clean, amount, date), group in duplicates.groupby(['merchant_clean', 'amount', 'date']):
            if merchant_clean == "unknown":
                continue
            
            ids = group['id'].tolist()
            alerts.append({
                "id": ids[0],
                "type": "Duplicate",
                "merchant": group.iloc[0].get("merchant_id", "Unknown"),
                "category": group.iloc[0].get("category_id"),
                "amount": amount,
                "message": f"Detected {len(group)} identical transactions for {group.iloc[0].get('merchant_id')} on {date}. Possible duplicate?",
                "severity": 3  # High severity
            })
        return alerts

    def check_novelties(self) -> List[Dict[str, Any]]:
        """Flags significant transactions at merchants seen for the first time."""
        alerts = []
        if 'merchant_id' not in self.df.columns or 'amount' not in self.df.columns:
            return alerts

        temp_df = self.df.copy()
        temp_df['merchant_str'] = temp_df['merchant_id'].fillna("Unknown").astype(str)
        
        # Novelty threshold in Euros (should be configurable)
        threshold = 50.0
        m_counts = temp_df['merchant_str'].value_counts()
        new_merchants = m_counts[m_counts == 1].index.tolist()
        
        for merchant in new_merchants:
            if merchant.lower() == "unknown":
                continue
            
            row = temp_df[temp_df['merchant_str'] == merchant].iloc[0]
            try:
                amt = float(row['amount'])
                if abs(amt) > threshold:
                    alerts.append({
                        "id": row.get("id"),
                        "type": "Novelty",
                        "merchant": merchant,
                        "category": row.get("category_id"),
                        "amount": amt,
                        "message": f"Significant new merchant: €{abs(amt):.2f} spent at {merchant}.",
                        "severity": 1
                    })
            except (ValueError, TypeError):
                continue
        return alerts

    def check_low_confidence(self) -> List[Dict[str, Any]]:
        """Flags transactions where the AI classifier confidence score is below threshold."""
        alerts = []
        if 'confidence' not in self.df.columns:
            return alerts
            
        low_conf = self.df[self.df['confidence'] < 0.7]
        for _, row in low_conf.iterrows():
             alerts.append({
                "id": row.get("id"),
                "type": "Low Confidence",
                "merchant": row.get("merchant_id"),
                "category": row.get("category_id"),
                "amount": row.get("amount"),
                "message": f"AI classification confidence is low ({int(row['confidence']*100)}%) for {row['merchant_id']}. Please verify.",
                "severity": 1
            })
        return alerts
