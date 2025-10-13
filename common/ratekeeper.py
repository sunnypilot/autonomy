import time
import logging


class Ratekeeper:
  def __init__(self, interval, name="", print_delay_threshold=0.0):
    self.interval = interval
    self.next_time = time.monotonic()
    self.print_delay_threshold = print_delay_threshold
    self.frame = 0
    self.name = name

  def keep_time(self):
    self.frame += 1
    self.next_time += self.interval
    now = time.monotonic()
    sleep_time = self.next_time - now
    lagged = sleep_time < 0
    if lagged:
      if self.print_delay_threshold > 0 and sleep_time < -self.print_delay_threshold:
        logging.warning(f"{self.name} lagging by {-sleep_time * 1000:.2f} ms")
      self.next_time = now
    else:
      time.sleep(sleep_time)
    return lagged
