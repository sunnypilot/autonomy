import capnp
import os

from navigation.common.params.params import Params
from navigation.navigation_helpers.mapbox_integration import MapboxIntegration
from navigation.navigation_helpers.nav_instructions import NavigationInstructions


class TestMapbox:
  def setup_method(self):
    self.mapbox = MapboxIntegration()
    self.nav = NavigationInstructions()
    self.params = Params()
    self.params_capnp = capnp.load(os.path.join(os.path.dirname(__file__), '..', '..','common', 'navigation.capnp'))

  def test_mapbox_integration(self):
    settings = self.params_capnp.MapboxSettings.new_message()
    settings.navData = self.params_capnp.MapboxSettings.NavData.new_message()
    settings.navData.cache = self.params_capnp.MapboxSettings.NavDestinationsList.new_message()
    settings.searchInput = 0
    self.params.put("MapboxSettings", settings.to_bytes())

    # Update GPS position
    current_lon, current_lat = -119.17557, 34.23305
    self.mapbox.update_gps_position(current_lon, current_lat)

    # location is inputted
    user_input_location = "740 E Ventura Blvd. Camarillo, CA"

    # Prepare the postvars dict
    postvars = {
      "place_name": user_input_location
    }

    # Call set_destination
    postvars, valid_addr = self.mapbox.set_destination(postvars, False)

    # Check result
    assert valid_addr, "Failed to geocode the location."
    print(f"Destination set: {postvars}")
    stored = self.params.get('MapboxSettings', encoding='bytes')
    assert stored is not None, "MapboxSettings not stored"
    with self.params_capnp.MapboxSettings.from_bytes(stored) as settings:
      dest_lat = settings.navData.current.latitude
      dest_lon = settings.navData.current.longitude
      print(f"Stored Destination: latitude: {dest_lat:.10f}, longitude: {dest_lon:.10f}, Address Name: {settings.navData.current.placeName}")

    # Get the route
    route = self.nav.get_current_route()

    # Check route exists and has expected structure
    assert route is not None, "Route should be generated"
    assert 'steps' in route, "Route should have steps"
    assert 'geometry' in route, "Route should have geometry"
    assert 'maxspeed' in route, "Route should have maxspeed"
    assert 'total_distance' in route, "Route should have total distance"
    assert 'total_duration' in route, "Route should have total duration"
    assert len(route['steps']) > 0, "Route should have at least one step"
    assert len(route['geometry']) > 0, "Route should have geometry coordinates"
    assert len(route['maxspeed']) > 0, "Route should have maxspeed data"

    maxspeed_kph = [(speed, 'km/h') for speed, unit in route['maxspeed'] if speed > 0]
    print(f"Maxspeed: {maxspeed_kph}")
    if route and 'steps' in route:
      print("Route steps turn_directions:", [step['turn_direction'] for step in route['steps']])

      # Assert all steps have turn_direction field
      for step in route['steps']:
        assert 'turn_direction' in step, "Each step should have turn_direction"

      # Test upcoming turn
      upcoming = self.nav.get_upcoming_turn(current_lat, current_lon)
      assert isinstance(upcoming, str), "Upcoming turn should be a string"
      print(f"Upcoming turn at start: {upcoming}")  # should be 'none' as starting coordinates are away from any turn
      assert upcoming == 'none', "Should not detect upcoming turn when far from route turns"

      if route['steps']:
        turn_lat, turn_lon = route['steps'][1]['location']
        close_lat = turn_lat + 0.0005  # Approx 50m closer?
        upcoming_close = self.nav.get_upcoming_turn(close_lat, turn_lon)
        print(f"Upcoming turn near turn: {upcoming_close}")

        # Assert correct turn direction detected when close. Should be 'right' for second step in this route
        expected_turn = route['steps'][1]['turn_direction']
        if expected_turn != 'none':  # Only assert if there's actually a turn
          assert upcoming_close == expected_turn == 'right', f"Should detect '{expected_turn}' turn when close to turn location"

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

      print(f"Route generated: {len(route['steps'])} steps, total distance: {route['total_distance']:.3f}m")

