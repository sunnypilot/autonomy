import time
import os
import psutil
import tracemalloc
import pytest

os.environ["ENABLE_MEMORY_PROFILING"] = "1"
import messaging.messenger as messenger


def get_memory_stats(top=10):
  """Get top memory allocations for profiling."""
  if not os.getenv("ENABLE_MEMORY_PROFILING"):
    return "Memory profiling not enabled. Set ENABLE_MEMORY_PROFILING=1"
  snapshot = tracemalloc.take_snapshot()
  top_stats = snapshot.statistics('lineno')[:top]
  return "\n".join(str(stat) for stat in top_stats)


@pytest.mark.skipif(not os.getenv("RUN_MEMORY_TEST"), reason="Memory test not enabled")
def test_memory_leak_submaster():
  process = psutil.Process(os.getpid())
  initial_memory = process.memory_info().rss / 1024 / 1024  # bytes to MB

  try:
    pub = messenger.PubMaster("navigationd")
    sub = messenger.SubMaster("navigationd")
    time.sleep(.01)

    for i in range(9000):  # ~30 minutes at 0.2s intervals (5 Hz)
      msg = messenger.schema.MapboxSettings.new_message()
      msg.navData.route.steps = [
        {"instruction": f"Turn {i % 100}", "distance": 100.0 + (i % 100) * 10.0, "duration": 60.0, "maneuver": "left", "location": {"longitude": -122.4 + (i % 100) * 0.01, "latitude": 37.7}}]
      msg.searchInput = i
      msg.timestamp = int(time.time())
      pub.publish(msg)
      time.sleep(0.2)

    final_memory = process.memory_info().rss / 1024 / 1024  # bytes to MB
    memory_increase = final_memory - initial_memory
    print("Memory Stats:\n", get_memory_stats())

    # Allow some increase, but flag above 10 MB
    assert memory_increase < 10, f"Potential leak: {memory_increase:.2f} MB increase"
  finally:
    sub.close()
