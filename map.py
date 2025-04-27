import pandas as pd
import folium
import requests
import math
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import os
import json

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

def calculate_priority_weights(coordinates_data):
    priority_map = {'High': 3, 'Mid': 2, 'Low': 1}
    return [priority_map.get(item['priority'], 2) for item in coordinates_data]

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c * 1000

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

def get_weather_impact(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(url)
        data = response.json()
        
        temperature = data.get('current_weather', {}).get('temperature', 0)
        windspeed = data.get('current_weather', {}).get('windspeed', 0)
        
        if temperature > 35 or windspeed > 20:
            return 1.3
        elif temperature < 0 or windspeed > 15:
            return 1.2
        else:
            return 1.0
    except Exception:
        return 1.0

def estimate_traffic_impact(lat, lon):
    from datetime import datetime
    current_hour = datetime.now().hour
    
    if 7 <= current_hour <= 9 or 16 <= current_hour <= 18:
        return 1.5
    return 1.0

def solve_priority_vrp(coordinates_data):
    coordinates = [item['coordinates'] for item in coordinates_data]
    priority_weights = calculate_priority_weights(coordinates_data)

    distance_matrix = []
    for i in range(len(coordinates)):
        row = []
        for j in range(len(coordinates)):
            if i == j:
                row.append(0)
            else:
                dist = haversine_distance(
                    coordinates[i][0], coordinates[i][1], 
                    coordinates[j][0], coordinates[j][1]
                )
                row.append(int(dist / priority_weights[j]))
        distance_matrix.append(row)

    manager = pywrapcp.RoutingIndexManager(
        len(distance_matrix), 1, 0
    )
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        route = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route.append(manager.IndexToNode(index))
        return route
    else:
        raise Exception("Could not find an optimized route")

def visualize_route(coordinates, route_geometry, output_file='N:/proj/nuel/roadmap_route.html'):
    # Ensure coordinates are valid and formatted
    coordinates = [[float(lat), float(lon)] for lat, lon in coordinates]

    # Initialize the map at the first coordinate
    m = folium.Map(location=coordinates[0], zoom_start=13)

    # Add markers for each coordinate
    for i, (lat, lon) in enumerate(coordinates):
        folium.Marker(
            location=[lat, lon],
            popup=f"Store {i+1}",
            icon=folium.Icon(color="green")
        ).add_to(m)

    # Draw the route as a red polyline
    folium.PolyLine(
        locations=route_geometry,
        color="red",
        weight=5,
        opacity=0.7
    ).add_to(m)

    # Save the map to the specified HTML file
    m.save(output_file)

    # Return the file:/// formatted link
    return f"file:///{os.path.abspath(output_file).replace(os.sep, '/')}"


def main():
    # Input file paths
    input_file_path = r"N:\proj\nuel\coordinates.xlsx"
    output_json_path = r"N:\proj\nuel\output.json"  # Change to JSON file path

    # Serial number range input
    start_serial = int(input("Enter the starting serial number: "))
    end_serial = int(input("Enter the ending serial number: "))

    # Read and filter data
    df = read_excel_data(input_file_path, start_serial, end_serial)
    if df.empty:
        print("No data found.")
        return

    # Get coordinates with priorities
    coordinates_data = get_coordinates_with_priority(df)
    coordinates = [item['coordinates'] for item in coordinates_data]

    # Calculate route and get route geometry
    route_geometry, total_distance = calculate_roadmap_route(coordinates)

    # Solve priority-based VRP
    optimized_route_indices = solve_priority_vrp(coordinates_data)
    optimized_coordinates = [coordinates[idx] for idx in optimized_route_indices]

    # Visualize the optimized route in a single HTML file
    html_file_path = os.path.abspath(r"N:\proj\nuel\roadmap_route.html")
    html_file_url = visualize_route(optimized_coordinates, route_geometry, html_file_path)

    # Prepare output data
    output_data = {
        "metadata": {
            "Total Distance (km)": total_distance / 1000,
            "HTML File": html_file_url,
            "Estimated Time Taken (hours)": total_distance / 40000  # Assuming 40 km/h average speed
        },
        "coordinates": [
            {"Latitude": lat, "Longitude": lon}
            for lat, lon in optimized_coordinates
        ]
    }

    # Save the output data as a JSON file
    with open(output_json_path, 'w') as json_file:
        json.dump(output_data, json_file, indent=4)  # Use indent for pretty-printing

    print(f"Output saved to {output_json_path}")
    print(f"Route map saved to {html_file_url}")

if __name__ == "__main__":
    main()
