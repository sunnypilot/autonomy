from navigation.navigation_helpers.mapbox_integration import MapboxIntegration
from navigation.navigation_helpers.nav_instructions import NavigationInstructions
from messaging.messenger import schema


class TestMapbox:
  def setup_method(self):
    self.params_capnp = schema
    self.mapbox = MapboxIntegration()
    self.nav = NavigationInstructions()

  def _setup_route(self):
    settings = self.mapbox._load_mapbox_settings()
    self.mapbox.params.put("MapboxSettings", settings.to_bytes())

    # setup route
    current_lon, current_lat = -119.17557, 34.23305
    user_input_location = "740 E Ventura Blvd. Camarillo, CA"
    postvars = {
      "place_name": user_input_location
    }

    postvars, valid_addr = self.mapbox.set_destination(postvars, False, current_lon, current_lat)
    assert valid_addr, "Failed to geocode the location."
    route = self.nav.get_current_route()
    assert route is not None, "Route should be generated"
    assert len(route['steps']) > 0, "Route should have at least one step"

    return route, current_lat, current_lon, postvars

  def test_set_destination(self):
    stored = self.mapbox.params.get('MapboxSettings', encoding='bytes')
    assert stored is not None, "MapboxSettings not stored"
    with self.params_capnp.MapboxSettings.from_bytes(stored) as settings:
      dest_lat = settings.navData.current.latitude
      dest_lon = settings.navData.current.longitude
      assert dest_lat != 0.0 and dest_lon != 0.0, "Coordinates not set"

  def test_get_route(self):
    route, _, _, _ = self._setup_route()

    assert 'steps' in route, "Route should have steps"
    assert 'geometry' in route, "Route should have geometry"
    assert 'maxspeed' in route, "Route should have maxspeed"
    assert 'total_distance' in route, "Route should have total distance"
    assert 'total_duration' in route, "Route should have total duration"
    assert len(route['steps']) > 0, "Route should have at least one step"
    assert len(route['geometry']) > 0, "Route should have geometry coordinates"
    assert len(route['maxspeed']) > 0, "Route should have maxspeed data"

    maxspeed_kph = [(speed, unit) for speed, unit in route['maxspeed'] if speed > 0]
    print(f"Maxspeed: {maxspeed_kph}")
    if route and 'steps' in route:
      for step in route['steps']:
        assert 'turn_direction' in step, "Each step should have turn_direction"

  def test_upcoming_turn_detection(self):
    route, current_lat, current_lon, _ = self._setup_route()

    upcoming = self.nav.get_upcoming_turn(current_lat, current_lon)
    assert isinstance(upcoming, str), "Upcoming turn should be a string"
    assert upcoming == 'none', "Should not detect upcoming turn when far from route turns"

    if route['steps']:
      turn_lat = route['steps'][1]['location'].latitude
      turn_lon = route['steps'][1]['location'].longitude
      close_lat = turn_lat + 0.0003  # Approx 33m closer?
      upcoming_close = self.nav.get_upcoming_turn(close_lat, turn_lon)

      # Should be 'right' for second step in this planned route
      expected_turn = route['steps'][1]['turn_direction']
      if expected_turn != 'none':
        assert upcoming_close == expected_turn == 'right', f"Should detect '{expected_turn}' turn when close to turn location"

  def test_route_progress_tracking(self):
    route, current_lat, current_lon, _ = self._setup_route()

    # Test route progress tracking
    progress = self.nav.get_route_progress(current_lat, current_lon)
    print(f"Route progress: {progress}")
    assert progress is not None, "Route progress should be available"
    assert 'distance_from_route' in progress, "Progress should include distance from route"
    assert 'next_turn' in progress, "Progress should include next turn info"
    assert 'route_progress_percent' in progress, "Progress should include route completion percentage"
    assert 'current_maxspeed' in progress, "Progress should include current maxspeed"
    assert progress['distance_from_route'] >= 0, "Distance from route should be non-negative"
    assert 0 <= progress['route_progress_percent'] <= 100, "Route progress should be 0-100%"
    assert route['total_distance'] > 0, "Route distance should be positive"
    assert route['total_duration'] > 0, "Route duration should be positive"
