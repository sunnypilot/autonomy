#include "params.h"

#include <sys/file.h>
#include <unistd.h>
#include <fcntl.h>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <sys/stat.h>

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

bool create_params_path(const std::string &param_path) {
  // Make sure params path exists
  if (mkdir(param_path.c_str(), 0775) != 0 && errno != EEXIST) {
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
    fd_ = open(fn.c_str(), O_CREAT | O_RDWR, 0775);
    if (fd_ < 0 || flock(fd_, LOCK_EX) < 0) {
      // Error handling simplified
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
  std::string tmp_path = params_path + "/.tmp_value_XXXXXX";
  int tmp_fd = mkstemp((char*)tmp_path.c_str());
  if (tmp_fd < 0) return -1;

  int result = -1;
  do {
    ssize_t bytes_written = write(tmp_fd, value, value_size);
    if (bytes_written < 0 || (size_t)bytes_written != value_size) {
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

std::string Params::get(const std::string &key) {
  FILE *f = fopen(getParamPath(key).c_str(), "r");
  if (!f) return "";
  char buf[4096];
  size_t n = fread(buf, 1, sizeof(buf), f);
  fclose(f);
  return std::string(buf, n);
}
