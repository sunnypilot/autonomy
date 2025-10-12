from urllib.parse import quote
import requests

from common.params.params import Params
from navigation.navd.helpers import Coordinate


class MapboxIntegration:
  def __init__(self):
    self.params = Params()

  def get_public_token(self) -> str:
    token = str(self.params.get('MapboxToken', return_default=True))
    return token

  def set_destination(self, postvars, current_lon, current_lat, bearing=None) -> tuple[dict, bool]:
    if 'latitude' in postvars and 'longitude' in postvars:
      self.nav_confirmed(postvars, current_lon, current_lat, bearing)
      return postvars, True

    addr = postvars.get('place_name')
    if not addr:
      return postvars, False

    token = self.get_public_token()
    query = f'https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(addr)}.json?access_token={token}&limit=1&proximity={current_lon},{current_lat}'
    response = requests.get(query, timeout=10)
    if response.status_code == 200:
      features = response.json().get('features', [])
      if features:
        longitude, latitude = features[0]['geometry']['coordinates']
        postvars.update({'latitude': latitude, 'longitude': longitude, 'name': addr})
        self.nav_confirmed(postvars, current_lon, current_lat, bearing)
        return postvars, True
    return postvars, False

  def nav_confirmed(self, postvars, start_lon, start_lat, bearing=None) -> None:
    if not postvars:
      return

    latitude = float(postvars['latitude'])
    longitude = float(postvars['longitude'])

    data: dict = {'navData': {'current': {'latitude': latitude, 'longitude': longitude}, 'route': {}}}

    token = self.get_public_token()
    route_data = self.generate_route(start_lon, start_lat, longitude, latitude, token, bearing)
    if route_data:
      data['navData']['route'] = {
        'steps': [
          {
            'maneuver': step['maneuver'],
            'instruction': step['instruction'],
            'distance': step['distance'],
            'duration': step['duration'],
            'location': {'latitude': step['location'].latitude, 'longitude': step['location'].longitude},
            'modifier': step['modifier'],
            'bannerInstructions': step['bannerInstructions'],
          }
          for step in route_data['steps']
        ],
        'totalDistance': route_data['total_distance'],
        'totalDuration': route_data['total_duration'],
        'geometry': [{'longitude': coord[0], 'latitude': coord[1]} for coord in route_data['geometry']],
        'maxspeed': route_data['maxspeed'],
      }
    self.params.put('MapboxSettings', data)

  def generate_route(self, start_lon, start_lat, end_lon, end_lat, token, bearing=None) -> dict | None:
    if not token:
      return None

    params = {'access_token': token, 'geometries': 'geojson', 'steps': 'true', 'overview': 'full', 'annotations': 'maxspeed', 'banner_instructions': 'true'}
    if bearing is not None:
      params['bearings'] = f'{int((bearing + 360) % 360):.0f},90;'

    response = requests.get(f'https://api.mapbox.com/directions/v5/mapbox/driving/{start_lon},{start_lat};{end_lon},{end_lat}', params=params, timeout=10)
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
        'bannerInstructions': step['bannerInstructions'],
      }
      for step in leg['steps']
    ]

    maxspeed = [{'speed': item['speed'], 'unit': item['unit']} for item in leg['annotation']['maxspeed'] if 'speed' in item]

    return {
      'steps': steps,
      'total_distance': route['distance'],
      'total_duration': route['duration'],
      'geometry': route['geometry']['coordinates'],
      'maxspeed': maxspeed,
    }
