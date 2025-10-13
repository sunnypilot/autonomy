import logging
import math

import messaging.messenger as messenger
from common.ratekeeper import Ratekeeper


class Livelocationd:
  '''Debug daemon to simulate live GPS updates.'''

  def __init__(self):
    self.pm = messenger.PubMaster('livelocationd')
    self.rk = Ratekeeper(self.pm['livelocationd'].rate_hz)

    # Initial coordinates set along a route navigating to a random house in CA that google picked: 580 Winchester Dr, Oxnard, CA.
    self.lat = 34.2299
    self.lon = -119.1733

    self.lat_increment = 0.0001
    self.lon_increment = -0.0001
    self.bearing = math.atan2(self.lon_increment, self.lat_increment)

  def run(self):
    logging.warning("livelocationd init")

    while True:
      # Send the same message that openpilot/sunnypilot expects to receive from livelocationkalman. That way, it'll be a simple swap in for on device use.
      msg = messenger.schema.LiveLocationKalman.new_message()
      msg.positionGeodetic.value = [self.lat, self.lon]
      msg.positionGeodetic.std = [0.0, 0.0]
      msg.positionGeodetic.valid = True

      msg.calibratedOrientationNED.value = [0.0, 0.0, self.bearing]  # roll, pitch, yaw (all I care about is yaw)
      msg.calibratedOrientationNED.std = [0.0, 0.0, 0.0]
      msg.calibratedOrientationNED.valid = True

      self.pm.send('livelocationd', msg)

      self.lat += self.lat_increment
      self.lon += self.lon_increment

      self.rk.keep_time()


def main():
  loc = Livelocationd()
  loc.run()
