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

    self.route: object | None = None
    self.destination: str | None = None
    self.new_destination: str = ''

    self.recompute_allowed: bool = False
    self.allow_recompute: bool = False
    self.reroute_counter: int = 0

    self.frame: int = -1
    self.last_position: Coordinate | None = None
    self.last_bearing: float | None = None
    self.is_metric: bool = False

    self.upcoming_turn: str = 'none'
    self.current_speed_limit: int = 0
    self.distance_to_next_turn: float = 0.0
    self.distance_to_end_of_step: float = 0.0
    self.route_progress_percent: float = 0.0
    self.distance_from_route: float = 0.0
    self.route_position_cumulative: float = 0.0

  def update_params(self):
    if self.last_position is not None:
      self.frame += 1
      if self.frame % 9 == 0:
        self.is_metric = self.params.get('IsMetric', return_default=True)
        self.new_destination = self.params.get('MapboxRoute')
        self.recompute_allowed = self.params.get('MapboxRecompute', return_default=True)

      self.allow_recompute: bool = ((self.new_destination != self.destination and self.new_destination != '') or
                              (self.recompute_allowed and self.reroute_counter > 3 and self.route))

      if self.allow_recompute:
        postvars = {'place_name': self.new_destination}
        postvars, valid_addr = self.mapbox.set_destination(postvars, self.last_position.longitude, self.last_position.latitude, self.last_bearing)
        logging.debug(f'Set new destination to: {self.new_destination}, valid: {valid_addr}')
        if valid_addr:
          self.destination = self.new_destination
          self.nav_instructions.clear_route_cache()
          self.route = self.nav_instructions.get_current_route()
          self.reroute_counter = 0

  def run(self):
    logging.warning('navigationd init')

    while True:
      gps_msg = self.sm['livelocationd']

      if gps_msg:
        self.last_position = Coordinate(gps_msg.positionGeodetic.value[0], gps_msg.positionGeodetic.value[1])
        if gps_msg.calibratedOrientationNED.valid:
          self.last_bearing = math.degrees(gps_msg.calibratedOrientationNED.value[2])

      self.update_params()

      banner_instructions = ''
      progress = None
      if self.last_position is not None:
        if progress:= self.nav_instructions.get_route_progress(self.last_position.latitude, self.last_position.longitude):
          self.upcoming_turn = self.nav_instructions.get_upcoming_turn_from_progress(progress, self.last_position.latitude, self.last_position.longitude)
          self.current_speed_limit = self.nav_instructions.get_current_speed_limit_from_progress(progress, self.is_metric)

          if progress['current_step']:
            parsed = parse_banner_instructions(progress['current_step']['bannerInstructions'], progress['distance_to_end_of_step'])
            if parsed:
              banner_instructions = parsed['maneuverPrimaryText']

          self.distance_to_next_turn = progress['distance_to_next_turn']
          self.distance_to_end_of_step = progress.get('distance_to_end_of_step', 0.0)
          self.route_progress_percent = progress['route_progress_percent']
          self.distance_from_route = progress['distance_from_route']
          self.route_position_cumulative = progress['route_position_cumulative']

          # Don't recompute in last segment to prevent reroute loops
          if self.route:
            if progress['current_step_index'] == len(self.route['steps']) - 1:
              self.allow_recompute = False

          if self.recompute_allowed:
            self.reroute_counter += 1 if self.distance_from_route > 25 else 0
            logging.debug(f'Reroute counter: {self.reroute_counter}, distance: {self.distance_from_route}')

      msg = messenger.schema.MapboxSettings.new_message()
      msg.timestamp = int(time.monotonic() * 1000)
      msg.upcomingTurn = self.upcoming_turn
      msg.currentSpeedLimit = self.current_speed_limit
      msg.bannerInstructions = banner_instructions
      msg.distanceToNextTurn = self.distance_to_next_turn
      msg.distanceToEndOfStep = self.distance_to_end_of_step
      msg.routeProgressPercent = self.route_progress_percent
      msg.distanceFromRoute = self.distance_from_route
      msg.routePositionCumulative = self.route_position_cumulative
      msg.totalDistanceRemaining = progress.get('total_distance_remaining', 0.0) if progress else 0.0
      msg.totalTimeRemaining = progress.get('total_time_remaining', 0.0) if progress else 0.0
      msg.allManeuvers = [messenger.schema.Maneuver.new_message(distance=m['distance'], type=m['type'], modifier=m['modifier']) for m in progress.get('all_maneuvers', [])] if progress else []
      msg.speedLimitSign = 'mutcd'
      self.pm.send('navigationd', msg)
      time.sleep(self.pm['navigationd'].rate_hz)


def main():
  logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  nav = Navigationd()
  nav.run()
