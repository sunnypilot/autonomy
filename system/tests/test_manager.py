from system.manager import processes


class TestManagerIntegration:
  def teardown_method(self):
    for process in processes:
      if process.process and process.process.is_alive():
        process.process.terminate()
        process.process.join()

  def test_python_process_start_and_alive(self):
    for process in processes:
      process.start()
      assert process.is_alive()

      process.process.terminate()
      process.process.join()
      assert not process.is_alive()

  def test_python_process_not_started(self):
    for process in processes:
      assert not process.is_alive()

  def test_manager_processes_list(self):
    assert processes[0].name == "navigationd"
    assert processes[0].module == "navigation.navigationd"

  def test_process_termination(self):
    for process in processes:
      process.start()
      assert process.is_alive()

      process.process.terminate()
      process.process.join()
      assert not process.is_alive()
