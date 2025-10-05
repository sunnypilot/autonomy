# Messaging Module

This module provides an easy to use publish-subscribe messaging system.

## Components

- **`messenger.py`**: Classes for publishing (`PubMaster`) and subscribing (`SubMaster`) to messages across services.

- **`autonomy.capnp`**: Capnp message structures (e.g., `MapboxSettings` for navigation data).

- **`services.yaml`**: Service config listing available services, ports, and schemas attached.

### Example Usage
```py
import messaging.messenger as messenger

class Navigation:
  def __init__(self):
    self.sm = messenger.SubMaster('navigationd')
    self.pm = messenger.PubMaster('navigationd')
    self.latitude: float = 0.0
    self.longitude: float = 0.0

  def update_location(self):
    nav = self.sm['navigationd']
    if nav:  # messenger will return None if message times out
      self.latitude = nav.navData.current.latitude
      self.longitude = nav.navData.current.longitude

  def publish_location(self, latitude: float, longitude: float):
    msg = messenger.schema.MapboxSettings.new_message()
    msg.navData.current.latitude = latitude
    msg.navData.current.longitude = longitude
    msg.timestamp = 123456
    self.pm.publish(msg)
```
