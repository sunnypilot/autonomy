import time
import tempfile
import os

import pytest

import messaging.messenger as messenger


def poll_for_message(subscriber, service_name, timeout=1.0, poll_interval=0.0001):
  """Poll subscriber for a message until received or timeout."""
  start_time = time.monotonic()
  while (time.monotonic() - start_time) < timeout:
    msg = subscriber[service_name]
    if msg is not None:
      return msg
    time.sleep(poll_interval)
  return None

def test_load_registry():
  registry = messenger.load_registry("messaging/services.yaml")
  assert "navigationd" in registry
  assert registry["navigationd"]["rate_hz"] == 5
  assert registry["navigationd"]["schema_type"] == messenger.schema.MapboxSettings

def test_sub_and_pub_master_init():
  pub = messenger.PubMaster("navigationd")
  assert pub.rate_hz == 5

  sub = messenger.SubMaster("navigationd")
  assert "navigationd" in sub.services

def test_pub_master_unknown_service():
  with pytest.raises(KeyError):
    messenger.PubMaster("unknown_service")

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
  pub = messenger.PubMaster("navigationd")
  sub = messenger.SubMaster("navigationd")
  time.sleep(0.01)

  msg = messenger.schema.MapboxSettings.new_message()
  msg.searchInput = 999
  msg.timestamp = 777888
  pub.publish(msg)

  received = poll_for_message(sub, "navigationd")
  assert received is not None
  assert received.searchInput == 999
  assert received.timestamp == 777888


def test_multiple_services():
  with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as file:
    file.write("""
services:
- name: service1
  rate_hz: 5
  schema: MapboxSettings
- name: service2
  rate_hz: 5
  schema: MapboxSettings
""")
    temp_path = file.name

  # Send a message from two services and verify receipt
  try:
    pub1 = messenger.PubMaster("service1", registry_path=temp_path)
    pub2 = messenger.PubMaster("service2", registry_path=temp_path)
    sub1 = messenger.SubMaster("service1", registry_path=temp_path)
    sub2 = messenger.SubMaster("service2", registry_path=temp_path)

    msg1 = messenger.schema.MapboxSettings.new_message()
    msg1.searchInput = 111
    pub1.publish(msg1)

    msg2 = messenger.schema.MapboxSettings.new_message()
    msg2.searchInput = 222
    pub2.publish(msg2)

    received1 = poll_for_message(sub1, "service1")
    received2 = poll_for_message(sub2, "service2")

    assert received1 is not None
    assert received1.searchInput == 111
    assert received2 is not None
    assert received2.searchInput == 222
  finally:
    os.unlink(temp_path)

def test_alive_property():
  sub = messenger.SubMaster("navigationd")
  assert not sub.alive["navigationd"]  # No messages yet

  with sub._lock:
    msg = messenger.schema.MapboxSettings.new_message()
    msg.searchInput = 42
    data = msg.to_bytes()
    sub.services["navigationd"]["last_data"] = data  # send data, set to current time
    sub.services["navigationd"]["received_at"] = time.monotonic()
  assert sub.alive["navigationd"]

  # fake an old message. This also tests timeout from __getitem__
  with sub._lock:
    sub.services["navigationd"]["received_at"] = time.monotonic() - 10
  assert not sub.alive["navigationd"]

def test_nested_message_structure():
  msg = messenger.schema.MapboxSettings.new_message()
  msg.navData.current.latitude = 37.7749
  msg.navData.current.longitude = -122.4194
  msg.navData.current.placeName = "San Francisco"
  msg.navData.route.steps = [  # something basic, this is one step of a fake route, but has enough detail to test the structure of the msg.
    {"instruction": "Turn left", "distance": 100.0, "duration": 60.0, "maneuver": "left", "location": {"longitude": -122.4, "latitude": 37.7}},
  ]
  msg.timestamp = 123456789

  serialized = msg.to_bytes()
  with messenger.schema.MapboxSettings.from_bytes(serialized) as parsed:
    assert parsed.navData.current.latitude == 37.7749
    assert parsed.navData.current.longitude == -122.4194
    assert parsed.navData.current.placeName == "San Francisco"
    assert len(parsed.navData.route.steps) == 1
    assert parsed.navData.route.steps[0].instruction == "Turn left"
    assert parsed.timestamp == 123456789
