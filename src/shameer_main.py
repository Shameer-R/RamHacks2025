from datetime import datetime

import pandas as pd
import json
import numpy as np
from geopy.distance import geodesic


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
    # Explore Incidents

    print("\nINCIDENT REPORTS:")
    print(f"Number of incidents: {len(incidents)}")
    for i, incident in enumerate(incidents):
        print(f"\nIncident {i + 1}")
        print(f"Date: {incident['date']}")
        print(f"Address: {incident['address']}")
        print(f"Entry Time: {incident['entry_time']}")
        print(f"Exit Time: {incident['exit_time']}")
        print(f"Notes: {incident['notes']}")

    # Explore Phone Pings

    print("\nPHONE PINGS:")
    print(f"Number of phone pings: {len(phone_pings)}")
    device_ids = set(ping['device_id'] for ping in phone_pings)
    print(f"Unique device ids: {device_ids}")

    # Explore Suspects
    print("\nSUSPECTS:")
    print(f"Number of suspects: {len(suspects)}")
    for i, suspect in enumerate(suspects):
        print(f"\nSuspect {i + 1}")
        for key, value in suspect.items():
            print(f"\t{key}: {value}")

    print("\nBIKE LOGS:")
    print(f"Total Bike Logs: {len(bike_logs)}")
    print(f"Columns: {list(bike_logs.columns)}")

    print("\nCAMERA SNAPSHOTS:")
    print(f"Total Camera Snapshots: {len(cam_snapshots)}")
    print(f"Columns: {list(cam_snapshots.columns)}")

    # Connect Device IDS to Suspect
    device_to_suspect = {}
    for suspect in suspects:
        if 'phone_id' in suspect and suspect['phone_id']:
            device_to_suspect[suspect['phone_id']] = suspect['name']

    print("\nDEVICE TO SUSPECT MAPPING:")
    for device, name in device_to_suspect.items():
        print(f"\t{device}: {name}")

    return device_to_suspect


def parse_timestamps(timestamp_str):
    try:
        if 'T' in timestamp_str:
            return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
        else:
            return datetime.strptime(timestamp_str, '%Y-%m-%d')
    except Exception as e:
        print(f"Error parsing timestamp {timestamp_str}: {e}")
        return None


def analyze_proximity(incidents, phone_pings, device_to_suspect):
    # Start checking which devices were near which incidents
    device_at_incidents = {device_id: set() for device_id in device_to_suspect.keys()}
    evidence_log = {device_id: [] for device_id in device_to_suspect.keys()}

    # Evidence constraints
    proximity_threshold = 0.2  # miles
    time_window = 60  # minutes

    for incident in incidents:
        incident_address = incident['address']

        if "108 Linden St" in incident_address:
            incident_location = (40.695, -73.92)
        elif "104 Linden St" in incident_address:
            incident_location = (40.696, -73.925)
        elif "102 Linden St" in incident_address:
            incident_location = (40.697, -73.93)
        else:
            continue

        entry_time = parse_timestamps(incident['entry_time'])
        exit_time = parse_timestamps(incident['exit_time'])

        if not entry_time or not exit_time:
            continue

        time_before = entry_time - pd.Timedelta(minutes=time_window)
        time_after = exit_time + pd.Timedelta(minutes=time_window)

        for ping in phone_pings:
            device_id = ping['device_id']
            if device_id not in device_to_suspect:  # Device not linked to suspect
                continue

            ping_time = parse_timestamps(ping['timestamp'])
            if not ping_time:
                continue  # Skip if timestamp couldn't be parsed

            if time_before <= ping_time <= time_after:
                ping_location = (ping['lat'], ping['lon'])

                distance = geodesic(ping_location, incident_location).miles

                if distance <= proximity_threshold:
                    device_at_incidents[device_id].add(incident_address)

                    evidence_log[device_id].append({
                        'incident_address': incident_address,
                        'ping_time': ping_time,
                        'incident_entry': entry_time,
                        'incident_exit': exit_time,
                        'distance_miles': distance
                    })

    return device_at_incidents, evidence_log


def analyze_bike_rentals(incidents, bike_logs, suspects):
    name_to_suspect = {}
    for suspect in suspects:
        name_to_suspect[suspect['name']] = suspect
        if 'alias' in suspect:
            name_to_suspect[suspect['alias']] = suspect

    suspect_rentals = {suspect['name']: set() for suspect in suspects}

    bike_logs['start_time'] = pd.to_datetime(bike_logs['start_time']).dt.tz_localize(None)
    bike_logs['end_time'] = pd.to_datetime(bike_logs['end_time']).dt.tz_localize(None)

    incident_times = []
    for incident in incidents:
        entry_time = parse_timestamps(incident['entry_time'])
        exit_time = parse_timestamps(incident['exit_time'])
        if entry_time and exit_time:
            incident_times.append({
                'address': incident['address'],
                'entry_time': entry_time,
                'exit_time': exit_time
            })

    for _, rental in bike_logs.iterrows():
        renter = rental['user_id']
        if renter in name_to_suspect:
            suspect = name_to_suspect[renter]
            suspect_name = suspect['name']

            rental_start = rental['start_time']
            rental_end = rental['end_time']

            for incident in incident_times:
                # Convert both to the same type for comparison
                if (rental_start <= incident['exit_time'] and
                    rental_end >= incident['entry_time']):
                    suspect_rentals[suspect_name].add(incident['address'])

    return suspect_rentals


def identify_primary_suspects(device_at_incidents, device_to_suspect, suspect_rentals, incidents):
    all_addresses = set(incident['address'] for incident in incidents)

    combined_evidence = {}

    # Collect evidence from phone pings
    for device_id, addresses in device_at_incidents.items():
        suspect_name = device_to_suspect[device_id]
        if suspect_name not in combined_evidence:
            combined_evidence[suspect_name] = set()
        combined_evidence[suspect_name].update(addresses)

    # Add bike rental evidence
    for suspect_name, addresses in suspect_rentals.items():
        if suspect_name not in combined_evidence:
            combined_evidence[suspect_name] = set()
        combined_evidence[suspect_name].update(addresses)

    prime_suspects = []
    for suspect_name, addresses in combined_evidence.items():
        if addresses == all_addresses:
            evidence_count = len(addresses)
            prime_suspects.append((suspect_name, evidence_count))

    if prime_suspects:
        # Sort by evidence count
        prime_suspects.sort(key=lambda x: x[1], reverse=True)

        top_suspect = prime_suspects[0][0]

        phone_evidence = []
        for device_id, addresses in device_at_incidents.items():
            if device_to_suspect[device_id] == top_suspect:
                phone_evidence = list(addresses)

        bike_evidence = list(suspect_rentals.get(top_suspect, []))
        justification = f"{top_suspect} was present at all three crimes"

        return top_suspect, justification

    # FIX: Add a more informative return message
    print("No suspect matches all three burglaries.")
    return None, "No suspect matches all three burglaries."


def main():
    # Load Data
    incidents, phone_pings, suspects, bike_logs, cam_snapshots = load_data()

    if incidents is None or phone_pings is None or suspects is None:
        print("Failed to load critical data files. Exiting.")
        return

    device_to_suspect = explore_data(incidents, phone_pings, suspects, bike_logs, cam_snapshots)
    device_at_incidents, evidence_log = analyze_proximity(incidents, phone_pings, device_to_suspect)

    # Debug prints
    print("\nDEVICES AT INCIDENTS:")
    for device_id, addresses in device_at_incidents.items():
        print(f"{device_id}: {addresses}")

    suspect_rentals = analyze_bike_rentals(incidents, bike_logs, suspects)

    # Debug prints
    print("\nSUSPECT RENTALS:")
    for suspect, addresses in suspect_rentals.items():
        print(f"{suspect}: {addresses}")

    result = identify_primary_suspects(device_at_incidents, device_to_suspect, suspect_rentals, incidents)

    if result and isinstance(result, tuple):
        top_suspect, justification = result
        print(f"\nTOP SUSPECT: {top_suspect}")
        print(f"JUSTIFICATION: {justification}")
    else:
        print("No definitive suspect identified.")


if __name__ == "__main__":
    main()