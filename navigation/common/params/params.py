import os
import base64
import ctypes
import sys


class Params:
  def __init__(self):
    self.params_dir = os.path.expanduser('~/.sunnypilot/params')
    os.makedirs(self.params_dir, exist_ok=True)
    
    # Load the compiled library
    lib_ext = '.dylib' if sys.platform == 'darwin' else '.so'
    lib_path = os.path.join(os.path.dirname(__file__), 'libparams' + lib_ext)
    self.lib = ctypes.CDLL(lib_path)
    self.lib.get_default_param.argtypes = [ctypes.c_char_p]
    self.lib.get_default_param.restype = ctypes.c_char_p

  def get(self, key, encoding=None):
    file_path = os.path.join(self.params_dir, key)
    if os.path.exists(file_path):
      try:
        with open(file_path, 'r') as f:
          value = f.read().strip()
          if encoding == 'bytes':
            return base64.b64decode(value)
          elif encoding == 'utf8':
            return value
          else:
            return value
      except Exception:
        pass
    # Get default from compiled library
    default_value = self.lib.get_default_param(key.encode('utf-8'))
    if default_value:
      value = default_value.decode('utf-8')
      if encoding == 'bytes':
        return base64.b64decode(value)
      elif encoding == 'utf8':
        return value
      else:
        return value
    return None

  def get_int(self, key):
    value = self.get(key)
    if value is None:
      return 0
    try:
      return int(value)
    except ValueError:
      return 0

  def put(self, key, value):
    file_path = os.path.join(self.params_dir, key)
    try:
      with open(file_path, 'w') as f:
        if isinstance(value, bytes):
          f.write(base64.b64encode(value).decode('utf-8'))
        else:
          f.write(str(value))
    except Exception:
      pass

  def get_mapbox_token(self):
    if os.environ.get('CI') == 'true':
      return os.environ.get('MAPBOX_TOKEN_CI', '')
    return self.get('MapboxToken') or ''
