import time
import logging
from collections import deque
from setproctitle import getproctitle


class Ratekeeper:
  def __init__(self, rate):
    self.interval = rate
    self.next_time = time.monotonic()
    self.frame = 0
    self._process_name = getproctitle()
    self._last_time = -1.0
    self.avg_dt = deque(maxlen=100)
    self.avg_dt.append(self.interval)

  @property
  def lagging(self):
    expected_dt = self.interval * (1 / 0.9)  # 10% tolerance
    return sum(self.avg_dt) / len(self.avg_dt) > expected_dt if self.avg_dt else False

  def keep_time(self):
    self.frame += 1
    now = time.monotonic()

    if self._last_time >= 0:
      dt = now - self._last_time
      self.avg_dt.append(dt)

    self._last_time = now
    self.next_time += self.interval
    sleep_time = self.next_time - now
    lagged = sleep_time < 0

    if lagged:
      if self.lagging:
        logging.warning(f"{self._process_name} lagging by {-sleep_time * 1000:.2f} ms")
      self.next_time = now
    else:
      time.sleep(sleep_time)

    return lagged
