import time
from messaging.messenger import SubMaster

def main():
  sm = SubMaster()

  while True:
    for name in sm.services.keys():
      msg = sm[name]
      print(f"Service: {name}")
      if msg:
        print(f"[{name}] {msg}")
      else:
        print(f"No recent message for {name}")
    time.sleep(1.0)

if __name__ == "__main__":
  main()
