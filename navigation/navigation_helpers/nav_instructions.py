from navigation.common.params.params import Params
from navigation.navd.helpers import Coordinate, string_to_direction
from navigation.common.capnp import navigation


class NavigationInstructions:
  def __init__(self):
    self.params = Params()
    self.params_capnp = navigation
    self.coord = Coordinate(0, 0)

  def get_upcoming_turn(self, current_lat, current_lon) -> str:
    route = self.get_current_route()
    if not route or not route.get('steps'):
      return 'none'
    self.coord.latitude = current_lat
    self.coord.longitude = current_lon
    for step in route['steps']:
      turn_dir = str(step.get('turn_direction'))
      if turn_dir and turn_dir != 'none':
        distance = self.coord.distance_to(step['location'])
        if distance <= 100:  # Within 100 meters
          return turn_dir
    return 'none'

  def get_route_progress(self, current_lat, current_lon):
    """Get current position on route and distance to next turn"""
    route = self.get_current_route()
    if not route or not route.get('geometry') or not route.get('steps'):
      return None

    self.coord.latitude = current_lat
    self.coord.longitude = current_lon

    temp_coord = Coordinate(0, 0)

    # Find closest point on the route polyline
    min_distance = float('inf')
    closest_index = 0
    for i in range(len(route['geometry'])):
      lat, lon = route['geometry'][i][1], route['geometry'][i][0]
      temp_coord.latitude = lat
      temp_coord.longitude = lon
      dist = self.coord.distance_to(temp_coord)
      if dist < min_distance:
        min_distance = dist
        closest_index = i
    closest_cumulative = route['cumulative_distances'][closest_index]
    current_maxspeed = route['maxspeed'][closest_index] if closest_index < len(route['maxspeed']) else None

    # Find the current step index: the highest i where the step location cumulative <= closest_cumulative
    current_step_index = -1
    for i, step in enumerate(route['steps']):
      if step['cumulative_distance'] <= closest_cumulative:
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
      next_turn_distance = max(0, next_turn['cumulative_distance'] - closest_cumulative)

    return {
      'distance_from_route': min_distance,
      'route_position_cumulative': closest_cumulative,
      'current_step': current_step,
      'next_turn': next_turn,
      'distance_to_next_turn': next_turn_distance,
      'route_progress_percent': (closest_cumulative / max(1, route['total_distance'])) * 100,
      'current_maxspeed': current_maxspeed
    }

  def get_current_route(self):
    param_value = self.params.get("MapboxSettings", encoding='bytes')
    if not param_value:
      return None
    with self.params_capnp.MapboxSettings.from_bytes(param_value) as settings:
      route = settings.navData.route
      steps = []
      geometry = [(coord.longitude, coord.latitude) for coord in route.geometry]
      cumulative_distances = [0.0]
      for j in range(1, len(geometry)):
        coord1 = Coordinate(geometry[j-1][1], geometry[j-1][0])
        coord2 = Coordinate(geometry[j][1], geometry[j][0])
        dist = coord1.distance_to(coord2)
        cumulative_distances.append(cumulative_distances[-1] + dist)
      maxspeed = [(ms.speed, ms.unit) for ms in route.maxspeed]
      for step in route.steps:
        location = Coordinate(step.location.latitude, step.location.longitude)
        closest_index = min(range(len(geometry)), key=lambda j: location.distance_to(Coordinate(geometry[j][1], geometry[j][0])))
        cumulative_distance = cumulative_distances[closest_index]
        steps.append({
          'instruction': step.instruction,
          'distance': step.distance,
          'duration': step.duration,
          'maneuver': step.maneuver,
          'location': location,
          'turn_direction': string_to_direction(step.instruction),
          'cumulative_distance': cumulative_distance
        })
      return {
        'steps': steps,
        'total_distance': route.totalDistance,
        'total_duration': route.totalDuration,
        'geometry': geometry,
        'cumulative_distances': cumulative_distances,
        'maxspeed': maxspeed
      }
