import time
import logging

import messaging.messenger as messenger
from common.ratekeeper import Ratekeeper


class Navigationd:
  def __init__(self):
    self.pm = messenger.PubMaster('navigationd')
    self.rk = Ratekeeper(self.pm['navigationd'].rate_hz)

  def run(self):
    logging.warning("navigationd init")

    while True:
      msg = messenger.schema.MapboxSettings.new_message()
      msg.timestamp = int(time.monotonic() * 1000)
      self.pm.send('navigationd', msg)
      self.rk.keep_time()


def main():
  nav = Navigationd()
  nav.run()
