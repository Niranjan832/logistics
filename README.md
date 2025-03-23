# Route Optimization with Priority-Based VRP

## Overview
This project implements a route optimization solution using a priority-based Vehicle Routing Problem (VRP) approach. It integrates data from an Excel file, calculates road distances via OSRM (Open Source Routing Machine) and Google Maps, and applies a metaheuristic approach for optimized route planning.

## Features
- Reads location and priority data from an Excel file.
- Calculates road distances using OSRM and Google Maps APIs.
- Uses the Haversine formula for approximate distances.
- Incorporates weather and traffic impact factors.
- Applies metaheuristic algorithms for priority-based optimization.
- Generates an interactive route map using Folium.
- Outputs optimized routes as a JSON file.

## Dependencies
Ensure you have the following dependencies installed:
```bash
pip install pandas folium requests ortools numpy openpyxl
```

## File Structure
- `coordinates.xlsx` - Input Excel file containing location data.
- `roadmap_route.html` - Generated route visualization.
- `output.json` - JSON output with optimized routes and metadata.
- `main.py` - The main script for route optimization.

## Usage
1. Update the `input_file_path` variable with the correct Excel file path.
2. Run the script:
```bash
python main.py
```
3. Enter the serial number range when prompted.
4. The optimized route and map visualization will be generated.

## Data Handling
The script extracts store latitude, longitude, and priority levels from the Excel file. It assigns weights to priority levels (`High: 3`, `Mid: 2`, `Low: 1`) and computes an adjusted distance matrix.

## Routing Algorithm
- The OSRM API is used to compute road distances.
- Google Maps API can be integrated for additional accuracy.
- A metaheuristic approach (such as Genetic Algorithm or Simulated Annealing) is used to optimize the route order based on priority weights and distance constraints.
- OR-Tools (Google) is employed for solving the VRP efficiently.

## Output
The output JSON contains:
- Total distance (km)
- Estimated travel time (hours)
- Optimized route coordinates
- Path to the generated HTML map

## Notes
- Ensure an internet connection is available for API requests.
- If OSRM is unavailable, the script falls back to Haversine distances.
- The metaheuristic optimization method can be tuned further for better results.

## Future Enhancements
- Dynamic rerouting based on real-time traffic.
- Improved metaheuristic algorithms for faster optimization.
- Mobile app integration for real-time navigation.

