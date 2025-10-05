import time
import tempfile
import os

import pytest

import messaging.messenger as messenger


class TestMessenger:
  def setup_method(self):
    self.instances: list = []

  def teardown_method(self):
    for instance in self.instances:
      instance.close()
    self.instances: list = []

  def test_load_registry(self):
    registry = messenger.load_registry("messaging/services.yaml")
    assert "navigationd" in registry
    assert registry["navigationd"]["rate_hz"] == 5
    assert registry["navigationd"]["schema_type"] == messenger.schema.MapboxSettings

  def test_sub_and_pub_master_init(self):
    pub = messenger.PubMaster("navigationd")
    assert pub['navigationd'].rate_hz == 5

    sub = messenger.SubMaster("navigationd")
    self.instances.append(sub)
    assert "navigationd" in sub.services

  def test_sub_and_pub_master_unknown_service(self):
    with pytest.raises(KeyError):
      messenger.PubMaster("unknown_service")

    with pytest.raises(ValueError):
      messenger.SubMaster("unknown_service")

  def test_message_serialization(self):
    msg = messenger.schema.MapboxSettings.new_message()
    msg.searchInput = 42
    msg.timestamp = 123456

    serialized = msg.to_bytes()
    assert isinstance(serialized, bytes)

    with messenger.schema.MapboxSettings.from_bytes(serialized) as parsed:
      assert parsed.to_dict()["searchInput"] == 42
      assert parsed.to_dict()["timestamp"] == 123456

  def test_pub_sub_integration(self):
    pub = messenger.PubMaster("navigationd")
    sub = messenger.SubMaster("navigationd")
    self.instances.append(sub)
    time.sleep(0.01)

    msg = messenger.schema.MapboxSettings.new_message()
    msg.searchInput = 999
    msg.timestamp = 777888
    pub.send('navigationd', msg)
    time.sleep(0.01)

    received = sub["navigationd"]
    assert received is not None
    assert received.searchInput == 999
    assert received.timestamp == 777888

  def test_multiple_services(self):
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
      pub = messenger.PubMaster(["service1", "service2"], registry_path=temp_path)
      sub = messenger.SubMaster(["service1", "service2"], registry_path=temp_path)
      self.instances.append(sub)
      time.sleep(0.01)

      msg1 = messenger.schema.MapboxSettings.new_message()
      msg1.searchInput = 111
      pub.send("service1", msg1)

      msg2 = messenger.schema.MapboxSettings.new_message()
      msg2.searchInput = 222
      pub.send("service2", msg2)
      time.sleep(0.01)

      received1 = sub['service1']
      received2 = sub['service2']

      assert received1 is not None
      assert received1.searchInput == 111
      assert received2 is not None
      assert received2.searchInput == 222
    finally:
      os.unlink(temp_path)

  def test_alive_property(self):
    pub = messenger.PubMaster("navigationd")
    sub = messenger.SubMaster("navigationd")
    self.instances.append(sub)
    time.sleep(0.01)
    assert not sub.alive["navigationd"]  # No messages yet

    msg = messenger.schema.MapboxSettings.new_message()
    msg.searchInput = 42
    data = pub.send('navigationd', msg)
    time.sleep(0.01)

    sub.services["navigationd"]["last_data"] = data
    sub.services["navigationd"]["received_at"] = time.monotonic()  # set to current time
    assert sub.alive["navigationd"]

    # fake an old message. This also tests timeout from getitem, which is 2 seconds for navigationd
    with sub._lock:
      sub.services["navigationd"]["received_at"] = time.monotonic() - 2.0
    assert not sub.alive["navigationd"]

  def test_nested_message_structure(self):
    pub = messenger.PubMaster("navigationd")
    sub = messenger.SubMaster("navigationd")
    self.instances.append(sub)
    time.sleep(0.01)

    msg = messenger.schema.MapboxSettings.new_message()
    msg.navData.current.latitude = 37.77493
    msg.navData.current.longitude = -122.41945
    msg.navData.current.placeName = "San Francisco"
    msg.navData.route.steps = [  # something basic, this is one step of a fake route, but has enough detail to test the structure of the msg.
      {"instruction": "Turn left", "distance": 100.0, "duration": 60.0, "maneuver": "left", "location": {"longitude": -122.4, "latitude": 37.7}},
    ]
    msg.timestamp = 123456789

    pub.send('navigationd', msg)
    time.sleep(0.01)
    received = sub["navigationd"]

    assert received.navData.current.latitude == 37.77493
    assert received.navData.current.longitude == -122.41945
    assert received.navData.current.placeName == "San Francisco"
    assert len(received.navData.route.steps) == 1
    assert received.navData.route.steps[0].instruction == "Turn left"
    assert received.timestamp == 123456789
