import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime

st.set_page_config(page_title="TamilVandi - Bus Finder", layout="centered")

@st.cache_data
def load_data():
    return pd.read_excel("bus_schedule.xlsx")

df = load_data()

# Set session state for map visibility
if 'show_map' not in st.session_state:
    st.session_state.show_map = False

# Custom CSS styles
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #f7f7f7;
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

.main-card {
    background-color: #ffffff;
    padding: 3rem 2rem;
    border-radius: 25px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
    max-width: 900px;
    margin: auto;
    animation: fadeIn 1s ease-in-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}

.header-title {
    text-align: center;
    font-size: 3rem;
    font-weight: 700;
    color: #ff6f00;
    margin-bottom: 2.5rem;
}

.search-button button {
    background-color: #ff6f00;
    color: white;
    font-size: 1.2rem;
    font-weight: bold;
    padding: 0.8rem 2.8rem;
    border-radius: 30px;
    border: none;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
    transition: all 0.3s ease;
}

.search-button button:hover {
    background-color: #e65100;
    transform: scale(1.05);
}

.bus-card {
    background: #fafafa;
    padding: 1.8rem;
    border-radius: 18px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
    margin: 1.8rem 0;
    transition: all 0.3s ease;
    text-align: center;
}

.bus-info {
    display: flex;
    justify-content: space-between;
    font-size: 1.2rem;
    margin: 0.8rem 0;
    color: #333;
    flex-wrap: wrap;
}

.bus-info span {
    width: 48%;
    text-align: left;
    margin-bottom: 0.4rem;
}

.bus-info span:last-child {
    text-align: right;
    color: #0044cc;
    font-weight: 600;
}

.result-info {
    text-align: center;
    margin-top: 1.5rem;
    padding: 1rem 1.5rem;
    background-color: #009688;
    color: white;
    border-radius: 25px;
    font-weight: bold;
    font-size: 1.2rem;
}

.bus-card:hover {
    background-color: #f4f4f4;
    transform: scale(1.02);
}

.footer-info {
    font-size: 0.9rem;
    color: #009688;
    text-align: center;
    margin-top: 3rem;
}

@media (max-width: 768px) {
    .header-title {
        font-size: 2rem;
        padding: 0 1rem;
    }

    .main-card {
        padding: 2rem 1rem;
    }

    .search-button button {
        padding: 0.6rem 1.5rem;
        font-size: 1rem;
        width: 90%;
    }

    .bus-card {
        padding: 1.2rem;
        margin: 1rem 0;
    }

    .bus-info {
        font-size: 1rem;
        flex-direction: column;
        align-items: flex-start;
    }

    .bus-info span {
        width: 100%;
        text-align: left !important;
    }

    .result-info {
        font-size: 1rem;
    }

    .footer-info {
        font-size: 0.8rem;
    }
}
</style>

""", unsafe_allow_html=True)

st.markdown('<div class="header-title">🚌 TamilVandi - Search Your Bus</div>', unsafe_allow_html=True)

@st.cache_data
def get_coordinates(place_name):
    geolocator = Nominatim(user_agent="tamilvandi-app")
    try:
        location = geolocator.geocode(place_name, timeout=100)
        if location:
            return location.latitude, location.longitude
    except (GeocoderTimedOut, GeocoderUnavailable):
        time.sleep(1)
        try:
            location = geolocator.geocode(place_name, timeout=100)
            if location:
                return location.latitude, location.longitude
        except:
            return None
    return None

ORS_API_KEY = "5b3ce3597851110001cf6248c23f8cc930534989a8399826ae328953"

@st.cache_data
def get_route(start_coords, end_coords):
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {'Authorization': ORS_API_KEY, 'Content-Type': 'application/json'}
    body = {'coordinates': [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]]}

    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()

        if "features" in data and data["features"]:
            geometry = data["features"][0]["geometry"]["coordinates"]
            summary = data["features"][0]["properties"]["summary"]

            duration = summary["duration"] / 60
            distance = summary["distance"] / 1000

            via_coords = geometry[::int(len(geometry)/6) or 1]
            return geometry, duration, distance, via_coords
        else:
            return None, None, None, []
    except:
        return None, None, None, []

with st.container():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        from_selected = st.selectbox("📍 From", sorted(df['FROM_1'].dropna().unique()), key="from_place")
    with col2:
        to_selected = st.selectbox("🎯 To", sorted(df['TO_2'].dropna().unique()), key="to_place")
    with col3:
        type_selected = st.selectbox("🚌 Bus Type", ['All'] + sorted(df['TYPE'].dropna().unique()), key="bus_type")

    st.markdown('<div class="search-button" style="text-align:center; margin-top:2rem;">', unsafe_allow_html=True)
    if st.button("🔍 Search Bus"):
        result = df[(df['FROM_1'] == from_selected) & (df['TO_2'] == to_selected)]
        if type_selected != 'All':
            result = result[result['TYPE'] == type_selected]

        from_coords = get_coordinates(from_selected)
        to_coords = get_coordinates(to_selected)
        _, _, distance, _ = get_route(from_coords, to_coords) if from_coords and to_coords else (None, None, None, None)

        if not result.empty:
            st.success(f"✅ {len(result)} buses found from {from_selected} to {to_selected}")
            for idx, row in result.iterrows():
                st.markdown(f"""
                    <div class="bus-card">
                        <div class="bus-info"><span>Corporation</span><span>{row['CORPORATION']}</span></div>
                        <div class="bus-info"><span>Trip Name</span><span>{row['TRIPNAME']}</span></div>
                        <div class="bus-info"><span>Departure</span><span>{row['Departure_time']}</span></div>
                        <div class="bus-info"><span>Type</span><span>{row['TYPE']}</span></div>
                        <div class="bus-info"><span>Distance</span><span>
                            <form action="" method="post">
                                <button name="show_map_button_{idx}" type="submit" style="background:none;border:none;color:#0044cc;text-decoration:underline;cursor:pointer;">
                                    {distance:.1f} km
                                </button>
                            </form>
                        </span></div>
                    </div>
                """, unsafe_allow_html=True)

                if f"show_map_button_{idx}" in st.session_state:
                    st.session_state.show_map = True

            st.markdown('<div class="result-info">Thanks for using Tamilvandi | Safe traveling 🚌</div>', unsafe_allow_html=True)
        else:
            st.warning("No matching buses found.")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.show_map:
        with st.expander("🗺️ Route Map Preview", expanded=True):
            from_coords = get_coordinates(from_selected)
            to_coords = get_coordinates(to_selected)

            if from_coords and to_coords:
                route, duration, distance, via_coords = get_route(from_coords, to_coords)

                if type_selected.lower() == "express":
                    duration *= 0.9
                elif type_selected.lower() == "deluxe":
                    duration *= 0.85

                if route:
                    hours = int(duration // 60)
                    minutes = int(duration % 60)
                    duration_str = f"{hours} hr {minutes} min" if hours else f"{minutes} min"
                    distance_str = f"{distance:.1f} km"
                    speed_kmph = (distance * 60) / duration

                    mid_lat = (from_coords[0] + to_coords[0]) / 2
                    mid_lon = (from_coords[1] + to_coords[1]) / 2
                    m = folium.Map(location=(mid_lat, mid_lon), zoom_start=8)

                    folium.Marker(from_coords, tooltip="From", icon=folium.Icon(icon='circle', color='green')).add_to(m)
                    folium.Marker(to_coords, tooltip="To", icon=folium.Icon(icon='diamond', color='red')).add_to(m)
                    folium.PolyLine(
                        [(coord[1], coord[0]) for coord in route],
                        color='blue', weight=5,
                        tooltip=f"🛣 {distance_str} | 🚀 {speed_kmph:.1f} km/h"
                    ).add_to(m)

                    st_folium(m, height=450, width=700)

                    def remove_consecutive_duplicates(lst): 
                        result = []
                        prev = None
                        for item in lst:
                            if item != prev:
                                result.append(item)
                                prev = item
                        return result

                    geolocator = Nominatim(user_agent="tamilvandi-app")
                    via_names = []
                    for coord in via_coords[1:-1]:
                        try:
                            location = geolocator.reverse((coord[1], coord[0]), timeout=10)
                            if location and location.address:
                                name = location.address.split(',')[2]
                                via_names.append(name)
                            else:
                                via_names.append("Unknown")
                        except:
                            via_names.append("Unknown")

                    via_names = remove_consecutive_duplicates(via_names)

                    if via_names:
                        via_text = " → ".join(via_names)
                        st.info(f"📏 Distance: {distance_str} | 🕓 Estimated Travel Time: {duration_str} | 🛣️ Via: {via_text}")
                    else:
                        st.info(f"📏 Distance: {distance_str} | 🕓 Estimated Travel Time: {duration_str}")
            else:
                st.warning("📍 Could not find map locations for the selected cities. Try using full names like 'Tiruchirappalli' instead of 'Trichy'.")
