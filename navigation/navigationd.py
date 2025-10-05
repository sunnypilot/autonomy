import time
import logging

import messaging.messenger as messenger


class Navigationd:
  def __init__(self):
    self.pm = messenger.PubMaster('navigationd')

  def run(self):
    logging.warning("navigationd init")

    while True:
      msg = messenger.schema.MapboxSettings.new_message()
      msg.timestamp = int(time.monotonic() * 1000)
      self.pm.send('navigationd', msg)
      time.sleep(self.pm['navigationd'].rate_hz)


def main():
  nav = Navigationd()
  nav.run()
