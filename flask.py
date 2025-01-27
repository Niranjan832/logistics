from flask import Flask, render_template_string, request, send_from_directory
import pandas as pd
import folium
import requests
import math
import os
import json
from threading import Timer
import webbrowser

app = Flask(__name__)

# Path to the output JSON file and HTML file for the map
OUTPUT_JSON_PATH = r"N:\proj\nuel\output.json"
HTML_FILE_PATH = r"N:\proj\nuel\roadmap_route.html"

def open_browser():
    """Open the default web browser to the Flask app's URL."""
    webbrowser.open_new("http://127.0.0.1:5000/")

def read_excel_data(file_path, start_serial, end_serial):
    df = pd.read_excel(file_path)
    df = df[(df['s.no'] >= start_serial) & (df['s.no'] <= end_serial)]
    return df

def get_coordinates_with_priority(df):
    coordinates_data = []
    for _, row in df.iterrows():
        lat, lon = row['Store_Latitude'], row['Store_Longitude']
        priority = row.get('Priority', 'Mid')
        coordinates_data.append({
            'coordinates': (lat, lon),
            'priority': priority
        })
    return coordinates_data

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of the Earth in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c * 1000  # Return distance in meters

def calculate_roadmap_route(coordinates):
    coordinates_str = ";".join([f"{lon},{lat}" for lat, lon in coordinates])
    url = f"http://router.project-osrm.org/route/v1/driving/{coordinates_str}?overview=full&geometries=geojson"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['code'] == 'Ok':
            route_geometry = data['routes'][0]['geometry']['coordinates']
            total_distance = data['routes'][0]['distance']
            return [(lat, lon) for lon, lat in route_geometry], total_distance
        else:
            raise Exception(f"OSRM API error: {data['message']}")
    else:
        raise Exception(f"Failed to connect to OSRM API: {response.status_code}")

def visualize_route(coordinates, route_geometry):
    m = folium.Map(location=coordinates[0], zoom_start=13)
    
    for i, (lat, lon) in enumerate(coordinates):
        folium.Marker(location=[lat, lon], popup=f"Store {i+1}").add_to(m)

    folium.PolyLine(locations=route_geometry, color="red", weight=5).add_to(m)
    
    m.save(HTML_FILE_PATH)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start_serial = int(request.form.get('start_serial'))
        end_serial = int(request.form.get('end_serial'))
        
        input_file_path = r"N:\proj\nuel\coordinates.xlsx"
        df = read_excel_data(input_file_path, start_serial, end_serial)
        
        if df.empty:
            return "No data found."
        
        coordinates_data = get_coordinates_with_priority(df)
        coordinates = [item['coordinates'] for item in coordinates_data]
        
        route_geometry, total_distance = calculate_roadmap_route(coordinates)
        
        visualize_route(coordinates_data, route_geometry)

        output_data = {
            "metadata": {
                "Total Distance (km)": total_distance / 1000,
                "HTML File": HTML_FILE_PATH,
                "Estimated Time Taken (hours)": total_distance / 40000  # Assuming average speed of 40 km/h
            },
            "coordinates": [{"Latitude": lat, "Longitude": lon} for lat, lon in coordinates]
        }

        with open(OUTPUT_JSON_PATH, 'w') as json_file:
            json.dump(output_data, json_file)

        return render_template_string("""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Route Planner</title>
                <style>
                    body {
                        font-family: Arial;
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .input-container {
                        display: grid;
                        grid-template-columns: repeat(3, 1fr);
                        gap: 20px;
                        margin-bottom: 30px;
                        background-color: #f5f5f5;
                        padding: 20px;
                        border-radius: 8px;
                    }
                    .input-group {
                        display: flex;
                        flex-direction: column;
                    }
                    .input-group label {
                        margin-bottom: 5px;
                        font-weight: bold;
                    }
                    .input-group input {
                        padding: 8px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                    }
                    button {
                        background-color: #4CAF50;
                        color: white;
                        padding: 10px 20px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                    }
                    button:hover {
                        background-color: #45a049;
                    }
                </style>
            </head>
            <body>
                <h1>Route Planner</h1>
                
                <form method="POST">
                    <div class="input-container">
                        <div class="input-group">
                            <label for="start_serial">Start Serial:</label>
                            <input type="number" id="start_serial" name="start_serial" required>
                        </div>
                        <div class="input-group">
                            <label for="end_serial">End Serial:</label>
                            <input type="number" id="end_serial" name="end_serial" required>
                        </div>
                    </div>
                    
                    <button type="submit">Calculate Route</button>
                </form>

                <h2>Results</h2>
                <p>Total Distance: {{ metadata["Total Distance (km)"] }} km</p>
                <p>Estimated Time: {{ metadata["Estimated Time Taken (hours)"] }} hours</p>

                <iframe src="{{ url_for('show_map') }}" width="100%" height="600" frameborder="0"></iframe>
            </body>
            </html>
        """, metadata=output_data["metadata"])

@app.route('/map')
def show_map():
    return send_from_directory(os.path.dirname(HTML_FILE_PATH), os.path.basename(HTML_FILE_PATH))

if __name__ == '__main__':
    Timer(1, open_browser).start()  # Open browser after a short delay
    app.run(debug=True)
