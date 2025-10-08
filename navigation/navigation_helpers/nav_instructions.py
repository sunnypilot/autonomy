from navigation.common.params.params import Params
from navigation.common.constants import CV
from navigation.navd.helpers import Coordinate, string_to_direction
from messaging.messenger import schema


class NavigationInstructions:
  def __init__(self):
    self.params = Params()
    self.autonomy_schema = schema
    self.coord = Coordinate(0, 0)
    self._cached_route = None
    self._route_loaded = False

  def get_route_progress(self, current_lat, current_lon):
    """Get current position on route and distance to next turn"""
    route = self.get_current_route()
    if not route or not route['geometry'] or not route['steps']:
      return None

    self.coord.latitude = current_lat
    self.coord.longitude = current_lon

    # Find closest point on the route polyline
    closest_index, min_distance = min(((i, self.coord.distance_to(Coordinate(latitude, longitude))) for i, (longitude, latitude) in enumerate(route['geometry'])), key=lambda x: x[1])
    closest_cumulative = route['cumulative_distances'][closest_index]

    # Find the current step index: the highest i where the step location cumulative <= closest_cumulative
    current_step_index = max((i for i, step in enumerate(route['steps']) if step['cumulative_distance'] <= closest_cumulative), default=-1)
    current_step = route['steps'][current_step_index] if current_step_index >= 0 else (route['steps'][0] if route['steps'] else None)

    # Next turn is the next step after current
    next_turn_index = current_step_index + 1
    next_turn = route['steps'][next_turn_index] if next_turn_index < len(route['steps']) else None
    next_turn_distance = max(0, next_turn['cumulative_distance'] - closest_cumulative) if next_turn else None

    current_maxspeed = current_step['maxspeed'] if current_step else None

    return {'distance_from_route': min_distance, 'route_position_cumulative': closest_cumulative, 'current_step': current_step, 'next_turn': next_turn, 'distance_to_next_turn': next_turn_distance, 'route_progress_percent': (closest_cumulative / max(1, route['total_distance'])) * 100, 'current_maxspeed': current_maxspeed}

  def get_current_route(self):
    if self._route_loaded and self._cached_route is not None:
      return self._cached_route

    param_value = self.params.get("MapboxSettings", encoding='bytes')
    if not param_value:
      return None
    with self.autonomy_schema.MapboxSettings.from_bytes(param_value) as settings:
      route = settings.navData.route
      steps = []
      geometry = [(coord.longitude, coord.latitude) for coord in route.geometry]
      cumulative_distances = [0.0]
      cumulative_distances.extend(cumulative_distances[-1] + Coordinate(geometry[j-1][1], geometry[j-1][0]).distance_to(Coordinate(geometry[j][1], geometry[j][0])) for j in range(1, len(geometry)))
      maxspeed = [(ms.speed, ms.unit) for ms in route.maxspeed]
      for step in route.steps:
        location = Coordinate(step.location.latitude, step.location.longitude)
        closest_index = min(range(len(geometry)), key=lambda i: location.distance_to(Coordinate(geometry[i][1], geometry[i][0])))
        cumulative_distance = cumulative_distances[closest_index]
        steps.append({
          'instruction': step.instruction,
          'distance': step.distance,
          'duration': step.duration,
          'maneuver': step.maneuver,
          'location': location,
          'turn_direction': string_to_direction(step.instruction),
          'cumulative_distance': cumulative_distance,
          'maxspeed': maxspeed[closest_index] if closest_index < len(maxspeed) else None
        })
      self._cached_route = {'steps': steps, 'total_distance': route.totalDistance, 'total_duration': route.totalDuration, 'geometry': geometry, 'cumulative_distances': cumulative_distances, 'maxspeed': maxspeed}
      self._route_loaded = True
      return self._cached_route

  def clear_route_cache(self):
    self._cached_route = None
    self._route_loaded = False

  def get_upcoming_turn_from_progress(self, progress, current_lat, current_lon) -> str:
    if progress and progress['next_turn']:
      self.coord.latitude = current_lat
      self.coord.longitude = current_lon
      distance = self.coord.distance_to(progress['next_turn']['location'])
      if distance <= 40:
        turn_dir = str(progress['next_turn']['turn_direction'])
        if turn_dir != 'none':
          return turn_dir
    return 'none'

  def get_current_speed_limit_from_progress(self, progress, is_metric: bool) -> int:
    if progress and progress['current_maxspeed']:
      speed, _ = progress['current_maxspeed']
      if is_metric:
        return int(speed)
      else:
        return int(round(speed * CV.KPH_TO_MPH))
    return 0
