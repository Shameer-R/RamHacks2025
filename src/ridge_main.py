import pandas as pd
import geopy
import geocoder
from geopy.geocoders import Nominatim
import json
import numpy as np

# Load data files
 

def load_data():
    # Load Data
    try:
        with open('../case_files/incident_reports.json', 'r') as f:
            incidents = json.load(f)

        with open('../case_files/phone_pings.json', 'r') as f:
            phone_pings = json.load(f)

        with open('../case_files/suspects.json', 'r') as f:
            suspects = json.load(f)

        # Load CSV Files
        bike_logs = pd.read_csv('../case_files/bike_logs.csv')
        cam_snapshots = pd.read_csv('../case_files/cam_snapshots_metadata.csv')

        print("Data successfully loaded")

        return incidents, phone_pings, suspects, bike_logs, cam_snapshots

    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def main():
    devices_at_crime = [];
    geolocator = Nominatim(user_agent="hackathon")
    incidents_json, pings_json, suspects_json, bike_logs_json, snapshots_json = load_data();

    for incident in incidents_json:
        for pings in pings_json:
            if pings['timestamp']>=incident['entry_time'] and pings['timestamp'] <=incident['exit_time']:
                location = geolocator.reverse((f"{pings['lat']}" +","+ f"{pings['lon']}"))
                first_partition = str.partition(location.address,", ")
                street_number = first_partition[0]
                street= str.partition(first_partition[2]," ")[0]
                if street == str.partition(str.partition(incident['address']," ")[2]," ")[0]:
                        print(street + " "+ street_number)
                        devices_at_crime.append(pings['device_id'])
    for i in devices_at_crime:
        print(i)
main()
