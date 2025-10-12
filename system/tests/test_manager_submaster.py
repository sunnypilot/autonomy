import time
import multiprocessing

import messaging.messenger as messenger
from system.manager import main as manager_main


def test_manager_submaster_integration():
  manager = multiprocessing.Process(target=manager_main)
  manager.start()
  time.sleep(0.1)

  assert manager.is_alive(), "Manager is not alive"

  try:
    sm = messenger.SubMaster()
    messages_received = []
    for _ in range(50):  # Run for 5 seconds
      for name in sm.services.keys():
        msg = sm[name]
        if msg:
          messages_received.append((name, str(msg)))
          print(f"Received message from {name}: {msg}")
      time.sleep(0.1)

    navigationd_messages = [msg for name, msg in messages_received if name == 'navigationd']  # Check that messages were received
    assert len(navigationd_messages) > 0, f"No messages found for navigationd. All messages: {messages_received}"

  finally:
    sm.close()
    manager.terminate()
    manager.join(timeout=5.0)
