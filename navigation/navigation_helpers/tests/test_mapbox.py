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
    cls.postvars = {"place_name": cls.user_input_location}
    cls.postvars, cls.valid_addr = cls.mapbox.set_destination(cls.postvars, cls.current_lon, cls.current_lat)
    assert cls.valid_addr
    cls.route = cls.nav.get_current_route()
    assert cls.route is not None
    assert len(cls.route['steps']) > 0

  def test_set_destination(self):
    settings = self.mapbox.params.get('MapboxSettings')
    assert settings is not None
    dest_lat = settings['navData']['current']['latitude']
    dest_lon = settings['navData']['current']['longitude']
    assert dest_lat == self.postvars["latitude"] and dest_lon == self.postvars["longitude"]

  def test_get_route(self):
    assert 'steps' in self.route
    assert 'geometry' in self.route
    assert 'maxspeed' in self.route
    assert 'total_distance' in self.route
    assert 'total_duration' in self.route
    assert len(self.route['steps']) > 0
    assert len(self.route['geometry']) > 0
    assert len(self.route['maxspeed']) > 0

    maxspeed = [(speed, unit) for speed, unit in self.route['maxspeed'] if speed > 0]
    print(f"Maxspeed: {maxspeed}")
    modifiers = [step['modifier'] for step in self.route['steps']]
    print(f"Modifiers: {modifiers}")
    if self.route and 'steps' in self.route:
      for step in self.route['steps']:
        assert 'modifier' in step

  def test_upcoming_turn_detection(self):
    progress = self.nav.get_route_progress(self.current_lat, self.current_lon)
    upcoming = self.nav.get_upcoming_turn_from_progress(progress, self.current_lat, self.current_lon)
    assert isinstance(upcoming, str)
    assert upcoming == 'none'

    if self.route['steps']:
      turn_lat = self.route['steps'][1]['location'].latitude
      turn_lon = self.route['steps'][1]['location'].longitude
      close_lat = turn_lat - 0.0008  # 80 ish meters before turn
      if progress and progress.get('next_turn'):
        expected_turn = progress['next_turn']['modifier']
        upcoming_close = self.nav.get_upcoming_turn_from_progress(progress, close_lat, turn_lon)
        if expected_turn:
          assert upcoming_close == expected_turn == 'right', f"Should detect '{expected_turn}' turn when close to next turn location"

  def test_route_progress_tracking(self):
    # Test route progress tracking
    progress = self.nav.get_route_progress(self.current_lat, self.current_lon)
    print(f"Route progress: {progress}")
    assert progress is not None
    assert 'distance_from_route' in progress
    assert 'next_turn' in progress
    assert 'route_progress_percent' in progress
    assert 'current_maxspeed' in progress
    assert 'total_distance_remaining' in progress
    assert 'total_time_remaining' in progress
    assert 'all_maneuvers' in progress
    assert progress['distance_from_route'] >= 0
    assert 0 <= progress['route_progress_percent'] <= 100
    assert progress['total_distance_remaining'] >= 0
    assert progress['total_time_remaining'] >= 0
    assert isinstance(progress['all_maneuvers'], list)

    # Test speed limit extraction
    speed_limit_metric = self.nav.get_current_speed_limit_from_progress(progress, True)
    speed_limit_imperial = self.nav.get_current_speed_limit_from_progress(progress, False)
    assert isinstance(speed_limit_metric, int)
    assert isinstance(speed_limit_imperial, int)
    expected_metric = int(progress['current_maxspeed'][0])
    expected_imperial = int(round(progress['current_maxspeed'][0] * CV.KPH_TO_MPH))
    assert speed_limit_metric == expected_metric
    assert speed_limit_imperial == expected_imperial
