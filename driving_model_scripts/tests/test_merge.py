import copy
import os
import onnx
import tempfile

from driving_model_scripts.merge import MergePolicyModel


class TestMerge:
  def setup_method(self):
    self.model_1: str = "driving_model_scripts/tests/debug/model1/driving_policy.onnx"
    self.model_2: str = "driving_model_scripts/tests/debug/model2/driving_policy.onnx"
    self.model1 = onnx.load(self.model_1)
    self.model2 = onnx.load(self.model_2)
    self.merge = MergePolicyModel(self.model_1, self.model_2)
    self.temp_path = tempfile.NamedTemporaryFile(suffix='.onnx', delete=False)
    self.temp_model = copy.deepcopy(self.model2)

  def teardown_method(self):
    os.remove(self.temp_path.name)

  def test_extract_checkpoint_info(self):
    checkpoint1, checkpoint2 = self.merge._extract_checkpoint_info()
    assert checkpoint1 != "" and checkpoint1 is not None
    assert checkpoint2 != "" and checkpoint2 is not None

  def test_merge_head_components(self):
    params1 = {init.name: init for init in self.model1.graph.initializer}
    params2 = {init.name: init for init in self.model2.graph.initializer}
    keys1 = set(params1.keys())
    keys2 = set(params2.keys())
    common_keys = keys1.intersection(keys2)
    head_prefixes = ['policy_head', 'desire_layer']
    merged_model = self.merge._merge_head_components(common_keys, params1, params2, head_prefixes)
    merged_names = {init.name for init in merged_model.graph.initializer}
    assert keys1.issubset(merged_names)

  def test_update_checkpoint(self):
    checkpoint1_info, checkpoint2_info = self.merge._extract_checkpoint_info()
    self.merge._update_checkpoint(self.temp_model, 0.5, checkpoint1_info, checkpoint2_info)
    assert any(prop.key == 'model_checkpoint' and 'merged' in prop.value for prop in self.temp_model.metadata_props)

  def test_merge_model_weights(self):
    self.merge.merge_model_weights(self.temp_path.name)
    assert os.path.exists(self.temp_path.name)
    assert os.path.getsize(self.temp_path.name) > 13_500_000

    merged_model = onnx.load(self.temp_path.name)
    merged_model_names = {init.name for init in merged_model.graph.initializer}
    model1_names = {init.name for init in self.model1.graph.initializer}
    model2_names = {init.name for init in self.model2.graph.initializer}
    head_prefixes = ['policy_head', 'desire_layer']
    heads_from_model2 = {name for name in model2_names if any(name.startswith(p) for p in head_prefixes)}

    assert model1_names.issubset(merged_model_names)
    assert heads_from_model2.issubset(merged_model_names)
    assert isinstance(merged_model, onnx.ModelProto)
