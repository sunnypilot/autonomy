import time
import tempfile
import os
import pytest

import messaging.messenger as messenger


def test_load_registry():
  registry = messenger.load_registry("messaging/services.yaml")
  assert "navigationd" in registry
  assert registry["navigationd"]["port"] == 3001
  assert registry["navigationd"]["rate_hz"] == 5

def test_pub_master_init():
  pub = messenger.PubMaster("navigationd")
  assert pub.port == 3001
  assert pub.rate_hz == 5

def test_pub_master_unknown_service():
  with pytest.raises(KeyError):
    messenger.PubMaster("unknown_service")

def test_sub_master_init():
  sub = messenger.SubMaster("navigationd")
  assert "navigationd" in sub.services

def test_sub_master_unknown_service():
  with pytest.raises(ValueError):
    messenger.SubMaster("unknown_service")

def test_message_serialization():
  msg = messenger.schema.MapboxSettings.new_message()
  msg.searchInput = 42
  msg.timestamp = 123456

  serialized = msg.to_bytes()
  assert isinstance(serialized, bytes)

  with messenger.schema.MapboxSettings.from_bytes(serialized) as parsed:
    assert parsed.to_dict()["searchInput"] == 42
    assert parsed.to_dict()["timestamp"] == 123456

def test_pub_sub_integration():
  # Create temp service config
  with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as file:
    file.write("""
services:
- name: test_service
  port: 4004
  rate_hz: 10
  schema: MapboxSettings
""")
    temp_path = file.name

  try:
    pub = messenger.PubMaster("test_service", registry_path=temp_path)
    sub = messenger.SubMaster("test_service", registry_path=temp_path)
    time.sleep(0.0005)  # allow sockets to connect. 0.5ms should be enough on localhost

    msg = messenger.schema.MapboxSettings.new_message()
    msg.searchInput = 999
    msg.timestamp = 777888
    pub.publish(msg)

    time.sleep(0.0005)

    received = sub["test_service"]
    assert received is not None
    assert received.searchInput == 999
    assert received.timestamp == 777888
  except Exception as e:
    print(f"Error during pub-sub integration test: {e}")
    raise
  finally:
    os.unlink(temp_path)

def test_multiple_services():
  with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as file:
    file.write("""
services:
- name: service1
  port: 4005
  rate_hz: 5
  schema: MapboxSettings
- name: service2
  port: 4006
  rate_hz: 5
  schema: MapboxSettings
""")
    temp_path = file.name

  try:
    pub1 = messenger.PubMaster("service1", registry_path=temp_path)
    pub2 = messenger.PubMaster("service2", registry_path=temp_path)
    sub1 = messenger.SubMaster("service1", registry_path=temp_path)
    sub2 = messenger.SubMaster("service2", registry_path=temp_path)
    time.sleep(0.0005)

    # Send different messages
    msg1 = messenger.schema.MapboxSettings.new_message()
    msg1.searchInput = 111
    pub1.publish(msg1)

    msg2 = messenger.schema.MapboxSettings.new_message()
    msg2.searchInput = 222
    pub2.publish(msg2)

    time.sleep(0.0005)

    # Verify both received
    assert sub1["service1"].searchInput == 111
    assert sub2["service2"].searchInput == 222
  except Exception as e:
    print(f"Error during multiple services test: {e}")
    raise
  finally:
    os.unlink(temp_path)

def test_timeout_behavior():
  sub = messenger.SubMaster("navigationd")

  with sub._lock:
    msg = messenger.schema.MapboxSettings.new_message()
    msg.searchInput = 42
    data = msg.to_bytes()
    sub.services["navigationd"]["last_data"] = data
    sub.services["navigationd"]["received_at"] = time.monotonic() - 10  # 10 seconds ago

  assert sub["navigationd"] is None
  assert not sub.alive["navigationd"]

def test_alive_property():
  sub = messenger.SubMaster("navigationd")
  assert not sub.alive["navigationd"]  # No messages yet
  
  # create a recent message
  with sub._lock:
    msg = messenger.schema.MapboxSettings.new_message()
    msg.searchInput = 42
    data = msg.to_bytes()
    sub.services["navigationd"]["last_data"] = data
    sub.services["navigationd"]["received_at"] = time.monotonic()
  
  assert sub.alive["navigationd"]
  
  # fake an old message
  with sub._lock:
    sub.services["navigationd"]["received_at"] = time.monotonic() - 10
  
  assert not sub.alive["navigationd"]

def test_nested_message_structure():
  # small integration test for nested structure used in navigationd
  msg = messenger.schema.MapboxSettings.new_message()
  msg.navData.current.latitude = 37.7749
  msg.navData.current.longitude = -122.4194
  msg.navData.current.placeName = "San Francisco"
  msg.navData.route.steps = [
    {"instruction": "Turn left", "distance": 100.0, "duration": 60.0, "maneuver": "left", "location": {"longitude": -122.4, "latitude": 37.7}},
  ]
  msg.timestamp = 123456789

  # Serialize and deserialize
  serialized = msg.to_bytes()
  with messenger.schema.MapboxSettings.from_bytes(serialized) as parsed:
    assert parsed.navData.current.latitude == 37.7749
    assert parsed.navData.current.longitude == -122.4194
    assert parsed.navData.current.placeName == "San Francisco"
    assert len(parsed.navData.route.steps) == 1
    assert parsed.navData.route.steps[0].instruction == "Turn left"
    assert parsed.timestamp == 123456789
