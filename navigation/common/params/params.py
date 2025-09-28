import os
import json
import base64
import ctypes
import platform


class Params:
  def __init__(self):
    self.storage_file = os.path.join(os.path.dirname(__file__), 'params.json')

    lib_name = 'libmapbox_token.dylib' if platform.system() == 'Darwin' else 'libmapbox_token.so'
    lib_path = os.path.join(os.path.dirname(__file__), lib_name)
    self.lib = ctypes.CDLL(lib_path)
    self.lib.decrypt_mapbox_data.argtypes = [ctypes.c_char_p, ctypes.c_int]
    self.lib.decrypt_mapbox_data.restype = ctypes.c_char_p
    for func_name in ['get_mapbox_token', 'get_encrypted_mapbox_token']:
      getattr(self.lib, func_name).argtypes = []
      getattr(self.lib, func_name).restype = ctypes.c_char_p
    
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
    if isinstance(value, bytes):
      self.data[key] = base64.b64encode(value).decode('utf-8')
    else:
      self.data[key] = value
    self.save()

  def get_mapbox_token(self):
    result_ptr = self.lib.get_mapbox_token()
    return result_ptr.decode('utf-8')
