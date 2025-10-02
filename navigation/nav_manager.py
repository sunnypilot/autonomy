#!/usr/bin/env python3

from navigation.navigation_helpers.mapbox_integration import MapboxIntegration
from navigation.navigation_helpers.nav_instructions import NavigationInstructions
from navigation.navd.helpers import Coordinate


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
      self.update_gps_position(0.0, 0.0)  # Default position

    # Set destination and generate route
    self._setup_destination(destination)

  def _read_mapbox_token(self) -> str:
    """Read Mapbox token from params"""
    token = str(self.mapbox.params.get("MapboxToken", encoding='utf8'))
    return token

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

  def _parse_step(self, step):
    """Parse Coordinate objects in step dict to dict format"""
    if step and 'location' in step and isinstance(step['location'], Coordinate):
      step = step.copy()
      step['location'] = {
        'latitude': step['location'].latitude,
        'longitude': step['location'].longitude
      }
    return step

  def update(self, gps_lat=None, gps_lon=None):
    """Update method called at 5Hz (5 frames per second)"""
    self.frame += 1

    # Update GPS position if provided
    if gps_lat is not None and gps_lon is not None:
      self.update_gps_position(gps_lon, gps_lat)

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
      "upcoming_turn": self._parse_step(progress.get('next_turn')) if progress else None,
      "current_instruction": self._parse_step(progress.get('current_step')) if progress else None
    }

    # Convert maxspeed from km/h to mph if present
    if progress and 'current_maxspeed' in progress and progress['current_maxspeed']:
        speed_kmh, unit = progress['current_maxspeed']
        if self.is_metric:
          status['current_maxspeed'] = speed_kmh
        else:
          status['current_maxspeed'] = round(speed_kmh * 0.621371)

    return status
