import json
import socket
import datetime
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

class DataHandler:
    SCRIPT_DIR = Path(__file__).resolve().parent
    RESULTS_PATH = SCRIPT_DIR.parent / "results"

    def __init__(self, IPAddress="UnknownIP", user_id="Anonymous"):
        # Create results directory if it doesn't exist
        self.RESULTS_PATH.mkdir(parents=True, exist_ok=True)
        IP = ""
        self.data = {
            "UserID": user_id,
            "IPAddress": IPAddress,
            "TimeStart": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Runs": {}
        }
        
        # Define the filename ONCE at initialization so we keep writing to the same file
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # sanitized_ip = self.data['IPAddress'].replace('.', '-')
        # sanitized_ip = sanitized_ip.replace(':', '-')
        self.filename = self.RESULTS_PATH / f"{user_id}_{timestamp}_data.json"

    def _ensure_path(self, run_id: str, version_id: str):
        """Ensures the Run and Version keys exist."""
        if run_id not in self.data["Runs"]:
            self.data["Runs"][run_id] = {}
        
        if version_id not in self.data["Runs"][run_id]:
            self.data["Runs"][run_id][version_id] = []

    def start_new_version(self, run_id: str, version_id: str, system_name: str):
        """Starts a new block inside a Version."""
        self._ensure_path(run_id, version_id)
        
        new_session = {
            "System": system_name,
            "Comprehension": "", 
            "StartTime": datetime.datetime.now().strftime("%H:%M:%S")
        }
        
        self.data["Runs"][run_id][version_id].append(new_session)

    def add_query(self, run_id: str, version_id: str, scene_number: int, query_data: Dict):
        """Adds a query to the current session."""
        self._ensure_path(run_id, version_id)
        
        versions_list = self.data["Runs"][run_id][version_id]
        
        # If no session exists, create a default one
        if not versions_list:
            self.start_new_version(run_id, version_id, "Unknown System")
            
        current_session = versions_list[-1]
        scene_key = f"scene: {scene_number}"
        
        if scene_key not in current_session:
            current_session[scene_key] = []
            
        query_count = len(current_session[scene_key]) + 1
        
        formatted_query = {
            f"Query: {query_count}": query_data
        }
        
        current_session[scene_key].append(formatted_query)

    def add_comprehension(self, run_id: str, version_id: str, text: str):
        """Adds the comprehension text to the current session."""
        self._ensure_path(run_id, version_id)
        versions_list = self.data["Runs"][run_id][version_id]
        
        if versions_list:
            versions_list[-1]["Comprehension"] = text

    def export_json(self):
        """Overwrites the specific user file with the latest data."""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f, indent=4)
            print(f"Data updated: {self.filename}")
        except Exception as e:
            print(f"Error saving data: {e}")

    def get_json_str(self):
        return json.dumps(self.data, indent=4)