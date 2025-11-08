import logging
import numpy as np
import onnx
import onnxruntime as ort

from google.protobuf.message import DecodeError
from onnx import numpy_helper
from typing import cast


class ValidateModel:
  def __init__(self):
    self.target_model = None
    self.issues: list = []

  def _check_model(self, model) -> bool:
    try:
      onnx.checker.check_model(model, full_check=True)
      return True
    except Exception as e:
      logging.error(f"ONNX validation failed: {e}")
      return False

  def _analyze_weights(self) -> bool:
    weight_stats = {}
    if not self.target_model.graph.initializer:
      return False

    for init in self.target_model.graph.initializer:
      weights = numpy_helper.to_array(init)
      weight_stats[init.name] = {
        'shape': weights.shape,
        'dtype': weights.dtype,
        'mean': float(np.mean(weights)),
        'std': float(np.std(weights)),
        'min': float(np.min(weights)),
        'max': float(np.max(weights)),
        'has_nan': bool(np.isnan(weights).any()),
        'has_inf': bool(np.isinf(weights).any()),
      }

    # Check for problematic weights
    problematic_weights = []
    for name, stats in weight_stats.items():
      if stats['has_nan']:
        problematic_weights.append(f"{name}: Contains NaN values")
      if stats['has_inf']:
        problematic_weights.append(f"{name}: Contains Inf values")
      if stats['std'] == 0 and all(sub not in name.lower() for sub in ['bias', 'pad']):
        problematic_weights.append(f"{name}: Zero variance (might be frozen)")
      if abs(cast(float, stats['mean'])) > 10:
        problematic_weights.append(f"{name}: Large mean value ({stats['mean']:.3f})")

    if problematic_weights:
      logging.warning("Possible weight issues found:")
      for issue in problematic_weights[:15]:
        self.issues.append(f"-{issue}")
      return False
    return True

  def _analyze_shapes(self) -> bool:
    node_inputs = set()
    node_outputs = set()

    for node in self.target_model.graph.node:
      node_inputs.update(node.input)
      node_outputs.update(node.output)

    initializer_names = {init.name for init in self.target_model.graph.initializer}
    input_names = {inp.name for inp in self.target_model.graph.input}
    output_names = {out.name for out in self.target_model.graph.output}

    # Check for dangling references
    missing_inputs = node_inputs - (node_outputs | initializer_names | input_names)
    unused_outputs = (node_outputs | initializer_names) - (node_inputs | output_names)

    if missing_inputs:
      self.issues.append(f"Missing inputs: {list(missing_inputs)[:10]}")

    if unused_outputs:
      self.issues.append(f"Unused outputs: {len(unused_outputs)}")
    return not (missing_inputs or unused_outputs)

  def _inference_session(self, model_path) -> bool:
    try:
      session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])

      # Get expected input shapes
      input_shapes = []
      for inp in session.get_inputs():
        shape = [dim if isinstance(dim, int) and dim > 0 else 1 for dim in inp.shape]
        input_shapes.append((inp.name, shape, inp.type))

      dummy_inputs = {}
      for name, shape, dtype in input_shapes:
        if dtype == 'tensor(float)':
          dummy_inputs[name] = np.random.randn(*shape).astype(np.float32)
        elif dtype == 'tensor(float16)':
          dummy_inputs[name] = np.random.randn(*shape).astype(np.float16)
        elif dtype == 'tensor(int64)':
          dummy_inputs[name] = np.random.randint(0, 10, shape).astype(np.int64)
        else:
          self.issues.append(f"Unknown input type: {dtype}")
          continue

      if dummy_inputs:
        inference = session.run(None, dummy_inputs)
        if inference is None:
          return False
      return True
    except Exception as e:
      logging.error(f"Inference test failed: {str(e)[:100]}")
      return False

  def validate_target_model(self, model_path) -> bool:
    try:
      self.target_model = onnx.load(model_path)
      if not self._check_model(self.target_model):
        return False
    except DecodeError:
      return False

    results: list[bool] = []
    results.append(self._analyze_weights())
    results.append(self._analyze_shapes())
    results.append(self._inference_session(model_path))
    success = all(results)

    for issue in self.issues:
      logging.error(issue)

    return success
