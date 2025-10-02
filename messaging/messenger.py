import threading
import time
import logging

import capnp
import yaml
import zmq


schema = capnp.load("messaging/autonomy.capnp")

def load_registry(path="messaging/services.yaml") -> dict:
  with open(path) as file:
    config = yaml.safe_load(file)
  registry = {}
  for service in config["services"]:
    registry[service["name"]] = {
      "port": service["port"],
      "schema_type": getattr(schema, service["schema"]),
      "rate_hz": service.get("rate_hz", 1),
    }
  return registry


class PubMaster:
  """Publishes messages to ZMQ publisher socket."""
  def __init__(self, name, registry_path="messaging/services.yaml") -> None:
    self.registry: dict[str, dict] = load_registry(registry_path)
    self.port: int = self.registry[name]["port"]
    self.rate_hz: int = self.registry[name]["rate_hz"]
    
    self.context = zmq.Context()
    self.socket = self.context.socket(zmq.PUB)
    self.socket.bind(f"tcp://localhost:{self.port}")

  def publish(self, msg) -> None:
    serialized = msg.to_bytes()
    self.socket.send(serialized)


class SubMaster:
  """Subscribes to multiple ZMQ publisher sockets and maintains latest messages."""
  def __init__(self, service_names=None, registry_path="messaging/services.yaml") -> None:
    self.registry: dict[str, dict] = load_registry(registry_path)
    if service_names is None:
      service_names = list(self.registry.keys())
    if isinstance(service_names, str):
      service_names = [service_names]

    self.services: dict[str, dict] = {}
    self._lock = threading.Lock()
    self.context = zmq.Context()
    self._running: bool = True
    self._threads: list[threading.Thread] = []

    for name in service_names:
      if name not in self.registry:
        raise ValueError(f"Unknown service {name}")
      svc = self.registry[name]
      port = svc["port"]
      schema_type = svc["schema_type"]
      
      socket = self.context.socket(zmq.SUB)
      socket.connect(f"tcp://localhost:{port}")
      socket.setsockopt(zmq.SUBSCRIBE, b"")  # Subscribe to all messages
      
      self.services[name] = {
        "socket": socket,
        "schema_type": schema_type,
        "last_data": None,
        "received_at": None,
        "timeout_seconds": 10.0 / svc["rate_hz"],
      }
      thread = threading.Thread(target=self._loop, args=(name,), daemon=True, name=f"SubMaster-{name}")
      thread.start()
      self._threads.append(thread)

  def _loop(self, name) -> None:
    socket = self.services[name]["socket"]
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    while self._running:
      socks = dict(poller.poll(timeout=1000))  # 1 second timeout
      if socket in socks and socks[socket] == zmq.POLLIN:
        try:
          data = socket.recv()
          with self._lock:
            self.services[name]["last_data"] = data
            self.services[name]["received_at"] = time.monotonic()
        except Exception as e:
          logging.error(f"Error receiving message for {name}: {e}", exc_info=True)

  def __getitem__(self, name):
    with self._lock:
      if name not in self.services:
        raise KeyError(f"Service {name} not subscribed")
      data = self.services[name]["last_data"]
      received_at = self.services[name]["received_at"]
      timeout = self.services[name]["timeout_seconds"]
      if data and received_at and (time.monotonic() - received_at) > timeout:
        return None
      if data:
        cm = self.services[name]["schema_type"].from_bytes(data)
        return cm.__enter__()
      return None

  @property
  def alive(self):
    # Return a dict of service name to a bool indicating if the last message was received within timeout
    with self._lock:
      return {
        name: (
          self.services[name]["received_at"] is not None and
          (time.monotonic() - self.services[name]["received_at"]) < (self.services[name]["timeout_seconds"])
        )
        for name in self.services
      }

  def close(self):
    self._running = False
    for thread in self._threads:
      thread.join(timeout=1.0)
    for svc in self.services.values():
      if 'socket' in svc and svc['socket']:
        svc['socket'].close()
    if hasattr(self, 'context') and self.context:
      self.context.term()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()

  def __del__(self):
    self.close()
