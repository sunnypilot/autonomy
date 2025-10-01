import time
import logging

from messaging.messenger import schema, PubMaster


def run():
  logging.warning("navigationd init")
  pub = PubMaster('navigationd')
  period = 1.0 / pub.rate_hz

  while True:
    msg = schema.MapboxSettings.new_message()
    msg.timestamp = int(time.monotonic() * 1000)
    pub.publish(msg)
    time.sleep(period)
