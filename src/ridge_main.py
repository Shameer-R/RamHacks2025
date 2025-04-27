import pandas as pd
import geopy
import geocoder
from geopy.geocoders import Nominatim
import json
import numpy as np
from geopy.distance import geodesic

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


def get_devices_near_crime(crime_json, ping_json):
    distance = 1
    geolocator = Nominatim(user_agent="hackathon")
    devices_near_crime = []
    incident_day = 5
    for incident in crime_json:
        for pings in ping_json:
            if pings['timestamp']>=incident['entry_time'] and pings['timestamp'] <=incident['exit_time']:
                location = geolocator.geocode((f"{incident['address']}"))
                if geodesic((location.latitude,location.longitude),(pings['lat'],pings['lon'])).miles <= distance:
                    devices_near_crime.append([pings['device_id'],incident_day])
        incident_day-=1
    return devices_near_crime

def suspects_from_phone(suspect_json, devices_near):
    suspect_list = []
    for suspect in suspect_json:
        for device_data in devices_near:
            if suspect['phone_id'] == device_data[0]:
                suspect_list.append([suspect['name'],device_data[1]])
    return suspect_list

def get_suspects_from_logs(bike_csv,incident_json):
    suspect_list = []
    for incident in incident_json:
        bike_counter = 0
        while bike_counter < len(bike_csv["start_time"]):
            if incident["entry_time"] >= (bike_csv["start_time"])[bike_counter] and incident["exit_time"] <= (bike_csv["end_time"])[bike_counter]:
                suspect_list.append((bike_csv["user_id"])[bike_counter])
            bike_counter+=1
    return suspect_list
                


def filter_bike_suspects(suspect_json, bike_suspects):
    final_list = []
    for suspect in suspect_json:
        for sus in bike_suspects:
            if sus == suspect["alias"] and not (sus in final_list):
                final_list.append(sus)
    return final_list

def main():

    incidents_json, pings_json, suspects_json, bike_logs_csv, snapshots_csv = load_data();
    devices_near_crime = get_devices_near_crime(incidents_json,pings_json)
    suspect_list = suspects_from_phone(suspects_json,devices_near_crime)




    for i in suspect_list:
        print(i)



    print("suspects from bike logs")
    bikes_rented = get_suspects_from_logs(bike_logs_csv,incidents_json)
    bike_suspect_list = filter_bike_suspects(suspects_json,bikes_rented)
    for i in bike_suspect_list:
        print(i)

main()
