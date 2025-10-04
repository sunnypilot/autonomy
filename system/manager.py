import time
import multiprocessing
import importlib

multiprocessing.set_start_method('spawn', force=True)


def python_process_launcher(module_name):
  module = importlib.import_module(module_name)
  module.main()


class PythonProcess:
  def __init__(self, name, module):
    self.name = name
    self.module = module
    self.process = None

  def start(self):
    self.process = multiprocessing.Process(target=python_process_launcher, args=(self.module,))
    self.process.start()

  def is_alive(self):
    return self.process.is_alive() if self.process else False


processes = [
  PythonProcess("navigationd", "navigation.navigationd"),
]


def main():
  for process in processes:
    process.start()

  while True:
    alive = [process.name for process in processes if process.is_alive()]
    not_alive = [process.name for process in processes if not process.is_alive()]
    print(f"Alive: {alive}, Not alive: {not_alive}")
    time.sleep(1)

if __name__ == "__main__":
  main()
