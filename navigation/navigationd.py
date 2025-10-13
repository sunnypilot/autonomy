import logging
import math
import time

import messaging.messenger as messenger
from common.params.params import Params
from navigation.navd.helpers import Coordinate, parse_banner_instructions
from navigation.navigation_helpers.mapbox_integration import MapboxIntegration
from navigation.navigation_helpers.nav_instructions import NavigationInstructions


class Navigationd:
  def __init__(self):
    self.params = Params()
    self.mapbox = MapboxIntegration()
    self.nav_instructions = NavigationInstructions()

    self.sm = messenger.SubMaster('livelocationd')
    self.pm = messenger.PubMaster('navigationd')

    self.route = None
    self.destination: str | None = None
    self.new_destination: str = ''

    self.recompute_allowed: bool = False
    self.allow_recompute: bool = False
    self.reroute_counter: int = 0

    self.frame: int = -1
    self.last_position: Coordinate | None = None
    self.last_bearing: float | None = None
    self.is_metric: bool = False

  def _update_params(self):
    if self.last_position is not None:
      self.frame += 1
      if self.frame % 9 == 0:
        self.is_metric = self.params.get('IsMetric', return_default=True)
        self.new_destination = self.params.get('MapboxRoute')
        self.recompute_allowed = self.params.get('MapboxRecompute', return_default=True)

      self.allow_recompute: bool = (self.new_destination != self.destination and self.new_destination != '') or (
        self.recompute_allowed and self.reroute_counter > 3 and self.route
      )

      if self.allow_recompute:
        postvars = {'place_name': self.new_destination}
        postvars, valid_addr = self.mapbox.set_destination(postvars, self.last_position.longitude, self.last_position.latitude, self.last_bearing)
        logging.debug(f'Set new destination to: {self.new_destination}, valid: {valid_addr}')
        if valid_addr:
          self.destination = self.new_destination
          self.nav_instructions.clear_route_cache()
          self.route = self.nav_instructions.get_current_route()
          self.reroute_counter = 0

  def _update_navigation(self) -> tuple[str, dict | None, dict]:
    banner_instructions: str = ''
    progress: dict | None = None
    nav_data: dict = {}
    if self.last_position is not None:
      if progress := self.nav_instructions.get_route_progress(self.last_position.latitude, self.last_position.longitude):
        nav_data['upcoming_turn'] = self.nav_instructions.get_upcoming_turn_from_progress(progress, self.last_position.latitude, self.last_position.longitude)
        nav_data['current_speed_limit'] = self.nav_instructions.get_current_speed_limit_from_progress(progress, self.is_metric)

        if progress['current_step']:
          parsed = parse_banner_instructions(progress['current_step']['bannerInstructions'], progress['distance_to_end_of_step'])
          if parsed:
            banner_instructions = parsed['maneuverPrimaryText']

        nav_data['distance_to_next_turn'] = progress['distance_to_next_turn']
        nav_data['distance_to_end_of_step'] = progress['distance_to_end_of_step']
        nav_data['route_progress_percent'] = progress['route_progress_percent']
        nav_data['distance_from_route'] = progress['distance_from_route']
        nav_data['route_position_cumulative'] = progress['route_position_cumulative']

        # Don't recompute in last segment to prevent reroute loops
        if self.route:
          if progress['current_step_idx'] == len(self.route['steps']) - 1:
            self.allow_recompute = False

        if self.recompute_allowed:
          self.reroute_counter += 1 if nav_data['distance_from_route'] > 25 else 0
          logging.debug(f'Reroute counter: {self.reroute_counter}, distance: {nav_data["distance_from_route"]}')

    return banner_instructions, progress, nav_data

  def _build_navigation_message(self, banner_instructions, progress, nav_data):
    msg = messenger.schema.MapboxSettings.new_message()
    msg.timestamp = int(time.monotonic() * 1000)
    msg.upcomingTurn = nav_data.get('upcoming_turn', 'none')
    msg.currentSpeedLimit = nav_data.get('current_speed_limit', 0)
    msg.bannerInstructions = banner_instructions
    msg.distanceToNextTurn = nav_data.get('distance_to_next_turn', 0.0)
    msg.distanceToEndOfStep = nav_data.get('distance_to_end_of_step', 0.0)
    msg.routeProgressPercent = nav_data.get('route_progress_percent', 0.0)
    msg.distanceFromRoute = nav_data.get('distance_from_route', 0.0)
    msg.routePositionCumulative = nav_data.get('route_position_cumulative', 0.0)
    msg.totalDistanceRemaining = progress['total_distance_remaining'] if progress else 0.0
    msg.totalTimeRemaining = progress['total_time_remaining'] if progress else 0.0

    all_maneuvers = (
      [messenger.schema.Maneuver.new_message(distance=m['distance'], type=m['type'], modifier=m['modifier']) for m in progress['all_maneuvers']]
      if progress
      else []
    )
    msg.allManeuvers = all_maneuvers

    return msg

  def run(self):
    logging.warning('navigationd init')

    while True:
      location = self.sm['livelocationd']
      localizer_valid = location.positionGeodetic.valid if location else False

      if localizer_valid:
        self.last_bearing = math.degrees(location.calibratedOrientationNED.value[2])
        self.last_position = Coordinate(location.positionGeodetic.value[0], location.positionGeodetic.value[1])

      self._update_params()
      banner_instructions, progress, nav_data = self._update_navigation()

      msg = self._build_navigation_message(banner_instructions, progress, nav_data)

      self.pm.send('navigationd', msg)
      time.sleep(self.pm['navigationd'].rate_hz)


def main():
  logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  nav = Navigationd()
  nav.run()
