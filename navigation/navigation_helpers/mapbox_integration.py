from urllib.parse import quote
import requests
from navigation.common.params.params import Params
from navigation.navd.helpers import Coordinate
from messaging.messenger import schema


class MapboxIntegration:
  def __init__(self):
    self.params = Params()
    self.autonomy_schema = schema

  def _load_mapbox_settings(self):
    settings = self.autonomy_schema.MapboxSettings.new_message()
    settings.init('navData').init('route')
    return settings
  
  def get_public_token(self):
    token = self.params.get("MapboxToken", return_default=True)
    return token

  def _populate_route(self, settings, route_data):
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
    route_geometry = settings.navData.route.init('geometry', len(route_data['geometry']))
    for idx, coord in enumerate(route_data['geometry']):
      route_geometry[idx].longitude = coord[0]
      route_geometry[idx].latitude = coord[1]
    maxspeed_entries = settings.navData.route.init('maxspeed', len(route_data['maxspeed']))
    for idx, ms in enumerate(route_data['maxspeed']):
      maxspeed_entries[idx].speed = ms['speed']
      maxspeed_entries[idx].unit = ms['unit']

  def search_addr(self, postvars, current_lon, current_lat, valid_addr, token):
    addr = postvars.get("addr_val")
    if not addr:
      return (addr, current_lon, current_lat, valid_addr, token)

    addr_encoded = quote(addr)
    query = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{addr_encoded}.json?access_token={token}&limit=1"
    query += f"&proximity={current_lon},{current_lat}"
    response = requests.get(query)
    if response.status_code == 200:
      features = response.json().get("features", [])
      if features:
        longitude, latitude = features[0]["geometry"]["coordinates"]
        return (addr, longitude, latitude, True, token)
    return (addr, current_lon, current_lat, valid_addr, token)

  def set_destination(self, postvars, valid_addr, current_lon, current_lat):
    if postvars.get("latitude") is not None and postvars.get("longitude") is not None:
      self.nav_confirmed(postvars, current_lon, current_lat)
      return postvars, True

    postvars["addr_val"] = postvars.get("place_name")
    token = self.get_public_token()
    data, longitude, latitude, valid_addr, _ = self.search_addr(postvars, current_lon, current_lat, valid_addr, token)
    postvars["latitude"] = latitude
    postvars["longitude"] = longitude
    postvars["name"] = data
    if valid_addr:
      self.nav_confirmed(postvars, current_lon, current_lat)
    return postvars, valid_addr

  def nav_confirmed(self, postvars, start_lon, start_lat):
    if not postvars:
      return

    latitude = float(postvars.get("latitude"))
    longitude = float(postvars.get("longitude"))
    name = postvars.get("name") or f"{latitude},{longitude}"

    settings = self._load_mapbox_settings()
    current = settings.navData.current
    current.latitude = latitude
    current.longitude = longitude
    current.placeName = name

    token = self.get_public_token()
    route_data = self.generate_route(start_lon, start_lat, longitude, latitude, token)
    if route_data:
      self._populate_route(settings, route_data)
    self.params.put("MapboxSettings", settings.to_bytes())

  def generate_route(self, start_lon, start_lat, end_lon, end_lat, token):
    if not token:
      return None
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
    params_api = {
      'access_token': token,
      'geometries': 'geojson',
      'steps': 'true',
      'overview': 'full',
      'annotations': 'maxspeed'
    }

    response = requests.get(url, params=params_api)
    data = response.json() if response.status_code == 200 else {}
    routes = data.get('routes', [])
    legs = routes[0].get('legs', []) if routes else []

    if not routes or not legs:
      return None

    route = routes[0]
    leg = legs[0]
    steps = [
      {
        'maneuver': step['maneuver']['type'],
        'instruction': step['maneuver'].get('instruction', ''),
        'distance': step['distance'],
        'duration': step['duration'],
        'location': Coordinate.from_mapbox_tuple(tuple(step['maneuver']['location'])),
      }
      for step in leg['steps']
    ]

    maxspeed = [
      {'speed': round(float(item.get('speed', item.get('value', 0)))), 'unit': 'km/h'}
      for item in leg['annotation']['maxspeed']
    ]

    return {
      'steps': steps,
      'total_distance': route['distance'],
      'total_duration': route['duration'],
      'geometry': route['geometry']['coordinates'],
      'maxspeed': maxspeed
    }
