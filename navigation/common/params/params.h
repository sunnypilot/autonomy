#pragma once

#include <unordered_map>
#include <string>

enum class ParamKeyType {
  STRING = 0,
  BOOL = 1,
  INT = 2,
  FLOAT = 3,
  JSON = 4,
  BYTES = 5,
};

struct KeyInfo {
  ParamKeyType type;
  std::string default_value;
};

const std::unordered_map<std::string, KeyInfo> KEYS = {
  {"MapboxToken", {ParamKeyType::STRING, ""}},
  {"IsMetric", {ParamKeyType::BOOL, "0"}},
  {"MapboxSettings", {ParamKeyType::BYTES}},
};

class Params {
public:
  Params(const std::string &path = "");
  ~Params();

  bool checkKey(const std::string &key);
  ParamKeyType getKeyType(const std::string &key);
  std::string getKeyDefaultValue(const std::string &key);
  std::string getParamsPath() const { return params_path; }

  int put(const char* key, const char* value, size_t value_size);
  std::string get(const std::string &key);

private:
  std::string params_path;

  std::string getParamPath(const std::string &key = "") const {
    return params_path + (key.empty() ? "" : "/" + key);
  }
};
