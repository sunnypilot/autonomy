import onnx

from driving_model_scripts.validate_model import ValidateModel


class TestValidateModel:
  def setup_method(self):
    self.validate_model = ValidateModel()
    self.test_model: str = "driving_model_scripts/tests/debug/model1/driving_policy.onnx"
    self.broken_model: str = "driving_model_scripts/tests/debug/broken_model/driving_policy.onnx"
    self.no_weight_model: str = "driving_model_scripts/tests/debug/broken_model/no_weights.onnx"

  def test_check_model(self):
    assert self.validate_model._check_model(self.test_model)
    # test nonexistent model
    assert not self.validate_model._check_model("driving_policy.onnx")
    # test broken model of 10k loc reduced from 77k loc
    assert not self.validate_model._check_model(self.broken_model)

  def test_analyze_weights(self):
    self.validate_model.target_model = onnx.load(self.test_model)
    assert self.validate_model._analyze_weights()
    self.validate_model.target_model = onnx.load(self.no_weight_model)
    assert not self.validate_model._analyze_weights()

  def test_analyze_shapes(self):
    self.validate_model.target_model = onnx.load(self.test_model)
    assert self.validate_model._analyze_shapes()
    self.validate_model.target_model = onnx.load(self.no_weight_model)
    assert self.validate_model._analyze_shapes()  # This model has no weights, but input/output proto fields are valid

  def test_inference_session(self):
    assert self.validate_model._inference_session(self.test_model)
    # These models WILL fail inference method as it runs the model in an onnxruntime session using CPU
    assert not self.validate_model._inference_session(self.broken_model)
    assert not self.validate_model._inference_session(self.no_weight_model)

  def test_validate_model_full_method(self):
    assert self.validate_model.validate_target_model(self.test_model)
    assert not self.validate_model.validate_target_model(self.broken_model)
    assert not self.validate_model.validate_target_model(self.no_weight_model)
