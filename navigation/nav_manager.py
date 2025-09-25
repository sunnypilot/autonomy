#!/usr/bin/env python3
import sys
import time
import argparse

from navigation.navigation_helpers.mapbox_integration import MapboxIntegration
from navigation.navigation_helpers.nav_instructions import NavigationInstructions


class NavManager:
  def __init__(self, destination, initial_gps=None):
    self.mapbox = MapboxIntegration()
    self.nav = NavigationInstructions()
    self.frame = 0
    self.is_metric = bool(self.mapbox.params.get('IsMetric', False))

    # Get Mapbox token from params (stored as string)
    self.token = self._read_mapbox_token()

    # Set initial GPS position if provided, otherwise use a default
    if initial_gps:
      self.update_gps_position(initial_gps[1], initial_gps[0])  # lon, lat
    else:
      # Set a default GPS position near the destination for route generation
      # This will be updated later with real GPS data
      self.update_gps_position(-119.19657, 34.16207)  # Default position

    # Set destination and generate route
    self._setup_destination(destination)

  def _read_mapbox_token(self):
    """Read Mapbox token from params"""
    token_bytes = self.mapbox.params.get('MapboxToken', encoding='bytes')
    return token_bytes.decode('utf-8') if token_bytes else ''

  def _setup_destination(self, destination):
    """Set up navigation destination and generate route"""
    postvars = {
      "place_name": destination
    }

    postvars, valid_addr = self.mapbox.set_destination(postvars, False)

    if not valid_addr:
      raise ValueError(f"Failed to geocode destination: {destination}")

    # Verify route was generated
    route = self.nav.get_current_route()
    if not route or len(route['steps']) == 0:
      raise ValueError("Failed to generate route to destination")

  def update_gps_position(self, longitude, latitude):
    """Update current GPS position"""
    self.mapbox.update_gps_position(longitude, latitude)

  def update(self):
    """Update method called at 5Hz (5 frames per second)"""
    self.frame += 1

    # Update params every 3 seconds (15 frames at 5Hz)
    if self.frame % 15 == 0:
      self.token = self._read_mapbox_token()
      self.is_metric = bool(self.mapbox.params.get('IsMetric', False))

  def get_navigation_status(self):
    """Get current navigation status including position, progress, and next turn"""
    # Get current position from MapboxIntegration
    current_lon, current_lat = self.mapbox.get_last_longitude_latitude()

    if current_lat == 0.0 and current_lon == 0.0:
      return {"error": "GPS position not set"}

    # Get navigation data from NavigationInstructions
    progress = self.nav.get_route_progress(current_lat, current_lon)
    route = self.nav.get_current_route()

    # Get destination from stored settings
    dest_lat = route['geometry'][-1][1] if route and route['geometry'] else 0.0
    dest_lon = route['geometry'][-1][0] if route and route['geometry'] else 0.0

    status = {
      "current_position": {
        "latitude": current_lat,
        "longitude": current_lon
      },
      "destination": {
        "latitude": dest_lat,
        "longitude": dest_lon
      },
      "route_info": {
        "total_steps": len(route['steps']) if route else 0,
        "total_distance": route['total_distance'] if route else 0,
        "total_duration": route['total_duration'] if route else 0
      },
      "progress": progress,
      "upcoming_turn": progress.get('next_turn') if progress else None,
      "current_instruction": progress.get('current_step') if progress else None
    }

    # Convert maxspeed from km/h to mph if present
    if progress and 'current_maxspeed' in progress and progress['current_maxspeed']:
        speed_kmh, unit = progress['current_maxspeed']
        if self.is_metric:
          status['current_maxspeed'] = speed_kmh
        else:
          status['current_maxspeed'] = round(speed_kmh * 0.621371)

    return status

def main():
  parser = argparse.ArgumentParser(description='Navigation Manager')
  parser.add_argument('--destination', required=True, help='Destination address')
  parser.add_argument('--gps-lat', type=float, help='Initial GPS latitude')
  parser.add_argument('--gps-lon', type=float, help='Initial GPS longitude')
  parser.add_argument('--update-interval', type=int, default=5, help='GPS update interval in seconds')

  args = parser.parse_args()

  # Prepare initial GPS if provided
  initial_gps = None
  if args.gps_lat is not None and args.gps_lon is not None:
    initial_gps = (args.gps_lat, args.gps_lon)

  try:
    # Initialize navigation manager
    nav_manager = NavManager(args.destination, initial_gps)

    # Keep running at 5Hz (5 frames per second)
    while True:
      # Update at 5Hz (every 0.2 seconds)
      nav_manager.update()
      time.sleep(0.2)  # 1/5 = 0.2 seconds

  except KeyboardInterrupt:
    print("\nNavigation manager stopped.")
  except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)


if __name__ == "__main__":
  main()
