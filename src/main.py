import pandas as pd
import json
import numpy as np

# Load data files
def load_data():
    # Load Data
    try:
        with open('case_files/incident_reports.json', 'r') as f:
            incidents = json.load(f)

        with open('case_files/phone_pings.json', 'r') as f:
            phone_pings = json.load(f)

        with open('case_files/suspects.json', 'r') as f:
            suspects = json.load(f)

        # Load CSV Files
        bike_logs = pd.read_csv('case_files/bike_logs.csv')
        cam_snapshots = pd.read_csv('case_files/cam_snapshots_metadata.csv')

        print("Data successfully loaded")

        return incidents, phone_pings, suspects, bike_logs, cam_snapshots

    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def explore_data(incidents, phone_pings, suspects, bike_logs, cam_snapshots):
    print("INCIDENT REPORTS:")
    print(f"Number of incidents: {len(incidents)}")
    for i, incident in enumerate(incidents):
        print(f"\nIncident {i+1}")
        print(f"Date: {incident['date']}")
        print(f"Address: {incident['address']}")
        print(f"Entry Time: {incident['entry_time']}")
        print(f"Exit Time: {incident['exit_time']}")
        print(f"Notes: {incident['notes']}")

def main():
    # Load Data
    incidents, phone_pings, suspects, bike_logs, cam_snapshots = load_data()

    explored_data = explore_data(incidents, phone_pings, suspects, bike_logs, cam_snapshots)

main()