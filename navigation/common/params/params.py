import os
import json
import base64


class Params:
  def __init__(self):
    self.storage_file = os.path.join(os.path.dirname(__file__), 'params.json')
    self.data = {}
    self.load()

  def load(self):
    if os.path.exists(self.storage_file):
     try:
      with open(self.storage_file, 'r') as file:
       self.data = json.load(file)
     except Exception:
      self.data = {}

  def save(self):
    try:
     with open(self.storage_file, 'w') as file:
      json.dump(self.data, file, indent=2)
    except Exception:
      pass

  def get(self, key, encoding=None):
    value = self.data.get(key)
    if value is None:
      return None
    if isinstance(value, str) and encoding == 'bytes':
      return base64.b64decode(value)
    if encoding == 'utf8':
      if key == "MapboxToken":
        return base64.b64decode(value).decode('utf-8')
      return value
    return value

  def get_int(self, key):
    value = self.data.get(key)
    if value is None:
      return 0
    try:
      return int(value)
    except ValueError:
      return 0

  def put(self, key, value):
    if key == "MapboxToken" and isinstance(value, str):
      value = value.encode('utf-8')
    if isinstance(value, bytes):
      self.data[key] = base64.b64encode(value).decode('utf-8')
    else:
      self.data[key] = value
    self.save()
