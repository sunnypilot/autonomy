# distutils: language = c++
import os
import base64
import json
from libcpp.string cimport string
from libcpp cimport bool as cpp_bool

cdef extern from "params.h":
  cpdef enum class ParamKeyType:
    STRING = 0
    BOOL = 1
    INT = 2
    FLOAT = 3
    JSON = 4
    BYTES = 5

  cdef cppclass CParams "Params":
    CParams(string path) except +
    cpp_bool checkKey(string key)
    ParamKeyType getKeyType(string key)
    string getKeyDefaultValue(string key)
    string getParamsPath()
    int put(const char* key, const char* value, size_t value_size)
    string get(string key)
    void putNonBlocking(string key, string val) nogil

class UnknownKeyName(Exception):
  pass

cdef class Params:
  cdef CParams* c_params

  def __cinit__(self, path=""):
    self.c_params = new CParams(path.encode('utf-8'))

  def __dealloc__(self):
    del self.c_params

  @property
  def params_dir(self):
    return self.c_params.getParamsPath().decode('utf-8')

  def check_key(self, key):
    return self.c_params.checkKey(key.encode('utf-8'))

  def get_key_type(self, key):
    return self.c_params.getKeyType(key.encode('utf-8'))

  def _convert_from_string(self, value, key_type):
    if key_type == ParamKeyType.STRING:
      return value
    elif key_type == ParamKeyType.BOOL:
      return value == "1"
    elif key_type == ParamKeyType.INT:
      return int(value)
    elif key_type == ParamKeyType.FLOAT:
      return float(value)
    elif key_type == ParamKeyType.JSON:
      return json.loads(value)
    elif key_type == ParamKeyType.BYTES:
      return value.encode()
    else:
      return value

  def _convert_to_string(self, value, key_type):
    if key_type == ParamKeyType.STRING:
      return str(value)
    elif key_type == ParamKeyType.BOOL:
      return "1" if value else "0"
    elif key_type == ParamKeyType.INT:
      return str(int(value))
    elif key_type == ParamKeyType.FLOAT:
      return str(float(value))
    elif key_type == ParamKeyType.JSON:
      return json.dumps(value)
    elif key_type == ParamKeyType.BYTES:
      return value.decode() if isinstance(value, bytes) else str(value)
    else:
      return str(value)

  def _prepare_value_for_put(self, key, value):
    if self.check_key(key):
      key_type = self.get_key_type(key)
      str_value = self._convert_to_string(value, key_type)
    else:
      if isinstance(value, bytes):
        str_value = base64.b64encode(value).decode('utf-8')
      else:
        str_value = str(value)
    return str_value.encode('utf-8')

  def get(self, key, encoding=None, return_default=True):
    if key == 'MapboxToken' and os.environ.get('CI') == 'true':
      return os.environ.get('MAPBOX_TOKEN_CI', '')

    cdef string c_key = key.encode('utf-8')
    cdef string value = self.c_params.get(c_key)
    cdef string default_value
    if value.empty() and return_default:
      # Get default value for known keys
      if self.check_key(key):
        default_value = self.c_params.getKeyDefaultValue(c_key)
        decoded = default_value.decode('utf-8')
        key_type = self.get_key_type(key)
        return self._convert_from_string(decoded, key_type)
      else:
        return None

    decoded = value.decode('utf-8')
    if encoding == 'bytes':
      decoded = base64.b64decode(decoded)
    elif encoding == 'utf8':
      pass

    if self.check_key(key):
      key_type = self.get_key_type(key)
      return self._convert_from_string(decoded, key_type)
    else:
      return decoded

  def put(self, key, value):
    cdef string c_key = key.encode('utf-8')
    cdef string c_value = self._prepare_value_for_put(key, value)
    return self.c_params.put(c_key.c_str(), c_value.c_str(), c_value.size())

  def get_int(self, key):
    try:
      val = self.get(key)
      return int(val) if val is not None else 0
    except (ValueError, TypeError):
      return 0

  def put_nonblocking(self, key, value):
    cdef string k = key.encode('utf-8')
    cdef string value_bytes = self._prepare_value_for_put(key, value)
    with nogil:
      self.c_params.putNonBlocking(k, value_bytes)
