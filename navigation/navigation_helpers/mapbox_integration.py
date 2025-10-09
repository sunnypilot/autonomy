from urllib.parse import quote
import requests
from navigation.common.params.params import Params
from navigation.navd.helpers import Coordinate
from messaging.messenger import schema


class MapboxIntegration:
  def __init__(self):
    self.params = Params()
    self.autonomy_schema = schema

  def get_public_token(self) -> str:
    token = str(self.params.get('MapboxToken', return_default=True))
    return token

  def _populate_route(self, settings, route_data) -> None:
    settings.navData.route.totalDistance = route_data['total_distance']
    settings.navData.route.totalDuration = route_data['total_duration']
    route_steps = settings.navData.route.init('steps', len(route_data['steps']))
    for idx, step in enumerate(route_data['steps']):
      route_steps[idx].instruction = step['instruction']
      route_steps[idx].distance = step['distance']
      route_steps[idx].duration = step['duration']
      route_steps[idx].maneuver = step['maneuver']
      route_steps[idx].location.longitude = step['location'].longitude
      route_steps[idx].location.latitude = step['location'].latitude
      route_steps[idx].modifier = step['modifier']
    route_geometry = settings.navData.route.init('geometry', len(route_data['geometry']))
    for idx, coord in enumerate(route_data['geometry']):
      route_geometry[idx].longitude = coord[0]
      route_geometry[idx].latitude = coord[1]
    maxspeed_entries = settings.navData.route.init('maxspeed', len(route_data['maxspeed']))
    for idx, ms in enumerate(route_data['maxspeed']):
      maxspeed_entries[idx].speed = ms['speed']
      maxspeed_entries[idx].unit = ms['unit']

  def set_destination(self, postvars, current_lon, current_lat) -> tuple[dict, bool]:
    if 'latitude' in postvars and 'longitude' in postvars:
      self.nav_confirmed(postvars, current_lon, current_lat)
      return postvars, True

    addr = postvars.get('place_name')
    if not addr:
      return postvars, False

    token = self.get_public_token()
    query = f'https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(addr)}.json?access_token={token}&limit=1&proximity={current_lon},{current_lat}'
    response = requests.get(query)
    if response.status_code == 200:
      features = response.json().get('features', [])
      if features:
        longitude, latitude = features[0]['geometry']['coordinates']
        postvars.update({'latitude': latitude, 'longitude': longitude, 'name': addr})
        self.nav_confirmed(postvars, current_lon, current_lat)
        return postvars, True
    return postvars, False

  def nav_confirmed(self, postvars, start_lon, start_lat) -> None:
    if not postvars:
      return

    latitude = float(postvars['latitude'])
    longitude = float(postvars['longitude'])

    settings = self.autonomy_schema.MapboxSettings.new_message()
    settings.init('navData').init('route')
    current = settings.navData.current
    current.latitude = latitude
    current.longitude = longitude

    token = self.get_public_token()
    route_data = self.generate_route(start_lon, start_lat, longitude, latitude, token)
    if route_data:
      self._populate_route(settings, route_data)
    self.params.put('MapboxSettings', settings.to_bytes())

  def generate_route(self, start_lon, start_lat, end_lon, end_lat, token) -> dict | None:
    if not token:
      return None

    response = requests.get(
      f'https://api.mapbox.com/directions/v5/mapbox/driving/{start_lon},{start_lat};{end_lon},{end_lat}',
      params={
        'access_token': token,
        'geometries': 'geojson',
        'steps': 'true',
        'overview': 'full',
        'annotations': 'maxspeed'
      }
    )
    data = response.json() if response.status_code == 200 else {}
    if data['code'] != 'Ok':  # status code 200 returns Ok, NoRoute, or NoSegment, we only want Ok responses
      return None

    routes = data.get('routes', [])
    legs = routes[0].get('legs', []) if routes else []

    if not routes or not legs:
      return None

    leg = legs[0]
    route = routes[0]
    steps = [
      {
        'maneuver': step['maneuver']['type'],
        'instruction': step['maneuver']['instruction'],
        'distance': step['distance'],
        'duration': step['duration'],
        'location': Coordinate.from_mapbox_tuple(tuple(step['maneuver']['location'])),
        'modifier': step['maneuver'].get('modifier', 'none'),
      }
      for step in leg['steps']
    ]

    maxspeed = [
      {'speed': item['speed'], 'unit': item['unit']}
      for item in leg['annotation']['maxspeed'] if 'speed' in item
    ]

    return {
      'steps': steps,
      'total_distance': route['distance'],
      'total_duration': route['duration'],
      'geometry': route['geometry']['coordinates'],
      'maxspeed': maxspeed
    }
