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

    if 'test_memory.py' in line:
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
    latencies = []
    prev_timestamp = 0.0

    for i in range(36000):  # 30 min
      publish_time = time.perf_counter()
      msg = messenger.schema.MapboxSettings.new_message()

      msg.timestamp = int(publish_time * 1000000)  # microseconds
      msg.upcomingTurn = "left" if i % 4 == 0 else "none"
      msg.currentSpeedLimit = float(50 + (i % 10))
      msg.bannerInstructions = f"Continue for {100 + i % 100} meters"
      msg.distanceToNextTurn = float(100 + i % 200)
      msg.routeProgressPercent = float((i % 100))
      msg.distanceFromRoute = float(i % 50)
      msg.routePositionCumulative = float(i * 10)
      pub.send("navigationd", msg)

      received = sub["navigationd"]
      if received is not None:
        _ = received.timestamp
        _ = received.upcomingTurn
        _ = received.currentSpeedLimit
        _ = received.bannerInstructions
        _ = received.distanceToNextTurn
        _ = received.routeProgressPercent
        _ = received.distanceFromRoute
        _ = received.routePositionCumulative
        if received.timestamp > prev_timestamp:
          latency = time.perf_counter() - (received.timestamp / 1000000)
          latencies.append(latency)
          prev_timestamp = received.timestamp
      time.sleep(0.05)

    final_memory = process.memory_info().rss / 1024 / 1024  # bytes to MB
    memory_increase = final_memory - initial_memory
    memory_stats = get_memory_stats()
    print("Memory Stats:\n", memory_stats)

    if latencies:
      avg_latency = sum(latencies) / len(latencies)
      print(f"Average latency: {avg_latency:.6f}s")
      assert avg_latency < 0.06, f"Average latency {avg_latency:.6f}s exceeds 60ms"

    # flag if above 7.5 MB, may be a bit too conservative
    assert memory_increase < 7.5, f"Potential leak: {memory_increase:.2f} MB increase"

    # check memory allocations for potential leaks
    stats_analysis = analyze_memory_stats(memory_stats)
    assert stats_analysis['total_allocations'] > 0, "No memory allocations found"

    top_size, _, top_line = stats_analysis['top_allocation']
    assert top_size < 256 * 1024, f"Excessive allocation: {top_size/1024:.1f} KiB in {top_line}"

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
