import json

from navigation.navigation_helpers.mapbox_integration import MapboxIntegration
from navigation.navigation_helpers.nav_instructions import NavigationInstructions
from navigation.common.constants import CV


class TestMapbox:
  @classmethod
  def setup_class(cls):
    cls.mapbox = MapboxIntegration()
    cls.nav = NavigationInstructions()

    # setup route
    cls.current_lon, cls.current_lat = -119.17557, 34.23305
    cls.user_input_location = "740 E Ventura Blvd. Camarillo, CA"
    cls.postvars = {
      "place_name": cls.user_input_location
    }
    cls.postvars, cls.valid_addr = cls.mapbox.set_destination(cls.postvars, cls.current_lon, cls.current_lat)
    assert cls.valid_addr, "Failed to geocode the location."
    cls.route = cls.nav.get_current_route()
    assert cls.route is not None, "Route should be generated"
    assert len(cls.route['steps']) > 0, "Route should have at least one step"

  def test_set_destination(self):
    stored = self.mapbox.params.get('MapboxSettings')
    assert stored is not None, "MapboxSettings not stored"
    settings = json.loads(stored)
    dest_lat = settings['navData']['current']['latitude']
    dest_lon = settings['navData']['current']['longitude']
    assert dest_lat == self.postvars["latitude"] and dest_lon == self.postvars["longitude"], "Destination coordinates not stored correctly"

  def test_get_route(self):
    assert 'steps' in self.route, "Route should have steps"
    assert 'geometry' in self.route, "Route should have geometry"
    assert 'maxspeed' in self.route, "Route should have maxspeed"
    assert 'total_distance' in self.route, "Route should have total distance"
    assert 'total_duration' in self.route, "Route should have total duration"
    assert len(self.route['steps']) > 0, "Route should have at least one step"
    assert len(self.route['geometry']) > 0, "Route should have geometry coordinates"
    assert len(self.route['maxspeed']) > 0, "Route should have maxspeed data"

    maxspeed_kph = [(speed, unit) for speed, unit in self.route['maxspeed'] if speed > 0]
    print(f"Maxspeed: {maxspeed_kph}")
    modifiers = [step['modifier'] for step in self.route['steps']]
    print(f"Modifiers: {modifiers}")
    if self.route and 'steps' in self.route:
      for step in self.route['steps']:
        assert 'modifier' in step, "Each step should have a turn in this sample"

  def test_upcoming_turn_detection(self):
    progress = self.nav.get_route_progress(self.current_lat, self.current_lon)
    upcoming = self.nav.get_upcoming_turn_from_progress(progress, self.current_lat, self.current_lon)
    assert isinstance(upcoming, str), "Upcoming turn should be a string"
    assert upcoming == 'none', "Should not detect upcoming turn when far from route turns"

    if self.route['steps']:
      turn_lat = self.route['steps'][1]['location'].latitude
      turn_lon = self.route['steps'][1]['location'].longitude
      close_lat = turn_lat - 0.0003  # 30m before turn
      if progress and progress.get('next_turn'):
        expected_turn = progress['next_turn']['modifier']
        upcoming_close = self.nav.get_upcoming_turn_from_progress(progress, close_lat, turn_lon)
        if expected_turn:
          assert upcoming_close == expected_turn == 'right', f"Should detect '{expected_turn}' turn when close to next turn location"

  def test_route_progress_tracking(self):
    # Test route progress tracking
    progress = self.nav.get_route_progress(self.current_lat, self.current_lon)
    print(f"Route progress: {progress}")
    assert progress is not None, "Route progress should be available"
    assert 'distance_from_route' in progress, "Progress should include distance from route"
    assert 'next_turn' in progress, "Progress should include next turn info"
    assert 'route_progress_percent' in progress, "Progress should include route completion percentage"
    assert 'current_maxspeed' in progress, "Progress should include current maxspeed"
    assert progress['distance_from_route'] >= 0, "Distance from route should be non-negative"
    assert 0 <= progress['route_progress_percent'] <= 100, "Route progress should be 0-100%"
    assert self.route['total_distance'] > 0, "Route distance should be positive"
    assert self.route['total_duration'] > 0, "Route duration should be positive"

    # Test speed limit extraction
    speed_limit_metric = self.nav.get_current_speed_limit_from_progress(progress, True)
    speed_limit_imperial = self.nav.get_current_speed_limit_from_progress(progress, False)
    assert isinstance(speed_limit_metric, int), "Speed limit should be an integer"
    assert isinstance(speed_limit_imperial, int), "Speed limit should be an integer"
    expected_metric = int(progress['current_maxspeed'][0])
    expected_imperial = int(round(progress['current_maxspeed'][0] * CV.KPH_TO_MPH))
    assert speed_limit_metric == expected_metric, f"Metric speed limit should be {expected_metric}"
    assert speed_limit_imperial == expected_imperial, f"Imperial speed limit should be {expected_imperial}"
