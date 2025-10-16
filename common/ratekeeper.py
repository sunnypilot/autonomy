import time
import logging
from collections import deque
from setproctitle import getproctitle


class Ratekeeper:
  def __init__(self, rate):
    self.interval = rate
    self._process_name = getproctitle()
    self._last_check_time = -1.0
    self._next_target_time = -1.0
    self._delta_times = deque(maxlen=100)

  @property
  def lagging(self):
    tolerance = self.interval * 0.10  # 10% tolerance
    max_tolerated_dt = self.interval + tolerance
    return sum(self._delta_times) / len(self._delta_times) > max_tolerated_dt if self._delta_times else False

  def keep_time(self) -> bool:
    is_lagging = self.monitor_time()
    if self._time_remaining > 0:
      time.sleep(self._time_remaining)
    return is_lagging

  def monitor_time(self) -> bool:
    if self._last_check_time < 0:
      self._next_target_time = time.monotonic() + self.interval
      self._last_check_time = time.monotonic()

    prev = self._last_check_time
    self._last_check_time = time.monotonic()
    self._delta_times.append(self._last_check_time - prev)

    is_lagging = False
    time_remaining = self._next_target_time - time.monotonic()
    self._next_target_time += self.interval

    if self.lagging:
      logging.warning(f"{self._process_name} lagging by {-time_remaining * 1000:.2f} ms")
      is_lagging = True

    self._time_remaining = time_remaining
    return is_lagging
