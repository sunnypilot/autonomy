import time
import logging

import messaging.messenger as messenger


class Livelocationd:
  def __init__(self):
    self.pm = messenger.PubMaster('livelocationd')
    self.lat = 34.2299
    self.lon = -119.1733
    self.lat_increment = 0.0001
    self.lon_increment = -0.0001

  def run(self):
    logging.warning("livelocationd init")

    while True:
      msg = messenger.schema.LiveLocationKalman.new_message()
      msg.positionGeodetic.value = [self.lat, self.lon]
      msg.positionGeodetic.std = [0.0, 0.0]
      msg.positionGeodetic.valid = True
      self.pm.send('livelocationd', msg)

      self.lat += self.lat_increment
      self.lon += self.lon_increment

      time.sleep(self.pm['livelocationd'].rate_hz)


def main():
  loc = Livelocationd()
  loc.run()
