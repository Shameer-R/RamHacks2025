import streamlit as st
import pandas as pd
import json
from datetime import datetime
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim

# global geocode object for turning address to coordinates and vice versa
locator = Nominatim(user_agent="proximity_analyzer")

def load_data():
    try:
        with open('../case_files/incident_reports.json', 'r') as f:
            incidents = json.load(f)

        with open('../case_files/phone_pings.json', 'r') as f:
            phone_pings = json.load(f)

        with open('../case_files/suspects.json', 'r') as f:
            suspects = json.load(f)

        bike_logs = pd.read_csv('../case_files/bike_logs.csv')

        return incidents, phone_pings, suspects, bike_logs
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None, None


def parse_timestamps(timestamp_str):
    try:
        if 'T' in timestamp_str:
            return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
        else:
            return datetime.strptime(timestamp_str, '%Y-%m-%d')
    except Exception as e:
        return None


def analyze_proximity(incidents, phone_pings, device_to_suspect):
    device_at_incidents = {device_id: set() for device_id in device_to_suspect.keys()}
    evidence_log = {device_id: [] for device_id in device_to_suspect.keys()}

    proximity_threshold = .1  # miles
    time_window = 60  # minutes

    for incident in incidents:
        incident_address = incident['address']
        incident_geocode = locator.geocode(incident_address)
        incident_location = (incident_geocode.latitude,incident_geocode.longitude)

        entry_time = parse_timestamps(incident['entry_time'])
        exit_time = parse_timestamps(incident['exit_time'])

        if not entry_time or not exit_time:
            continue

        time_before = entry_time - pd.Timedelta(minutes=time_window)
        time_after = exit_time + pd.Timedelta(minutes=time_window)

        for ping in phone_pings:
            device_id = ping['device_id']
            if device_id not in device_to_suspect:
                continue

            ping_time = parse_timestamps(ping['timestamp'])
            if not ping_time:
                continue

            #maybe change
            if time_before <= ping_time <= time_after:
                ping_location = locator.reverse(f"{ping['lat']}" +"," +f"{ping['lon']}")
                if "Linden Street" in ping_location.address:
                    device_at_incidents[device_id].add(incident_address)

                    evidence_log[device_id].append({
                            'incident_address': incident_address,
                            'ping_time': ping_time,
                            'incident_entry': entry_time,
                            'incident_exit': exit_time,
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
                if rental_start <= incident['entry_time'] and rental_end >= incident['exit_time']:
                    suspect_rentals[suspect_name].add(incident['address'])

    return suspect_rentals


def identify_primary_suspects(device_at_incidents, device_to_suspect, suspect_rentals, incidents):
    all_addresses = set(incident['address'] for incident in incidents)

    combined_evidence = {}

    for device_id, addresses in device_at_incidents.items():
        suspect_name = device_to_suspect[device_id]
        if suspect_name not in combined_evidence:
            combined_evidence[suspect_name] = set()
        combined_evidence[suspect_name].update(addresses)

    for suspect_name, addresses in suspect_rentals.items():
        if suspect_name not in combined_evidence:
            combined_evidence[suspect_name] = set()
        combined_evidence[suspect_name].update(addresses)

    suspects_scored = []
    for suspect_name, addresses in combined_evidence.items():
        match_count = len(addresses)
        coverage = (match_count / len(all_addresses)) * 100
        suspects_scored.append({
            'name': suspect_name,
            'match_count': match_count,
            'coverage': coverage,
            'addresses': list(addresses)
        })

    suspects_scored.sort(key=lambda x: x['match_count'], reverse=True)

    return suspects_scored[:3]


def create_map(incidents, phone_pings, top_suspect_devices):
    incident_coords = []
    for incident in incidents:
        geocode = locator.geocode(incident['address'])
        incident_coords.append((geocode.latitude,geocode.longitude, incident['address'], incident['date']))

    center_lat = sum(coord[0] for coord in incident_coords) / len(incident_coords)
    center_lon = sum(coord[1] for coord in incident_coords) / len(incident_coords)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=16)

    for lat, lon, address, date in incident_coords:
        folium.Marker(
            location=[lat, lon],
            popup=f"{address}<br>Date: {date}",
            icon=folium.Icon(color='red', icon='home'),
        ).add_to(m)

    for ping in phone_pings:
        if ping['device_id'] in top_suspect_devices:
            color = 'green'
            radius = 30
            fill_opacity = 0.7
        else:
            color = 'blue'
            radius = 10
            fill_opacity = 0.3

        folium.CircleMarker(
            location=[ping['lat'], ping['lon']],
            radius=radius,
            popup=f"Device: {ping['device_id']}<br>Time: {ping['timestamp']}",
            color=color,
            fill=True,
            fill_opacity=fill_opacity
        ).add_to(m)

    return m


st.title("Linden Street Burglaries Investigation")

if st.button("Analyze Evidence"):
    incidents, phone_pings, suspects, bike_logs = load_data()

    if incidents is None:
        st.error("Failed to load data files. Check file paths.")
        st.stop()

    device_to_suspect = {}
    for suspect in suspects:
        if 'phone_id' in suspect and suspect['phone_id']:
            device_to_suspect[suspect['phone_id']] = suspect['name']

    device_at_incidents, evidence_log = analyze_proximity(incidents, phone_pings, device_to_suspect)
    suspect_rentals = analyze_bike_rentals(incidents, bike_logs, suspects)
    top_suspects = identify_primary_suspects(device_at_incidents, device_to_suspect, suspect_rentals, incidents)

    st.header("Top Suspects")

    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3]

    for i, suspect in enumerate(top_suspects):
        with columns[i]:
            st.subheader(f"#{i + 1}: {suspect['name']}")
            for s in suspects:
                if s['name'] == suspect['name']:
                    st.write(f"**Occupation:** {s.get('occupation', 'Unknown')}")
                    st.write(f"**Alibi:** {s.get('alibi', 'None provided')}")
                    st.write(f"**Connections:** {suspect['match_count']} locations ({suspect['coverage']:.0f}%)")

    st.header("Crime Scene Map")

    top_suspect_devices = []
    for suspect in top_suspects:
        for s in suspects:
            if s['name'] == suspect['name'] and 'phone_id' in s:
                top_suspect_devices.append(s['phone_id'])

    map_figure = create_map(incidents, phone_pings, top_suspect_devices)
    folium_static(map_figure)

    st.header("Incident Reports")
    incident_df = pd.DataFrame([{
        'Date': incident['date'],
        'Address': incident['address'],
        'Entry Time': incident['entry_time'],
        'Exit Time': incident['exit_time'],
        'Notes': incident['notes']
    } for incident in incidents])

    st.dataframe(incident_df)

    st.header("Evidence Summary")

    tabs = st.tabs(["Phone Evidence", "Bike Rentals"])

    with tabs[0]:
        for device_id, addresses in device_at_incidents.items():
            if addresses:
                st.write(f"**{device_to_suspect[device_id]}'s phone** detected at:")
                for address in addresses:
                    st.write(f"- {address}")

    with tabs[1]:
        for suspect_name, addresses in suspect_rentals.items():
            if addresses:
                st.write(f"**{suspect_name}** rented bikes during crimes at:")
                for address in addresses:
                    st.write(f"- {address}")

    primary_suspect = top_suspects[0]['name'] if top_suspects else "No definitive suspect"
    st.success(f"Primary suspect: **{primary_suspect}**")

else:
    st.info("Click 'Analyze Evidence' to view results")

# Run 'streamlit run src/shameer_main.py' in terminal
