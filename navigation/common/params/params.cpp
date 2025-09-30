#include "params.h"

#include <sys/file.h>
#include <unistd.h>
#include <fcntl.h>
#include <cstdlib>
#include <sys/stat.h>
#include <stdexcept>
#include <chrono>
#include <cassert>
#include <fstream>
#include <iterator>
#include <iostream>

extern "C" {
const char* get_default_param(const char* key) {
  auto it = KEYS.find(std::string(key));
  if (it != KEYS.end()) {
    return it->second.default_value.c_str();
  }
  return nullptr;
}
}

namespace {
int fsync_dir(const std::string &path) {
  int result = -1;
  int fd = open(path.c_str(), O_RDONLY);
  if (fd >= 0) {
    result = fsync(fd);
    close(fd);
  }
  return result;
}

bool create_params_path(const std::string &params_path) {
  // Make sure params path exists
  if (mkdir(params_path.c_str(), 0775) != 0 && errno != EEXIST) {
    return false;
  }
  return true;
}

std::string ensure_params_path(const std::string &path = {}) {
  std::string params_path = path.empty() ? std::string(getenv("HOME")) + "/.sunnypilot/params" : path;
  if (!create_params_path(params_path)) {
    throw std::runtime_error("Failed to ensure params path");
  }
  return params_path;
}

class FileLock {
public:
  FileLock(const std::string &fn) {
    fd_ = open(fn.c_str(), O_CREAT, 0775);
    if (fd_ < 0 || flock(fd_, LOCK_EX) < 0) {
      std::cerr << "Failed to lock file " << fn << ", errno=" << errno << std::endl;
    }
  }
  ~FileLock() { if (fd_ >= 0) close(fd_); }

private:
  int fd_ = -1;
};
}

Params::Params(const std::string &path) {
  params_path = ensure_params_path(path);
}

Params::~Params() {
  // wait for async writes to finish before destruction
  if (future_.valid()) {
    future_.wait();
  }
  assert(queue_.empty());
}

bool Params::checkKey(const std::string &key) {
  return KEYS.find(key) != KEYS.end();
}

ParamKeyType Params::getKeyType(const std::string &key) {
  return KEYS.at(key).type;
}

std::string Params::getKeyDefaultValue(const std::string &key) {
  return KEYS.at(key).default_value;
}

int Params::put(const char* key, const char* value, size_t value_size) {
  return writeParam(std::string(key), std::string(value, value_size));
}

int Params::writeParam(const std::string &key, const std::string &value) {
  std::string tmp_path = params_path + "/.tmp_value_XXXXXX";
  int tmp_fd = mkstemp((char*)tmp_path.c_str());
  if (tmp_fd < 0) return -1;

  int result = -1;
  do {
    ssize_t bytes_written = write(tmp_fd, value.c_str(), value.size());
    if (bytes_written < 0 || (size_t)bytes_written != value.size()) {
      result = -20;
      break;
    }

    if ((result = fsync(tmp_fd)) < 0) break;

    FileLock file_lock(params_path + "/.lock");

    if ((result = rename(tmp_path.c_str(), getParamPath(key).c_str())) < 0) break;

    result = fsync_dir(getParamPath());
  } while (false);

  close(tmp_fd);
  if (result != 0) {
    unlink(tmp_path.c_str());
  }
  return result;
}

void Params::putNonBlocking(const std::string &key, const std::string &val) {
  queue_.push(std::make_pair(key, val));
  // start thread on demand
  if (!future_.valid() || future_.wait_for(std::chrono::milliseconds(0)) == std::future_status::ready) {
    future_ = std::async(std::launch::async, &Params::asyncWriteThread, this);
  }
}

void Params::asyncWriteThread() {
  while (!queue_.empty()) {
    auto item = queue_.front();
    queue_.pop();
    writeParam(item.first, item.second);
  }
}

std::string Params::get(const std::string &key) {
  std::ifstream file(getParamPath(key));
  if (!file) return "";
  return std::string((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
}
