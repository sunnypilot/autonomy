#!/usr/bin/env python3
import sys
import time
import argparse
import contextily as ctx
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from navigation.nav_manager import NavManager
from navigation.navd.helpers import Coordinate


class Simulator:
 @staticmethod
 def interpolate_route_points(route_geometry, interval_meters=100):
   """Interpolate points along the route at 100m (or specified) intervals"""

   if not route_geometry or len(route_geometry) < 2:
     return []

   points: list = []
   total_distance: float = 0.0
   next_target: int = interval_meters

   for idx in range(len(route_geometry) - 1):
     lat1, lon1 = route_geometry[idx][1], route_geometry[idx][0]
     lat2, lon2 = route_geometry[idx+1][1], route_geometry[idx+1][0]

     segment_distance = Coordinate(lat1, lon1).distance_to(Coordinate(lat2, lon2))

     while next_target <= total_distance + segment_distance:
       remaining = next_target - total_distance
       fraction = remaining / segment_distance
       lat_interp = lat1 + fraction * (lat2 - lat1)
       lon_interp = lon1 + fraction * (lon2 - lon1)

       points.append((lat_interp, lon_interp))
       next_target += interval_meters

     total_distance += segment_distance

   return points

 @staticmethod
 def run_simulation(destination, gps_lat=34.16207, gps_lon=-119.19657, interval=0.01):
   """Run the navigation simulation and return collected data"""
   try:
     # Initialize navigation manager
     nav_manager = NavManager(destination, (gps_lat, gps_lon))

     # Get route geometry
     route = nav_manager.nav.get_current_route()
     if not route or 'geometry' not in route:
       print("No route geometry available")
       sys.exit(1)

     route_geometry = route['geometry']
     print(f"Route has {len(route_geometry)} points, total distance: {route['total_distance']:.1f}m")
     print("Route steps:")
     for index, step in enumerate(route['steps']):
       # Find cumulative for this step
       step_closest_index = min(range(len(route['geometry'])),
                   key=lambda k: step['location'].distance_to(Coordinate(route['geometry'][k][1], route['geometry'][k][0])))
       turn_cumulative = route['cumulative_distances'][step_closest_index]
       print(f"{index+1}. {step['instruction']} at {step['location']} (cumulative: {turn_cumulative:.1f}m)")
     print()

     # Generate simulated positions every update interval, change to up your flavor
     update_interval_meters = 100
     simulated_positions = Simulator.interpolate_route_points(route_geometry, update_interval_meters)

     print(f"Generated {len(simulated_positions)} simulated positions every {update_interval_meters}m")

     print(f"Starting simulation with {len(simulated_positions)} GPS updates every {update_interval_meters}m")

     # initialize data collection empty list
     simulation_data: list = []

     for index, (lat, lon) in enumerate(simulated_positions):
       # Update GPS position
       nav_manager.update_gps_position(lon, lat)

       # Get navigation status
       status = nav_manager.get_navigation_status()

       # Collect data for this step
       step_data = {
         'step': index + 1,
         'position': (lat, lon),
         'current_maxspeed': status.get('current_maxspeed'),
         'progress': status.get('progress'),
         'current_instruction': status.get('current_instruction'),
         'upcoming_turn': status.get('upcoming_turn')
       }
       simulation_data.append(step_data)

       print(f"\nUpdate {index + 1}/{len(simulated_positions)} - Position: ({lat:.6f}, {lon:.6f})")
       if 'current_maxspeed' in status:
         print(f"Current Max Speed: {status['current_maxspeed']} mph")
       if 'progress' in status and status['progress']:
         print(f"Route Progress: {status['progress'].get('route_progress_percent', 'N/A'):.1f}%")
         distance_to_next = status['progress'].get('distance_to_next_turn')
         if distance_to_next is not None:
           print(f"Distance to next turn: {distance_to_next:.1f}m")
         else:
           print("Distance to next turn: N/A")
       else:
         print("Route Progress: N/A")

       if status.get('current_instruction'):
         current_instr = status['current_instruction']
         print(f"Current Instruction: {current_instr['instruction']}")
       else:
         print("Current Instruction: None")

       if status.get('upcoming_turn'):
         turn = status['upcoming_turn']
         distance_to_turn = status['progress'].get('distance_to_next_turn') if status.get('progress') else None
         if distance_to_turn is not None:
           print(f"Next Turn: {turn['instruction']} ({distance_to_turn:.1f}m)")
         else:
           print(f"Next Turn: {turn['instruction']} (N/A)")
       else:
         print("Next Turn: None")

       # Simulate real-time updates
       time.sleep(interval)

     print("\nSimulation completed!")
     return route, simulation_data

   except KeyboardInterrupt:
     print("\nSimulation stopped by user.")
     return None, []
   except Exception as e:
     print(f"Error: {e}")
     sys.exit(1)

 @staticmethod
 def save_animation(animation, output_file):
   """Save animation as video file"""
   try:
     animation.save(output_file, writer='ffmpeg', fps=5, dpi=150, bitrate=1800)
     print(f"High-resolution map animation saved to {output_file}")
     return output_file
   except Exception as e:
     print(f"Failed to save animation: {e}")
     return None

 @staticmethod
 def create_map_animation(route, simulation_data, output_file='navigation/debug/simulation_videos/nav_simulation.mp4'):
   if not route or not simulation_data:
     return None

   # Extract route coordinates
   route_geometry = route['geometry']
   lons = [coordinate[0] for coordinate in route_geometry]
   lats = [coordinate[1] for coordinate in route_geometry]

   # Duplicate frames for speeds under 40 mph to 'simulate' slower movement
   new_data = []
   for data in simulation_data:
     new_data.append(data)
     if (data['current_maxspeed'] or 0) < 40:
       new_data.append(data)  # duplicate frame for 2x slower

   # Update step numbers for the new data
   for i, data in enumerate(new_data):
     data['step'] = i + 1

   # Update sim data and positions
   simulation_data = new_data
   sim_lons = [data['position'][1] for data in simulation_data]
   sim_lats = [data['position'][0] for data in simulation_data]

   # Set up the figure and 2D axis
   fig = plt.figure(figsize=(16, 12), dpi=150) # this allows for a larger map. without it, it's very thin
   axes = fig.add_subplot(111, projection=ccrs.PlateCarree())

   # Plot the route
   axes.plot(lons, lats, 'b-', linewidth=4, alpha=0.8, label='Route', transform=ccrs.PlateCarree())

   # Plot turn markers, kind of weird
   for step in route['steps']:
     lon = step['location'].longitude
     lat = step['location'].latitude
     axes.scatter([lon], [lat], color='red', s=150, marker='^', label='Turn' if step == route['steps'][0] else "", transform=ccrs.PlateCarree())

   # set position
   vehicle = axes.scatter([], [], color='green', s=200, marker='o', label='Vehicle', transform=ccrs.PlateCarree())

   # Add text for navigation instructions
   instruction_text = axes.text(0.02, 0.98, '', transform=axes.transAxes,
                                fontsize=16, verticalalignment='top',
                                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))

   axes.set_xlabel('Longitude', fontsize=14)
   axes.set_ylabel('Latitude', fontsize=14)
   axes.set_title('Navigation Simulation', fontsize=18)
   
   lon_padding = 0.05  # degrees
   lat_padding = 0.05  # degrees

   axes.set_extent([min(lons) - lon_padding, max(lons) + lon_padding,
      min(lats) - lat_padding, max(lats) + lat_padding], crs=ccrs.PlateCarree())

   # Add basemap tile from osm
   ctx.add_basemap(axes, crs='EPSG:4326', source=ctx.providers.OpenStreetMap.Mapnik, zoom=16)

   axes.legend(fontsize=12)

   def animate(frame):
     """Animation function called for each frame"""
     if frame < len(simulation_data):
       data = simulation_data[frame]

       # Update vehicle position
       current_lon = sim_lons[frame]
       current_lat = sim_lats[frame]

       vehicle.set_offsets([[current_lon, current_lat]])

       # Pan map to follow vehicle, kind of cool but could be smoothened out
       zoom_level = 0.005  # degrees, about 500m I think
       axes.set_extent([current_lon - zoom_level, current_lon + zoom_level,
              current_lat - zoom_level, current_lat + zoom_level], crs=ccrs.PlateCarree())

       # Update navigation instruction text
       current_instruction = data['current_instruction']['instruction'] if data['current_instruction'] else 'none'
       next_turn = data['upcoming_turn']['instruction'] if data['upcoming_turn'] else 'none'
       progress = data['progress'].get('route_progress_percent', 0) if data['progress'] else 0
       max_speed = data['current_maxspeed'] or 'N/A'

       instruction_text.set_text(
        f'''Step {data['step']}/{len(simulation_data)}
          Position: ({current_lat:.6f}, {current_lon:.6f})
          Progress: {progress:.1f}%
          Max Speed: {max_speed} mph
          Current: {current_instruction}
          Next: {next_turn}''')

     return vehicle, instruction_text

   animation_output = animation.FuncAnimation(fig, animate, frames=len(simulation_data), interval=200, blit=False, repeat=True)
   return Simulator.save_animation(animation_output, output_file)

 @classmethod
 def main(cls):
   parser = argparse.ArgumentParser(description='Navigation Simulator')
   parser.add_argument('--destination', required=True, help='Destination address')
   parser.add_argument('--gps-lat', type=float, default=34.23305, help='Initial GPS latitude')
   parser.add_argument('--gps-lon', type=float, default=-119.17557, help='Initial GPS longitude')
   parser.add_argument('--output', type=str, default='navigation/debug/simulation_videos/nav_simulation.mp4', help='Output video file name')
   args = parser.parse_args()

   # Run simulation
   route, simulation_data = cls.run_simulation(args.destination, args.gps_lat, args.gps_lon)

   if not simulation_data:
     return

   output_file = cls.create_map_animation(route, simulation_data, args.output)

   if output_file:
     print(f"Video saved as {output_file}")
   else:
     print("Failed to create map animation")


if __name__ == "__main__":
 Simulator.main()
