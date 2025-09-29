import os
import base64
import ctypes
import sys
from pathlib import Path


class Params:
  def __init__(self):
    self.params_dir = Path(os.path.expanduser('~/.sunnypilot/params'))
    self.params_dir.mkdir(parents=True, exist_ok=True)
    
    # Load the compiled library
    lib_ext = '.dylib' if sys.platform == 'darwin' else '.so'
    lib_path = os.path.join(os.path.dirname(__file__), 'libparams' + lib_ext)
    self.lib = ctypes.CDLL(lib_path)
    self.lib.get_default_param.argtypes = [ctypes.c_char_p]
    self.lib.get_default_param.restype = ctypes.c_char_p

  def __decode_value(self, value, encoding):
    if encoding == 'bytes':
      return base64.b64decode(value)
    elif encoding == 'utf8':
      return value
    else:
      return value

  def _get_default(self, key, encoding):
    default_value = self.lib.get_default_param(key.encode('utf-8'))
    if default_value:
      value = default_value.decode('utf-8')
      decoded = self.__decode_value(value, encoding)
    else:
      decoded = None
    if key == 'MapboxToken' and decoded is None:
      return ''
    return decoded

  def get(self, key, encoding=None, return_default=True):
    if key == 'MapboxToken':
      if os.environ.get('CI') == 'true':
        return os.environ.get('MAPBOX_TOKEN_CI', '')

    if return_default:
      file_path = self.params_dir / key
      if file_path.exists():
        try:
          value = file_path.read_text().strip()
          decoded = self.__decode_value(value, encoding)
          if key == 'MapboxToken' and decoded is None:
            return ''
          return decoded
        except (OSError, ValueError):
          pass

    return self._get_default(key, encoding)

  def get_int(self, key):
    value = self.get(key)
    if value is None:
      return 0
    try:
      return int(value)
    except ValueError:
      return 0

  def put(self, key, value):
    file_path = self.params_dir / key
    with file_path.open('w') as f:
      if isinstance(value, bytes):
        f.write(base64.b64encode(value).decode('utf-8'))
      else:
        f.write(str(value))
