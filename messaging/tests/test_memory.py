import os
import psutil
import time

import pytest
import tracemalloc

import messaging.messenger as messenger


def get_memory_stats(top=10):
  """Get top memory allocations for profiling."""
  snapshot = tracemalloc.take_snapshot()
  return "\n".join(str(stat) for stat in snapshot.statistics('lineno')[:top])


def analyze_memory_stats(stats_str):
  """Split memory stats string and return metrics."""
  allocations = []

  for line in stats_str.strip().split('\n'):
    if 'size=' not in line or 'count=' not in line:
      continue

    try:
      # Parse: size=x KiB, count=x, average=x B
      size_part = line.split('size=')[1].split(',')[0].strip()
      count_part = line.split('count=')[1].split(',')[0].strip()
      size_bytes = float(size_part.replace(' KiB', '')) * 1024 if 'KiB' in size_part else float(size_part.replace(' B', ''))
      allocations.append((size_bytes, int(count_part), line))
    except (ValueError, IndexError):
      continue

  return {
    'total_allocations': len(allocations),
    'top_allocation': max(allocations, key=lambda x: x[0]) if allocations else (0, 0, ''),
    'allocations': allocations
  }


@pytest.mark.skipif(not os.getenv("RUN_MEMORY_TEST"), reason="not enabled, run export RUN_MEMORY_TEST=1")
def test_memory_leak_submaster(capsys):
  tracemalloc.start()
  process = psutil.Process(os.getpid())
  initial_memory = process.memory_info().rss / 1024 / 1024  # bytes to MB

  try:
    pub = messenger.PubMaster("navigationd")
    sub = messenger.SubMaster("navigationd")
    time.sleep(.01)

    for i in range(36000):  # 30 min
      if i % 4 == 0:  # Publish at 5 Hz
        msg = messenger.schema.MapboxSettings.new_message()

        msg.searchInput = i
        msg.timestamp = int(time.monotonic())

        msg.lastGPSPosition.longitude = -122.4 + (i % 100) * 0.01
        msg.lastGPSPosition.latitude = 37.7 + (i % 100) * 0.01

        msg.navData.current.latitude = 37.8 + (i % 50) * 0.01
        msg.navData.current.longitude = -122.3 + (i % 50) * 0.01
        msg.navData.current.placeName = f"Sunnypilot HQ {i % 10}"

        msg.navData.route.steps = [
          {"instruction": f"Turn {i % 100}", "distance": 100.0 + (i % 100) * 10.0, "duration": 60.0, "maneuver": "left", "location": {"longitude": -122.4 + (i % 100) * 0.01, "latitude": 37.7 + (i % 100) * 0.01}}]
        msg.navData.route.totalDistance = 175.0 + i * 10.0
        msg.navData.route.totalDuration = 60.0 + i * 5.0
        msg.navData.route.geometry = [{"longitude": -122.4 + j * 0.01, "latitude": 37.7 + j * 0.01} for j in range(10)]
        msg.navData.route.maxspeed = [{"speed": 50.0 + (i % 5) * 10.0, "unit": "mph"}]

        pub.publish(msg)

      # Query at 20 Hz to build up cache usage
      received = sub["navigationd"]
      if received is not None:
        _ = received.navData.route.steps
      time.sleep(0.05)

    final_memory = process.memory_info().rss / 1024 / 1024  # bytes to MB
    memory_increase = final_memory - initial_memory
    memory_stats = get_memory_stats()
    print("Memory Stats:\n", memory_stats)

    # flag if above 5 MB, may be conservative
    assert memory_increase < 5, f"Potential leak: {memory_increase:.2f} MB increase"

    # Analyze memory allocations for potential leaks
    stats_analysis = analyze_memory_stats(memory_stats)
    assert stats_analysis['total_allocations'] > 0, "No memory allocations found"

    top_size, _, top_line = stats_analysis['top_allocation']
    assert top_size < 100 * 1024, f"Excessive allocation: {top_size/1024:.1f} KiB in {top_line}"

    messenger_allocations = [allocation for allocation in stats_analysis['allocations'] 
                            if 'messenger.py' in allocation[2]]

    if messenger_allocations:
      total_messenger_size = sum(allocation[0] for allocation in messenger_allocations)
      assert total_messenger_size < 50 * 1024, f"Messenger memory usage too high: {total_messenger_size/1024:.1f} KiB"

      for size, count, line in messenger_allocations:
        if size < 1024:  # Small allocations
          assert count < 1000, f"Too many small allocations in messenger: {count} objects of {size} bytes in {line}"

  finally:
    sub.close()
    tracemalloc.stop()
