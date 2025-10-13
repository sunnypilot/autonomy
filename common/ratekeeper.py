import time
import logging
from collections import deque
from setproctitle import getproctitle


class Ratekeeper:
  def __init__(self, rate):
    self.interval = rate
    self._process_name = getproctitle()
    self._last_monitor_time = -1.0
    self._next_frame_time = -1.0
    self.avg_dt = deque(maxlen=100)
    self.avg_dt.append(self.interval)

  @property
  def lagging(self):
    expected_dt = self.interval * (1 / 0.9)  # 10% tolerance
    return sum(self.avg_dt) / len(self.avg_dt) > expected_dt if self.avg_dt else False

  def keep_time(self) -> bool:
    lagged = self.monitor_time()
    if self._remaining > 0:
      time.sleep(self._remaining)
    return lagged

  def monitor_time(self) -> bool:
    if self._last_monitor_time < 0:
      self._next_frame_time = time.monotonic() + self.interval
      self._last_monitor_time = time.monotonic()

    prev = self._last_monitor_time
    self._last_monitor_time = time.monotonic()
    self.avg_dt.append(self._last_monitor_time - prev)

    lagged = False
    remaining = self._next_frame_time - time.monotonic()
    self._next_frame_time += self.interval

    if self.lagging:
      logging.warning(f"{self._process_name} lagging by {-remaining * 1000:.2f} ms")
      lagged = True

    self._remaining = remaining
    return lagged
