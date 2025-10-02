import time
import logging

import messaging.messenger as messenger


def run():
  logging.warning("navigationd init")
  pub = messenger.PubMaster('navigationd')
  period = 1.0 / pub.rate_hz

  while True:
    msg = messenger.schema.MapboxSettings.new_message()
    msg.timestamp = int(time.monotonic() * 1000)
    pub.publish(msg)
    time.sleep(period)
