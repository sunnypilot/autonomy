import threading
import time
from navigation import navigationd


SERVICE_MAP = {
  "navigationd": navigationd.run,
}


def start_service(name):
  target = SERVICE_MAP[name]
  thread = threading.Thread(target=target, daemon=True)
  thread.start()
  return thread

def main():
  threads = []
  for name in SERVICE_MAP.keys():
    thread = start_service(name)
    threads.append((name, thread))

  while True:
    alive = []
    not_alive = []
    for name, thread in threads:
      if thread.is_alive():
        alive.append(name)
      else:
        not_alive.append(name)
    print(f"Alive: {alive}, Not alive: {not_alive}")
    time.sleep(1)

if __name__ == "__main__":
  main()
