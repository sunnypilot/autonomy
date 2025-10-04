import time
import messaging.messenger as messenger


def main():
  sm = messenger.SubMaster()

  while True:
    for name in sm.services.keys():
      msg = sm[name]
      print(f"Service: {name}")
      if msg:
        print(f"[{name}] {msg}")
      else:
        print(f"No recent message for {name}")
    time.sleep(0.1)

if __name__ == "__main__":
  main()
