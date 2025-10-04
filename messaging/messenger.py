import threading
import time
import logging
import asyncio
from pathlib import Path
from dataclasses import dataclass

import capnp
import yaml
import zmq
import zmq.asyncio as zmq_async


schema = capnp.load("messaging/autonomy.capnp")

# This big chonk needs to be reviewed piecewise.

@dataclass
class CachedMessage:
  msg: object = None
  capnp_reader: object = None


def load_registry(path="messaging/services.yaml") -> dict[str, dict]:
  with Path(path).open() as file:
    config = yaml.safe_load(file)

  registry: dict[str, dict] = {}

  for service in config["services"]:
    schema_name = service["schema"]
    try:
      schema_type = getattr(schema, schema_name)
    except AttributeError:
      raise ValueError(f"Schema '{schema_name}' not found in capnp for service '{service['name']}'")

    registry[service["name"]] = {
      "port": service["port"],
      "rate_hz": service["rate_hz"],
      "schema_type": schema_type,
    }
  return registry


class PubMaster:
  """Publishes messages to ZMQ publisher socket."""
  def __init__(self, name, registry_path="messaging/services.yaml") -> None:
    self.registry: dict[str, dict] = load_registry(registry_path)
    self.port: int = self.registry[name]["port"]
    self.rate_hz: float = self.registry[name]["rate_hz"]  # Used by clients to determine publish rate (1.0/rate_hz)

    self.context = zmq.Context()
    self.socket = self.context.socket(zmq.PUB)
    self.socket.bind(f"tcp://127.0.0.1:{self.port}")

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

    logging.warning(f"SubMaster initializing with services: {service_names}")

    self.services: dict[str, dict] = {}
    self._lock = threading.Lock()  # Lock for thread safety
    self.context = zmq_async.Context()  # Use asyncio-compatible context
    self._running: bool = True  # Control flag for async loops
    self._thread: threading.Thread | None = None  # Thread for running async loops

    for name in service_names:  # Initialize each service
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
        "rate_hz": svc["rate_hz"],
        "last_timeout_logged": None,
        "cached": CachedMessage(),
      }
    self._thread = threading.Thread(target=self._run_all_loops, daemon=True, name="SubMaster-all")
    self._thread.start()

  def _update_cached_msg(self, name, data=None):
    """Update the cached message for a service."""
    cached = self.services[name]["cached"]
    if cached.capnp_reader is not None:  # clean up previous reader
      cached.capnp_reader.__exit__(None, None, None)
    if data is not None:
      cached.capnp_reader = self.services[name]["schema_type"].from_bytes(data)  # deserialize message
      cached.msg = cached.capnp_reader.__enter__()
    else:  # clear cached message
      cached.msg = None
      cached.capnp_reader = None

  async def _async_loop(self, name):
    """Asynchronously receive messages for a service."""
    socket = self.services[name]["socket"]
    while self._running:
      try:
        data = await asyncio.wait_for(socket.recv(), timeout=0.1)
        with self._lock:
          self.services[name]["last_data"] = data
          self.services[name]["received_at"] = time.monotonic()
          self._update_cached_msg(name, data)
      except asyncio.TimeoutError:
        continue
      except Exception as e:
        logging.error(f"Error receiving message for {name}: {e}", exc_info=True)

  def _run_all_loops(self):
    """Run all async loops concurrently in a single event loop."""
    asyncio.run(self._run_all_async_loops())

  async def _run_all_async_loops(self):
    await asyncio.gather(*[self._async_loop(name) for name in self.services])

  def __getitem__(self, name):
    with self._lock:
      if name not in self.services:
        raise KeyError(f"Service {name} not subscribed")
      data = self.services[name]["last_data"]
      received_at = self.services[name]["received_at"]
      timeout = self.services[name]["timeout_seconds"]
      
      if data is not None and received_at is not None:
        age = time.monotonic() - received_at
        if age > timeout:  # log warning every second if message is stale
          if (last_logged := self.services[name]["last_timeout_logged"]) is None or time.monotonic() - last_logged > 1.0:
            logging.warning(f"Message for service {name} timed out (age: {age:.2f}s > {timeout:.2f}s)")
            self.services[name]["last_timeout_logged"] = time.monotonic()
          self._update_cached_msg(name)
          return None
      
      if data:
        return self.services[name]["cached"].msg
      return None

  @property
  def alive(self):
    """Return a dict of service name to a bool indicating if the last message was received within timeout"""
    with self._lock:
      return {
        name: (
          self.services[name]["received_at"] is not None and
          (time.monotonic() - self.services[name]["received_at"]) < (self.services[name]["timeout_seconds"])
        )
        for name in self.services
      }

  def close(self):
    """Shutdown the subscriber and clean up."""
    logging.warning("SubMaster shutting down")
    self._running = False
    for name in self.services:
      self._update_cached_msg(name)
    if self._thread:
      self._thread.join(timeout=1.0)
    for service in self.services.values():
      service['socket'].close()
    self.context.term()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()

  def __del__(self):
    self.close()
