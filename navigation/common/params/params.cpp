#include "params.h"

extern "C" {

const char* get_default_param(const char* key) {
  auto it = DEFAULT_PARAMS.find(std::string(key));
  if (it != DEFAULT_PARAMS.end()) {
    return it->second.c_str();
  }
  return nullptr;
}
}
