import json
from urllib.parse import quote
import requests
from navigation.common.params.params import Params
from navigation.navd.helpers import Coordinate, string_to_direction
from messaging.messenger import schema


class MapboxIntegration:
  def __init__(self):
    self.params = Params()
    self.params_capnp = schema

  def _load_mapbox_settings(self):
    param_value = self.params.get("MapboxSettings", encoding='bytes')
    settings = self.params_capnp.MapboxSettings.new_message()
    if param_value:
      with self.params_capnp.MapboxSettings.from_bytes(param_value) as existing:
        settings.navData = existing.navData
    else:
      settings.navData = self.params_capnp.MapboxSettings.NavData.new_message()
      settings.navData.route = self.params_capnp.MapboxSettings.Route.new_message()
    return settings
  
  def get_public_token(self):
    token = self.params.get("MapboxToken", encoding='utf8')
    return token

  def _populate_route(self, settings, route_data):
    settings.navData.route.totalDistance = route_data['total_distance']
    settings.navData.route.totalDuration = route_data['total_duration']
    route_steps = settings.navData.route.init('steps', len(route_data['steps']))
    for i, step in enumerate(route_data['steps']):
      route_steps[i].instruction = step['instruction']
      route_steps[i].distance = step['distance']
      route_steps[i].duration = step['duration']
      route_steps[i].maneuver = step['maneuver']
      route_steps[i].location.longitude = step['location'].longitude
      route_steps[i].location.latitude = step['location'].latitude
    route_geometry = settings.navData.route.init('geometry', len(route_data['geometry']))
    for i, coord in enumerate(route_data['geometry']):
      route_geometry[i].longitude = coord[0]
      route_geometry[i].latitude = coord[1]
    maxspeed_entries = settings.navData.route.init('maxspeed', len(route_data['maxspeed']))
    for i, ms in enumerate(route_data['maxspeed']):
      maxspeed_entries[i].speed = ms['speed']
      maxspeed_entries[i].unit = ms['unit']

  def search_addr(self, postvars, current_lon, current_lat, valid_addr, token):
    addr = postvars.get("addr_val")
    longitude = current_lon
    latitude = current_lat
    if addr and addr != "":
      addr_encoded = quote(addr)
      query = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{addr_encoded}.json?access_token={token}&limit=1"
      # focus on place around gps position
      query += f"&proximity={current_lon},{current_lat}"
      r = requests.get(query)
      if r.status_code == 200:
        json_response = json.loads(r.text)
        if json_response["features"]:
          longitude, latitude = json_response["features"][0]["geometry"]["coordinates"]
          valid_addr = True
    return (addr, longitude, latitude, valid_addr, token)

  def set_destination(self, postvars, valid_addr, current_lon, current_lat):
    if postvars.get("latitude") is not None and postvars.get("longitude") is not None:
      self.nav_confirmed(postvars, current_lon, current_lat)
      valid_addr = True
    else:
      addr = postvars.get("place_name")
      postvars["addr_val"] = addr
      token = self.get_public_token()
      data, longitude, latitude, valid_addr, token = self.search_addr(postvars, current_lon, current_lat, valid_addr, token)
      postvars["latitude"] = latitude
      postvars["longitude"] = longitude
      postvars["name"] = data  # Set the name to the geocoded address
      if valid_addr:
        self.nav_confirmed(postvars, current_lon, current_lat)
    return postvars, valid_addr

  def nav_confirmed(self, postvars, start_lon, start_lat):
    if postvars is not None:
      latitude = float(postvars.get("latitude"))
      longitude = float(postvars.get("longitude"))
      name = postvars.get("name") or ""
      settings = self._load_mapbox_settings()
      if name == "":
        name = f"{latitude},{longitude}"
      settings.navData.current.latitude = latitude
      settings.navData.current.longitude = longitude
      settings.navData.current.placeName = name
      # Generate route from current GPS to destination
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
    r = requests.get(url, params=params_api)
    if r.status_code != 200:
      return None
    data = r.json()
    if not data.get('routes'):
      return None
    route = data['routes'][0]
    legs = route['legs'][0]
    steps = [
        {
            'maneuver': step['maneuver']['type'],
            'instruction': step['maneuver'].get('instruction', ''),
            'distance': step['distance'],
            'duration': step['duration'],
            'location': Coordinate(step['maneuver']['location'][1], step['maneuver']['location'][0]),
            'turn_direction': string_to_direction(step['maneuver'].get('instruction', ''))
        }
        for step in legs['steps']
    ]
    maxspeed_list = legs.get('annotation', {}).get('maxspeed', [])
    maxspeed = []
    for item in maxspeed_list:
      speed_kmh = float(item.get('speed', item.get('value', 0)))
      maxspeed.append({'speed': round(speed_kmh), 'unit': 'km/h'})

    return {
      'steps': steps,
      'total_distance': route['distance'],
      'total_duration': route['duration'],
      'geometry': route['geometry']['coordinates'],
      'maxspeed': maxspeed
    }
