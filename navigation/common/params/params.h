#ifndef PARAMS_H
#define PARAMS_H

#include <unordered_map>
#include <string>

const std::unordered_map<std::string, std::string> DEFAULT_PARAMS = {
  {"MapboxSettings", ""},
  {"IsMetric", "false"},
  {"MapboxToken", ""}
};

#endif
