import time
import multiprocessing
import yaml
from pathlib import Path

import messaging.messenger as messenger
from system.manager import main as manager_main


def test_ratekeeper_integration():
  original_services = Path("messaging/services.yaml")
  with original_services.open() as f:
    config = yaml.safe_load(f)

  rates = {service["name"]: service["rate_hz"] for service in config["services"]}
  manager = multiprocessing.Process(target=manager_main)
  manager.start()
  time.sleep(1.0)

  try:
    sm = messenger.SubMaster()
    time.sleep(1.0)
    start_time = time.monotonic()
    message_counts = {name: 0 for name in rates}
    last_timestamps = {name: 0 for name in rates}
    last_lats = {name: float('-inf') for name in rates}

    while time.monotonic() - start_time < 5.0:
      for name in rates:
        msg = sm[name]
        if msg:
          if name == 'navigationd' and hasattr(msg, 'timestamp') and msg.timestamp > last_timestamps[name]:
            message_counts[name] += 1
            last_timestamps[name] = msg.timestamp
          elif name == 'livelocationd' and hasattr(msg, 'positionGeodetic') and msg.positionGeodetic.value[0] > last_lats[name]:
            message_counts[name] += 1
            last_lats[name] = msg.positionGeodetic.value[0]
    # Check that we received at least 4 secs worth of messages for each service
    for name, count in message_counts.items():
      expected_min = int(rates[name] * 4)
      assert count >= expected_min, f"Service {name} received {count} messages, expected at least {expected_min} for {rates[name]} Hz"

    # timing between messages
    for name in rates:
      if message_counts[name] > 1:
        avg_interval = 5.0 / message_counts[name]
        expected_interval = 1.0 / rates[name]
        assert abs(avg_interval - expected_interval) / expected_interval < 0.2, (  # Allow 20% tolerance
          f"Service {name} avg interval {avg_interval:.3f}s, expected {expected_interval:.3f}s"
        )

  finally:
    sm.close()
    manager.terminate()
    manager.join(timeout=5.0)
