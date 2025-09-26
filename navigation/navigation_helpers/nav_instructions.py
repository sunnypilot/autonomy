import capnp
import math
import os

from navigation.common.params.params import Params
from navigation.navigation_helpers.mapbox_integration import MapboxIntegration


class NavigationInstructions:
  def __init__(self):
    self.mapbox = MapboxIntegration()
    self.params = Params()
    self.params_capnp = capnp.load(os.path.join(os.path.dirname(__file__), '..', 'common', 'navigation.capnp'))

  def haversine_distance(self, lat1, lon1, lat2, lon2):
    # Radius of Earth in meters
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

  def extract_turn_direction(self, instruction):
    if 'Turn left' in instruction:
      return 'left'
    elif 'Turn right' in instruction:
      return 'right'
    else:
      return 'None'

  def get_upcoming_turn(self, current_lat, current_lon) -> str:
    route = self.get_current_route()
    if not route or not route.get('steps'):
      return 'None'
    for step in route['steps']:
      turn_dir = str(step.get('turn_direction'))
      if turn_dir and turn_dir != 'None':
        turn_lat, turn_lon = step['location']
        distance = self.haversine_distance(current_lat, current_lon, turn_lat, turn_lon)
        if distance <= 100:  # Within 100 meters
          return turn_dir
    return 'None'

  def get_route_progress(self, current_lat, current_lon):
    """Get current position on route and distance to next turn"""
    route = self.get_current_route()
    if not route or not route.get('geometry') or not route.get('steps'):
      return None

    # Find closest point on the route polyline
    min_distance = float('inf')
    closest_index = 0
    for i in range(len(route['geometry'])):
      lat, lon = route['geometry'][i][1], route['geometry'][i][0]
      dist = self.haversine_distance(current_lat, current_lon, lat, lon)
      if dist < min_distance:
        min_distance = dist
        closest_index = i
    closest_cumulative = route['cumulative_distances'][closest_index]
    current_maxspeed = route['maxspeed'][closest_index] if closest_index < len(route['maxspeed']) else None

    # Find the current step index: the highest i where the step location cumulative <= closest_cumulative
    current_step_index = -1
    for i, step in enumerate(route['steps']):
      step_closest_index = min(range(len(route['geometry'])),
                               key=lambda j: self.haversine_distance(step['location'][1], step['location'][0],
                                                                     route['geometry'][j][1], route['geometry'][j][0]))
      step_cumulative = route['cumulative_distances'][step_closest_index]
      if step_cumulative <= closest_cumulative:
        current_step_index = i
      else:
        break

    if current_step_index == -1:
      current_step = route['steps'][0] if route['steps'] else None
    else:
      current_step = route['steps'][current_step_index]

    # Next turn is the next step after current
    next_turn_index = current_step_index + 1
    next_turn = route['steps'][next_turn_index] if next_turn_index < len(route['steps']) else None
    next_turn_distance = None
    if next_turn:
      next_step_closest_index = min(range(len(route['geometry'])),
                                    key=lambda j: self.haversine_distance(next_turn['location'][1], next_turn['location'][0],
                                                                         route['geometry'][j][1], route['geometry'][j][0]))
      next_turn_distance = max(0, route['cumulative_distances'][next_step_closest_index] - closest_cumulative)

    return {
      'distance_from_route': min_distance,
      'route_position_cumulative': closest_cumulative,
      'current_step': current_step,
      'next_turn': next_turn,
      'distance_to_next_turn': next_turn_distance,
      'route_progress_percent': (closest_cumulative / max(1, route['total_distance'])) * 100,
      'current_maxspeed': current_maxspeed
    }

  def closest_point_on_segment(self, lat, lon, lat1, lon1, lat2, lon2):
    # Approximate closest point on segment in lat/lon space
    dx = lat2 - lat1
    dy = lon2 - lon1
    dxp = lat - lat1
    dyp = lon - lon1
    dot = dxp * dx + dyp * dy
    len_sq = dx * dx + dy * dy
    if len_sq == 0:
      return lat1, lon1, self.haversine_distance(lat, lon, lat1, lon1)
    param = dot / len_sq
    param = max(0, min(1, param))
    closest_lat = lat1 + param * dx
    closest_lon = lon1 + param * dy
    dist = self.haversine_distance(lat, lon, closest_lat, closest_lon)
    return closest_lat, closest_lon, dist

  def get_current_route(self):
    param_value = self.params.get("MapboxSettings", encoding='bytes')
    if not param_value:
      return None
    with self.params_capnp.MapboxSettings.from_bytes(param_value) as settings:
      route = settings.navData.route
      steps = []
      for step in route.steps:
        steps.append({
          'instruction': step.instruction,
          'distance': step.distance,
          'duration': step.duration,
          'maneuver': step.maneuver,
          'location': (step.location.longitude, step.location.latitude),
          'turn_direction': self.extract_turn_direction(step.instruction)
        })
      geometry = [(coord.longitude, coord.latitude) for coord in route.geometry]
      cumulative_distances = [0.0]
      for j in range(1, len(geometry)):
        dist = self.haversine_distance(geometry[j-1][1], geometry[j-1][0], geometry[j][1], geometry[j][0])
        cumulative_distances.append(cumulative_distances[-1] + dist)
      maxspeed = [(ms.speed, ms.unit) for ms in route.maxspeed]
      return {
        'steps': steps,
        'total_distance': route.totalDistance,
        'total_duration': route.totalDuration,
        'geometry': geometry,
        'cumulative_distances': cumulative_distances,
        'maxspeed': maxspeed
      }
