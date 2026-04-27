import requests
import os
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

class APIClient:
    def __init__(self, base_url=API_BASE_URL):
        self.base_url = base_url

    def get_transactions(self, params=None):
        try:
            response = requests.get(f"{self.base_url}/transactions/", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error fetching transactions: {e}")
            return []

    def upload_file(self, file, profile_name):
        try:
            files = {"file": (file.name, file.getvalue(), file.type)}
            params = {"profile_name": profile_name}
            response = requests.post(f"{self.base_url}/upload/", files=files, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error uploading file: {e}")
            return None

    def get_task_status(self, task_id):
        try:
            response = requests.get(f"{self.base_url}/upload/task/{task_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error fetching task status: {e}")
            return None

    def update_transaction(self, tx_id, data):
        try:
            response = requests.patch(f"{self.base_url}/transactions/{tx_id}", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error updating transaction: {e}")
            return None

    def delete_transaction(self, tx_id):
        try:
            response = requests.delete(f"{self.base_url}/transactions/{tx_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error deleting transaction: {e}")
            return None

    def get_categories(self):
        try:
            response = requests.get(f"{self.base_url}/metadata/categories")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error fetching categories: {e}")
            return []

    def get_merchants(self):
        try:
            response = requests.get(f"{self.base_url}/metadata/merchants")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error fetching merchants: {e}")
            return []

    def get_profiles(self):
        try:
            response = requests.get(f"{self.base_url}/metadata/profiles")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error fetching profiles: {e}")
            return []

    def create_profile(self, name, config=None):
        try:
            response = requests.post(f"{self.base_url}/metadata/profiles", json={"name": name, "config": config or {}})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error creating profile: {e}")
            return None

    def delete_profile(self, name):
        try:
            response = requests.delete(f"{self.base_url}/metadata/profiles/{name}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error deleting profile: {e}")
            return None

    def run_recovery(self):
        try:
            response = requests.post(f"{self.base_url}/maintenance/recover")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error running recovery: {e}")
            return None

api_client = APIClient()
