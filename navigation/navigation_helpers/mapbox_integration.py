import json
import capnp
from urllib.parse import quote
import requests
from navigation.common.params.params import Params
from navigation.navd.helpers import string_to_direction


class MapboxIntegration:
  def __init__(self):
    self.params = Params()
    self.params_capnp = capnp.load('navigation/common/navigation.capnp')

  def get_public_token(self):
    token = self.params.get("MapboxToken", encoding='utf8')
    return token

  def get_last_longitude_latitude(self):
    param_value = self.params.get("MapboxSettings", encoding='bytes')
    if param_value:
      with self.params_capnp.MapboxSettings.from_bytes(param_value) as settings:
        return settings.lastGPSPosition.longitude, settings.lastGPSPosition.latitude
    return 0.0, 0.0  # Default if not set

  def search_addr(self, postvars, longitude, latitude, valid_addr, token):
    if "addr_val" in postvars:
      addr = postvars.get("addr_val")
      if addr != "":
        addr_encoded = quote(addr)
        query = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{addr_encoded}.json?access_token={token}&limit=1"
        # focus on place around last gps position
        longitude, latitude = self.get_last_longitude_latitude()
        query += f"&proximity={longitude},{latitude}"
        r = requests.get(query)
        if r.status_code != 200:
          return (addr, longitude, latitude, valid_addr, token)
        json_response = json.loads(r.text)
        if not json_response["features"]:
          return (addr, longitude, latitude, valid_addr, token)
        longitude, latitude = json_response["features"][0]["geometry"]["coordinates"]
        valid_addr = True
    return (addr, longitude, latitude, valid_addr, token)

  def set_destination(self, postvars, valid_addr):
    if postvars.get("latitude") is not None and postvars.get("longitude") is not None:
      postvars["latitude"] = postvars.get("latitude")
      postvars["longitude"] = postvars.get("longitude")
      self.nav_confirmed(postvars)
      valid_addr = True
    else:
      addr = postvars.get("place_name")
      postvars["addr_val"] = addr
      longitude = 0.0
      latitude = 0.0
      token = self.get_public_token()
      data, longitude, latitude, valid_addr, token = self.search_addr(postvars, longitude, latitude, valid_addr, token)
      postvars["latitude"] = latitude
      postvars["longitude"] = longitude
      postvars["name"] = data  # Set the name to the geocoded address
      if valid_addr:
        self.nav_confirmed(postvars)
    return postvars, valid_addr

  def nav_confirmed(self, postvars):
    print(f"nav_confirmed {postvars}")
    if postvars is not None:
      latitude = float(postvars.get("latitude"))
      longitudinal = float(postvars.get("longitude"))
      name = postvars.get("name") if postvars.get("name") is not None else ""
      param_value = self.params.get("MapboxSettings", encoding='bytes')
      settings = self.params_capnp.MapboxSettings.new_message()
      if param_value:
        with self.params_capnp.MapboxSettings.from_bytes(param_value) as existing:
          settings.lastGPSPosition.longitude = existing.lastGPSPosition.longitude
          settings.lastGPSPosition.latitude = existing.lastGPSPosition.latitude
          settings.navData.current.latitude = existing.navData.current.latitude
          settings.navData.current.longitude = existing.navData.current.longitude
          settings.navData.current.placeName = existing.navData.current.placeName
          settings.navData.cache = existing.navData.cache
          settings.navData.route = existing.navData.route
      else:
        settings.navData = self.params_capnp.MapboxSettings.NavData.new_message()
        settings.navData.cache = self.params_capnp.MapboxSettings.NavDestinationsList.new_message()
        settings.navData.route = self.params_capnp.MapboxSettings.Route.new_message()
      print(f"nav_confirmed {latitude}, {longitudinal}, {name}")
      if name == "":
        name =  str(latitude) + "," + str(longitudinal)
      new_dest = {"latitude": float(latitude), "longitude": float(longitudinal), "place_name": name}
      destinations = []
      for entry in settings.navData.cache.entries:
        destinations.append({
          'latitude': entry.latitude,
          'longitude': entry.longitude,
          'place_name': entry.placeName
        })
      # Keep only recent 10
      if len(destinations) >= 10:
        destinations.pop(0)
      destinations.insert(0, new_dest)
      settings.navData.current.latitude = latitude
      settings.navData.current.longitude = longitudinal
      settings.navData.current.placeName = name
      # Generate route from current GPS to destination
      start_lon, start_lat = settings.lastGPSPosition.longitude, settings.lastGPSPosition.latitude
      token = self.get_public_token()
      route_data = self.generate_route(start_lon, start_lat, longitudinal, latitude, token)
      if route_data:
        settings.navData.route.totalDistance = route_data['total_distance']
        settings.navData.route.totalDuration = route_data['total_duration']
        route_steps = settings.navData.route.init('steps', len(route_data['steps']))
        for i, step in enumerate(route_data['steps']):
          route_steps[i].instruction = step['instruction']
          route_steps[i].distance = step['distance']
          route_steps[i].duration = step['duration']
          route_steps[i].maneuver = step['maneuver']
          route_steps[i].location.longitude = step['location'][0]
          route_steps[i].location.latitude = step['location'][1]
        route_geometry = settings.navData.route.init('geometry', len(route_data['geometry']))
        for i, coord in enumerate(route_data['geometry']):
          route_geometry[i].longitude = coord[0]
          route_geometry[i].latitude = coord[1]
        maxspeed_entries = settings.navData.route.init('maxspeed', len(route_data['maxspeed']))
        for i, ms in enumerate(route_data['maxspeed']):
          maxspeed_entries[i].speed = ms['speed']
          maxspeed_entries[i].unit = ms['unit']

      entries = settings.navData.cache.init('entries', len(destinations))
      for i, d in enumerate(destinations):
        entries[i].latitude = d['latitude']
        entries[i].longitude = d['longitude']
        entries[i].placeName = d['place_name']
      self.params.put("MapboxSettings", settings.to_bytes())

  def update_gps_position(self, longitude, latitude):
    param_value = self.params.get("MapboxSettings", encoding='bytes')
    settings = self.params_capnp.MapboxSettings.new_message()
    if param_value:
      with self.params_capnp.MapboxSettings.from_bytes(param_value) as existing:
        settings.navData.current.latitude = existing.navData.current.latitude
        settings.navData.current.longitude = existing.navData.current.longitude
        settings.navData.current.placeName = existing.navData.current.placeName
        settings.navData.cache = existing.navData.cache
        settings.navData.route = existing.navData.route
    else:
      settings.navData = self.params_capnp.MapboxSettings.NavData.new_message()
      settings.navData.cache = self.params_capnp.MapboxSettings.NavDestinationsList.new_message()
      settings.navData.route = self.params_capnp.MapboxSettings.Route.new_message()
    settings.lastGPSPosition.longitude = longitude
    settings.lastGPSPosition.latitude = latitude
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
    steps = []
    for step in legs['steps']:
      maneuver = step['maneuver']['type']
      instruction = step['maneuver'].get('instruction', '')
      distance = step['distance']
      duration = step['duration']
      location = step['maneuver']['location']
      steps.append({
        'maneuver': maneuver,
        'instruction': instruction,
        'distance': distance,
        'duration': duration,
        'location': location,
        'turn_direction': string_to_direction(instruction)
      })
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
