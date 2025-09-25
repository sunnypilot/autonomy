import navigation.navigation_helpers.mapbox_integration
from navigation.navigation_helpers.mapbox_integration import MapboxIntegration
from navigation.navigation_helpers.nav_instructions import NavigationInstructions
import folium


def test_mapbox_integration():
  mapbox = MapboxIntegration()
  nav = NavigationInstructions()
  params = navigation.navigation_helpers.mapbox_integration.params

  # Set Mapbox public access token
  mapbox_token = "pk.eyJ1IjoianZlY2VsbGkiLCJhIjoiY2xzNHFxaWkwMTBvODJqbjQyMHkzM2plMyJ9.x7ddgNgQE--pBpD5PB0xRA"
  settings = navigation.navigation_helpers.mapbox_integration.params_capnp.MapboxSettings.new_message()
  settings.publicKey = mapbox_token
  settings.navData = navigation.navigation_helpers.mapbox_integration.params_capnp.MapboxSettings.NavData.new_message()
  settings.navData.cache = navigation.navigation_helpers.mapbox_integration.params_capnp.MapboxSettings.NavDestinationsList.new_message()
  settings.searchInput = 0
  params.put("MapboxSettings", settings.to_bytes())

  # Update current GPS position
  current_lon, current_lat = -119.19657, 34.16207
  mapbox.update_gps_position(current_lon, current_lat)

  # Example: User types a location
  user_input_location = "580 Winchester dr. oxnard, CA"

  # Prepare the postvars dict
  postvars = {
    "place_name": user_input_location
  }

  # Call set_destination
  postvars, valid_addr = mapbox.set_destination(postvars, False)

  # Check result
  assert valid_addr, "Failed to geocode the location."
  print(f"Destination set: {postvars}")
  stored = params.get('MapboxSettings', encoding='bytes')
  assert stored is not None, "MapboxSettings not stored"
  with navigation.navigation_helpers.mapbox_integration.params_capnp.MapboxSettings.from_bytes(stored) as settings:
    dest_lat = settings.navData.current.latitude
    dest_lon = settings.navData.current.longitude
    print(f"Stored NavDestination: latitude: {dest_lat:.10f}, longitude: {dest_lon:.10f}, Address Name: {settings.navData.current.placeName}")

  # Get and visualize the route
  route = nav.get_current_route()

  # Assert route exists and has expected structure
  assert route is not None, "Route should be generated"
  assert 'steps' in route, "Route should have steps"
  assert 'geometry' in route, "Route should have geometry"
  assert 'maxspeed' in route, "Route should have maxspeed"
  assert 'total_distance' in route, "Route should have total distance"
  assert 'total_duration' in route, "Route should have total duration"
  assert len(route['steps']) > 0, "Route should have at least one step"
  assert len(route['geometry']) > 0, "Route should have geometry coordinates"
  assert len(route['maxspeed']) > 0, "Route should have maxspeed data"

  print(route['steps'][1:3])
  maxspeed_kph = [(speed, 'km/h') for speed, unit in route['maxspeed'] if speed > 0]
  print(f"Maxspeed: {maxspeed_kph}")
  if route and 'steps' in route:
    print("Route steps turn_directions:", [step['turn_direction'] for step in route['steps']])

    # Assert all steps have turn_direction field
    for step in route['steps']:
      assert 'turn_direction' in step, "Each step should have turn_direction"

    # Test upcoming turn
    upcoming = nav.get_upcoming_turn(current_lat, current_lon)
    print(f"Upcoming turn at start: {upcoming}")

    # Assert no upcoming turn when far from any turn
    assert upcoming is None, "Should not detect upcoming turn when far from route turns"

    if route['steps']:
      turn_lat, turn_lon = route['steps'][1]['location']
      close_lat = turn_lat + 0.0005  # Approx 50m closer
      upcoming_close = nav.get_upcoming_turn(close_lat, turn_lon)
      print(f"Upcoming turn near turn: {upcoming_close}")

      # Assert correct turn direction detected when close
      expected_turn = route['steps'][1]['turn_direction']
      if expected_turn != 'None':  # Only assert if there's actually a turn
        assert upcoming_close == expected_turn, f"Should detect '{expected_turn}' turn when close to turn location"

    # Test route progress tracking
    progress = nav.get_route_progress(current_lat, current_lon)
    print(f"Route progress: {progress}")
    assert progress is not None, "Route progress should be available"
    assert 'distance_from_route' in progress, "Progress should include distance from route"
    assert 'next_turn' in progress, "Progress should include next turn info"
    assert 'route_progress_percent' in progress, "Progress should include route completion percentage"
    assert 'current_maxspeed' in progress, "Progress should include current maxspeed"
    assert progress['distance_from_route'] >= 0, "Distance from route should be non-negative"
    assert 0 <= progress['route_progress_percent'] <= 100, "Route progress should be 0-100%"

    print(f"Route generated: {len(route['steps'])} steps, total distance: {route['total_distance']:.3f}m")

    # Assert reasonable route properties
    assert route['total_distance'] > 0, "Route distance should be positive"
    assert route['total_duration'] > 0, "Route duration should be positive"

    # Create interactive map with folium
    m = folium.Map(location=[current_lat, current_lon], zoom_start=13)
    # Add route polyline (folium expects [lat, lon])
    route_coords = [(lat, lon) for lon, lat in route['geometry']]
    folium.PolyLine(route_coords, color='blue', weight=5, opacity=0.8).add_to(m)
    # Add start and destination markers
    folium.Marker([current_lat, current_lon], popup='Start', icon=folium.Icon(color='green')).add_to(m)
    folium.Marker([dest_lat, dest_lon], popup='Destination', icon=folium.Icon(color='red')).add_to(m)
    # Save map
    m.save('route_map.html')
    print("Interactive route map saved as route_map.html")
  else:
    print("No route generated")


if __name__ == "__main__":
    test_mapbox_integration()

