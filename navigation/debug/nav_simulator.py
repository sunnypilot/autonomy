#!/usr/bin/env python3
import sys
import time
import argparse
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from navigation.navigation_helpers.nav_instructions import NavigationInstructions
from navigation.nav_manager import NavManager
import contextily as ctx
import cartopy.crs as ccrs


def interpolate_route_points(route_geometry, interval_meters=100):
  nav_instructions = NavigationInstructions()
  haversine_distance = nav_instructions.haversine_distance
  """Interpolate points along the route at specified intervals"""
  if not route_geometry or len(route_geometry) < 2:
    return []

  points = []
  total_distance = 0.0
  next_target = interval_meters

  for i in range(len(route_geometry) - 1):
    lat1, lon1 = route_geometry[i][1], route_geometry[i][0]
    lat2, lon2 = route_geometry[i+1][1], route_geometry[i+1][0]

    segment_distance = haversine_distance(lat1, lon1, lat2, lon2)

    while next_target <= total_distance + segment_distance:
      remaining = next_target - total_distance
      fraction = remaining / segment_distance
      lat_interp = lat1 + fraction * (lat2 - lat1)
      lon_interp = lon1 + fraction * (lon2 - lon1)

      points.append((lat_interp, lon_interp))
      next_target += interval_meters

    total_distance += segment_distance

  return points


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
    for j, step in enumerate(route['steps']):
      # Find cumulative for this step
      step_closest_index = min(range(len(route['geometry'])),
                               key=lambda k: nav_manager.nav.haversine_distance(step['location'][1], step['location'][0],
                               route['geometry'][k][1], route['geometry'][k][0]))
      turn_cumulative = route['cumulative_distances'][step_closest_index]
      print(f"  {j+1}. {step['instruction']} at {step['location']} (cumulative: {turn_cumulative:.1f}m)")
    print()

    # Generate simulated positions every 100 meters
    simulated_positions = interpolate_route_points(route_geometry, 100)

    print(f"Generated {len(simulated_positions)} simulated positions every 100m")

    print(f"Starting simulation with {len(simulated_positions)} GPS updates every 100m")

    # Collect simulation data
    simulation_data = []

    for i, (lat, lon) in enumerate(simulated_positions):
      # Update GPS position
      nav_manager.update_gps_position(lon, lat)

      # Get navigation status
      status = nav_manager.get_navigation_status()

      # Collect data for this step
      step_data = {
        'step': i + 1,
        'position': (lat, lon),
        'current_maxspeed': status.get('current_maxspeed'),
        'progress': status.get('progress'),
        'current_instruction': status.get('current_instruction'),
        'upcoming_turn': status.get('upcoming_turn')
      }
      simulation_data.append(step_data)

      print(f"\nUpdate {i+1}/{len(simulated_positions)} - Position: ({lat:.6f}, {lon:.6f})")
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


def save_animation(anim, output_file):
  """Save animation as MP4"""
  try:
    anim.save(output_file, writer='ffmpeg', fps=5, dpi=150, bitrate=1800)
    print(f"High-resolution map animation saved to {output_file}")
    return output_file
  except Exception as e:
    print(f"Failed to save animation: {e}")
    return None


def create_map_animation(route, simulation_data, output_file='navigation/debug/simulation_videos/nav_simulation.mp4'):
  """Create a high-resolution zoomable map-based animated simulation video"""
  if not route or not simulation_data:
    return None

  # Extract route coordinates
  route_geometry = route['geometry']
  lons = [coord[0] for coord in route_geometry]
  lats = [coord[1] for coord in route_geometry]

  # Duplicate frames for speeds under 40 mph to `simulate` slower movement
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

  # Set up the figure and 2D axis with map projection - high resolution for zoomability
  fig = plt.figure(figsize=(16, 12), dpi=150)  # High resolution figure
  ax = fig.add_subplot(111, projection=ccrs.PlateCarree())

  # Plot the route
  ax.plot(lons, lats, 'b-', linewidth=4, alpha=0.8, label='Route', transform=ccrs.PlateCarree())

  # Plot turn markers
  for step in route['steps']:
    lon, lat = step['location']
    ax.scatter([lon], [lat], color='red', s=150, marker='^', label='Turn' if step == route['steps'][0] else "", transform=ccrs.PlateCarree())

  # Initialize vehicle position
  vehicle = ax.scatter([], [], color='green', s=200, marker='o', label='Vehicle', transform=ccrs.PlateCarree())

  # Add text for navigation instructions - larger font
  instruction_text = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                fontsize=16, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))

  # Set labels and title
  ax.set_xlabel('Longitude', fontsize=14)
  ax.set_ylabel('Latitude', fontsize=14)
  ax.set_title('Navigation Simulation', fontsize=18)

  # Set extent with generous padding to cover a large map area
  lon_padding = 0.05  # degrees
  lat_padding = 0.05  # degrees

  ax.set_extent([min(lons) - lon_padding, max(lons) + lon_padding,
         min(lats) - lat_padding, max(lats) + lat_padding], crs=ccrs.PlateCarree())

  # Add basemap tile with auto zoom for best quality across the entire route
  ctx.add_basemap(ax, crs='EPSG:4326', source=ctx.providers.OpenStreetMap.Mapnik, zoom=16)

  # Add legend
  ax.legend(fontsize=12)

  def animate(frame):
    """Animation function called for each frame"""
    if frame < len(simulation_data):
      data = simulation_data[frame]

      # Update vehicle position
      current_lon = sim_lons[frame]
      current_lat = sim_lats[frame]

      vehicle.set_offsets([[current_lon, current_lat]])

      # Pan map to follow vehicle, kind of cool
      zoom_level = 0.005  # degrees, about 500m
      ax.set_extent([current_lon - zoom_level, current_lon + zoom_level,
                     current_lat - zoom_level, current_lat + zoom_level], crs=ccrs.PlateCarree())

      # Update navigation instruction text
      current_instr = data['current_instruction']['instruction'] if data['current_instruction'] else 'None'
      next_turn = data['upcoming_turn']['instruction'] if data['upcoming_turn'] else 'None'
      progress = data['progress'].get('route_progress_percent', 0) if data['progress'] else 0
      max_speed = data['current_maxspeed'] or 'N/A'

      instruction_text.set_text(f'''Step {data['step']}/{len(simulation_data)}
Position: ({current_lat:.6f}, {current_lon:.6f})
Progress: {progress:.1f}%
Max Speed: {max_speed} mph
Current: {current_instr}
Next: {next_turn}''')

    return vehicle, instruction_text

  # Create animation with fixed interval, slower speed sections have duplicated frames
  anim = animation.FuncAnimation(fig, animate, frames=len(simulation_data),
                interval=200, blit=False, repeat=True)

  return save_animation(anim, output_file)


def main():
  parser = argparse.ArgumentParser(description='Navigation Simulator with Map Animation')
  parser.add_argument('--destination', required=True, help='Destination address')
  parser.add_argument('--gps-lat', type=float, default=34.23305, help='Initial GPS latitude')
  parser.add_argument('--gps-lon', type=float, default=-119.17557, help='Initial GPS longitude')
  parser.add_argument('--interval', type=float, default=0.01, help='Update interval in seconds')
  parser.add_argument('--output', type=str, default='navigation/debug/simulation_videos/nav_simulation.mp4', help='Output video file name')
  args = parser.parse_args()

  # Run simulation
  route, simulation_data = run_simulation(args.destination, args.gps_lat, args.gps_lon, args.interval)

  if not simulation_data:
    return

  # Create map animation
  output_file = create_map_animation(route, simulation_data, args.output)

  if output_file:
    print(f"Video saved as {output_file} - open with your preferred video player")
  else:
    print("Failed to create map animation")


if __name__ == "__main__":
  main()
