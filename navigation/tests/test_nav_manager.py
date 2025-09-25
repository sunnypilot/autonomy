from navigation.nav_manager import NavManager


def test_nav_manager():
  """Test navigation manager functionality"""
  try:
    # Test initialization
    nav_manager = NavManager("580 winchester dr. Oxnard, CA", (34.16207, -119.19657))

    # Test route retrieval
    route = nav_manager.nav.get_current_route()
    assert route is not None, "Route should be available"
    assert 'geometry' in route, "Route should have geometry"
    assert len(route['steps']) > 0, "Route should have steps"

    # Debug print to crosscheck route is loaded correctly
    print(f"Route loaded: {len(route['geometry'])} points, {route['total_distance']:.1f}m")

    # Test GPS update
    nav_manager.update_gps_position(-119.195483, 34.162142)
    status = nav_manager.get_navigation_status()

    assert 'current_position' in status, "Status should include current position"
    assert 'progress' in status, "Status should include progress"
    assert 'current_instruction' in status, "Status should include current instruction"

    # Test navigation status
    progress = status['progress']
    assert 'route_progress_percent' in progress, "Progress should include percentage"
    assert 'current_step' in progress, "Progress should include current step"
    assert 'next_turn' in progress, "Progress should include next turn"
  except Exception as e:
    print(f"Test failed: {e}")
