import time
import logging

import messaging.messenger as messenger
from navigation.navigation_helpers.nav_instructions import NavigationInstructions
from navigation.navigation_helpers.mapbox_integration import MapboxIntegration
from navigation.common.params.params import Params
from navigation.navd.helpers import Coordinate


class Navigationd:
  def __init__(self):
    self.params = Params()
    self.mapbox = MapboxIntegration()
    self.nav_instructions = NavigationInstructions()
    self.sm = messenger.SubMaster('livelocationd')
    self.pm = messenger.PubMaster('navigationd')
    self.route = None
    self.destination = None
    self.frame = -1
    self.last_position = None
    self.is_metric = False

  def update_params(self):
    if self.frame % 15 == 0 and self.last_position is not None:
      self.is_metric = bool(self.params.get('IsMetric', return_default=True))
      new_destination = str(self.params.get('MapboxRoute', encoding='utf8'))
      if new_destination != self.destination and new_destination != '':
        postvars = {'place_name': new_destination}
        postvars, valid_addr = self.mapbox.set_destination(postvars, self.last_position.longitude, self.last_position.latitude)
        print(f'Set new destination to: {new_destination}, valid: {valid_addr}')  # debugging. delete me later!
        if valid_addr:
          self.destination = new_destination
          self.nav_instructions.clear_route_cache()
          self.route = self.nav_instructions.get_current_route()
    self.frame += 1

  def run(self):
    logging.warning('navigationd init')

    while True:
      gps_msg = self.sm['livelocationd']

      if gps_msg:
        self.last_position = Coordinate(gps_msg.positionGeodetic.value[0], gps_msg.positionGeodetic.value[1])
      else:
        self.last_position = None

      self.update_params()

      upcoming_turn = 'none'
      current_speed_limit = 0
      current_instruction = ''
      distance_to_next_turn = 0.0
      route_progress_percent = 0.0
      distance_from_route = 0.0
      route_position_cumulative = 0.0

      if self.last_position is not None:
        progress = self.nav_instructions.get_route_progress(self.last_position.latitude, self.last_position.longitude)
        if progress:
          upcoming_turn = self.nav_instructions.get_upcoming_turn_from_progress(progress, self.last_position.latitude, self.last_position.longitude)
          current_speed_limit = self.nav_instructions.get_current_speed_limit_from_progress(progress, self.is_metric)
          current_instruction = progress['current_step']['instruction']
          distance_to_next_turn = progress['distance_to_next_turn']
          route_progress_percent = progress['route_progress_percent']
          distance_from_route = progress['distance_from_route']
          route_position_cumulative = progress['route_position_cumulative']

      msg = messenger.schema.MapboxSettings.new_message()
      msg.upcomingTurn = upcoming_turn
      msg.currentSpeedLimit = current_speed_limit
      msg.currentInstruction = current_instruction
      msg.distanceToNextTurn = distance_to_next_turn
      msg.routeProgressPercent = route_progress_percent
      msg.distanceFromRoute = distance_from_route
      msg.routePositionCumulative = route_position_cumulative
      self.pm.send('navigationd', msg)
      time.sleep(self.pm['navigationd'].rate_hz)


def main():
  nav = Navigationd()
  nav.run()
