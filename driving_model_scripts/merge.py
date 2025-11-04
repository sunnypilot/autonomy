import logging
import os
import onnx
from onnx import numpy_helper

from driving_model_scripts.validate_model import ValidateModel


class MergePolicyModel:
  def __init__(self, model_path1, model_path2):
    self.validate_model = ValidateModel()
    self.model1 = onnx.load(model_path1)
    self.model2 = onnx.load(model_path2)

  def _extract_checkpoint_info(self) -> tuple:
    checkpoint1_info = ""
    checkpoint2_info = ""

    for prop in self.model1.metadata_props:
      if prop.key == "model_checkpoint":
        checkpoint1_info = prop.value
        break

    for prop in self.model2.metadata_props:
      if prop.key == "model_checkpoint":
        checkpoint2_info = prop.value
        break

    return checkpoint1_info, checkpoint2_info

  def _merge_head_components(self, common_keys, params1, params2, head_prefixes):
    keys1 = set(params1.keys())
    keys2 = set(params2.keys())
    model2_only_keys = keys2 - keys1
    merged_model = self.model1

    if not head_prefixes:
      return merged_model

    if not common_keys:
      logging.warning("No common keys found!")

    common_head_weights = [name for name in common_keys if any(name.startswith(prefix) for prefix in head_prefixes)]

    initializers_to_remove = [init.name for init in merged_model.graph.initializer if any(init.name.startswith(prefix) for prefix in head_prefixes)]
    new_initializers = [init for init in merged_model.graph.initializer if init.name not in initializers_to_remove]
    merged_model.graph.ClearField('initializer')
    merged_model.graph.initializer.extend(new_initializers)

    # Add new head initializers from model2 to merged_model
    for name in model2_only_keys:
      if any(name.startswith(prefix) for prefix in head_prefixes):
        new_initializer = params2[name]
        merged_model.graph.initializer.extend([new_initializer])

    # Add common head weights from model2 (replacing model1's head weights)
    for name in common_head_weights:
      new_initializer = params2[name]
      merged_model.graph.initializer.extend([new_initializer])

    # Remove old head nodes
    nodes_to_remove_names = [node.name for node in merged_model.graph.node if any(node.name.startswith(prefix) for prefix in head_prefixes)]
    new_nodes = [node for node in merged_model.graph.node if node.name not in nodes_to_remove_names]

    # Add new head nodes from model2
    for node in self.model2.graph.node:
      if any(node.name.startswith(prefix) for prefix in head_prefixes):
        new_nodes.append(node)

    # Update the graph nodes
    merged_model.graph.ClearField('node')
    merged_model.graph.node.extend(new_nodes)

    # Update graph outputs
    new_outputs = []
    for output in merged_model.graph.output:
      is_head_output = any(output.name.startswith(prefix) for prefix in head_prefixes)
      if is_head_output:
        for model2_output in self.model2.graph.output:
          if any(model2_output.name.startswith(prefix) for prefix in head_prefixes):
            new_outputs.append(model2_output)
            break
      else:
        new_outputs.append(output)

    merged_model.graph.ClearField('output')
    merged_model.graph.output.extend(new_outputs)
    return merged_model

  def _merge_common_weights(self, common_keys, params1, params2, head_prefixes, merged_model, weight) -> None:
    for name in common_keys:
      if any(name.startswith(prefix) for prefix in head_prefixes):
        continue

      w1 = numpy_helper.to_array(params1[name])
      w2 = numpy_helper.to_array(params2[name])

      if w1.shape != w2.shape:
        continue

      # Calculate the weighted average and update tensors
      merged_w = (weight * w1) + ((1 - weight) * w2)
      new_tensor = numpy_helper.from_array(merged_w, name=name)

      for index, tensor in enumerate(merged_model.graph.initializer):
        if tensor.name == name:
          merged_model.graph.initializer[index].CopyFrom(new_tensor)
          break

  def _update_checkpoint(self, merged_model, weight, checkpoint1_info, checkpoint2_info) -> None:
    new_checkpoint_info = f"merged with {weight}w from (model1: '{checkpoint1_info}') and (model2: '{checkpoint2_info}')"
    existing_metadata = {}

    for prop in merged_model.metadata_props:
      if prop.key != "model_checkpoint":
        existing_metadata[prop.key] = prop.value
    merged_model.ClearField('metadata_props')

    for key, value in existing_metadata.items():
      metadata_prop = merged_model.metadata_props.add()
      metadata_prop.key = key
      metadata_prop.value = value

    checkpoint_prop = merged_model.metadata_props.add()
    checkpoint_prop.key = "model_checkpoint"
    checkpoint_prop.value = new_checkpoint_info

  def _save_and_validate_model(self, merged_model, output_path) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    onnx.save(merged_model, output_path)
    validation_passed = self.validate_model.validate_target_model(output_path)

    if validation_passed:
      print("\nSuccessfully merged and validated models")
      print(f"Saved to: '{output_path}'")
    else:
      print("\nModel saved but has validation issues")
      print(f"Check: '{output_path}'")

  def _check_architecture(self) -> None:
    if len(self.model1.graph.input) != len(self.model2.graph.input):
      raise ValueError("incompatible input count")
    elif len(self.model1.graph.output) != len(self.model2.graph.output):
      raise ValueError("Not same architecture between the two models!")

    for input1, input2 in zip(self.model1.graph.input, self.model2.graph.input):
      if input1.type.HasField('tensor_type') and input2.type.HasField('tensor_type'):
        if len(input1.type.tensor_type.shape.dim) == len(input2.type.tensor_type.shape.dim):
          for dim1, dim2 in zip(input1.type.tensor_type.shape.dim, input2.type.tensor_type.shape.dim):
            if dim1.HasField('dim_value') and dim2.HasField('dim_value'):
              if dim1.dim_value != dim2.dim_value:
                raise ValueError("input shape mismatch!")

    for output1, output2 in zip(self.model1.graph.output, self.model2.graph.output):
      if output1.type.HasField('tensor_type') and output2.type.HasField('tensor_type'):
        if len(output1.type.tensor_type.shape.dim) == len(output2.type.tensor_type.shape.dim):
          for out_dim1, out_dim2 in zip(output1.type.tensor_type.shape.dim, output2.type.tensor_type.shape.dim):
            if out_dim1.HasField('dim_value') and out_dim2.HasField('dim_value'):
              if out_dim1.dim_value != out_dim2.dim_value:
                raise ValueError("output shape mismatch!")

  def merge_model_weights(self, output_path, weight=0.5) -> None:
    checkpoint1_info, checkpoint2_info = self._extract_checkpoint_info()
    params1 = {init.name: init for init in self.model1.graph.initializer}
    params2 = {init.name: init for init in self.model2.graph.initializer}
    keys1 = set(params1.keys())
    keys2 = set(params2.keys())
    common_keys = keys1.intersection(keys2)
    head_prefixes = ['policy_head', 'desire_layer']

    self._check_architecture()
    merged_model = self._merge_head_components(common_keys, params1, params2, head_prefixes)

    self._merge_common_weights(common_keys, params1, params2, head_prefixes, merged_model, weight)
    self._update_checkpoint(merged_model, weight, checkpoint1_info, checkpoint2_info)
    self._save_and_validate_model(merged_model, output_path)


if __name__ == "__main__":
  base_path = "driving_model_scripts/model_path"
  model1_path = f"{base_path}/model1/driving_policy.onnx"
  model2_path = f"{base_path}/model2/driving_policy.onnx"
  model_merger = MergePolicyModel(model1_path, model2_path)
  model_merger.merge_model_weights(f"{base_path}/driving_policy_merged.onnx")
