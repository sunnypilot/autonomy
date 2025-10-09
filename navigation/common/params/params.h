#pragma once

#include <unordered_map>
#include <string>
#include <queue>
#include <future>
#include <utility>

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
  // default keys
  {"MapboxToken", {ParamKeyType::STRING, ""}},
  {"IsMetric", {ParamKeyType::BOOL, "0"}},
  {"MapboxSettings", {ParamKeyType::JSON, "{}"}},
  {"MapboxRoute", {ParamKeyType::STRING, ""}},


  // CI test keys
  {"key", {ParamKeyType::STRING, ""}},
  {"bool_key", {ParamKeyType::BOOL, "1"}},
  {"int_key", {ParamKeyType::INT, "42"}},
  {"float_key", {ParamKeyType::FLOAT, "3.14"}},
  {"list_key", {ParamKeyType::JSON, "[1, 2, 3]"}},
  {"json_key", {ParamKeyType::JSON, "{}"}},
  {"bytes_key", {ParamKeyType::BYTES}},
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
  void putNonBlocking(const std::string &key, const std::string &val);

private:
  std::string params_path;

  std::string getParamPath(const std::string &key = "") const {
    return params_path + (key.empty() ? "" : "/" + key);
  }

  void asyncWriteThread();
  int writeParam(const std::string &key, const std::string &value);
  std::queue<std::pair<std::string, std::string>> queue_;
  std::future<void> future_;
};
