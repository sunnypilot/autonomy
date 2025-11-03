import os
import onnx
from onnx import numpy_helper

from driving_model_scripts.validate_model import ValidateModel


class MergePolicyModel:
  def __init__(self, model_path1, model_path2):
    self.validate_model = ValidateModel()
    self.model1 = onnx.load(model_path1)
    self.model2 = onnx.load(model_path2)

  def merge_model_weights(self, output_path, weight=0.5):
    # Extract checkpoint info
    checkpoint1_info = "N/A"
    for prop in self.model1.metadata_props:
      if prop.key == "model_checkpoint":
        checkpoint1_info = prop.value
        break

    checkpoint2_info = "N/A"
    for prop in self.model2.metadata_props:
      if prop.key == "model_checkpoint":
        checkpoint2_info = prop.value
        break

    params1 = {init.name: init for init in self.model1.graph.initializer}
    params2 = {init.name: init for init in self.model2.graph.initializer}

    keys1 = set(params1.keys())
    keys2 = set(params2.keys())
    common_keys = keys1.intersection(keys2)
    model2_only_keys = keys2 - keys1
    head_prefixes = ['policy_head', 'desire_layer']

    # Check for other possible head patterns
    all_weight_names = keys1.union(keys2)
    possible_head_patterns = set()
    for name in all_weight_names:
      if any(pattern in name.lower() for pattern in ['head', 'policy', 'desire', 'output']):
        possible_head_patterns.add(name.split('.')[0] if '.' in name else name.split('/')[0] if '/' in name else name)

    # Identify head weights in each model and create new merge
    common_head_weights = [name for name in common_keys if any(name.startswith(prefix) for prefix in head_prefixes)]
    merged_model = self.model1

    # Track changes for verification
    removed_initializers = []
    added_initializers = []
    merged_weights_count = 0

    initializers_to_remove = [init.name for init in merged_model.graph.initializer if any(init.name.startswith(prefix) for prefix in head_prefixes)]
    removed_initializers.extend(initializers_to_remove)
    new_initializers = [init for init in merged_model.graph.initializer if init.name not in initializers_to_remove]
    merged_model.graph.ClearField('initializer')
    merged_model.graph.initializer.extend(new_initializers)

    # Add new head initializers from model2 to merged_model
    for name in model2_only_keys:
      if any(name.startswith(prefix) for prefix in head_prefixes):
        new_initializer = params2[name]
        merged_model.graph.initializer.extend([new_initializer])
        added_initializers.append(name)

    # Add common head weights from model2 (replacing model1's head weights)
    for name in common_head_weights:
      new_initializer = params2[name]
      merged_model.graph.initializer.extend([new_initializer])
      added_initializers.append(name)

    # Remove old head nodes
    nodes_to_remove_names = [node.name for node in merged_model.graph.node if any(node.name.startswith(prefix) for prefix in head_prefixes)]
    new_nodes = [node for node in merged_model.graph.node if node.name not in nodes_to_remove_names]

    # Add new head nodes from model2
    added_nodes = []
    for node in self.model2.graph.node:
      if any(node.name.startswith(prefix) for prefix in head_prefixes):
        new_nodes.append(node)
        added_nodes.append(node.name)

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

      for i, tensor in enumerate(merged_model.graph.initializer):
        if tensor.name == name:
          merged_model.graph.initializer[i].CopyFrom(new_tensor)
          merged_weights_count += 1
          break

    # Create new checkpoint and add to graph
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

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    onnx.save(merged_model, output_path)
    validation_passed = self.validate_model.validate_target_model(output_path)

    if validation_passed:
      print("\nSuccessfully merged and validated models")
      print(f"Saved to: '{output_path}'")
    else:
      print("\nModel saved but has validation issues")
      print(f"Check: '{output_path}'")


if __name__ == "__main__":
  base_path = "driving_model_scripts/model_path"
  model1_path = f"{base_path}/model1/driving_policy.onnx"
  model2_path = f"{base_path}/model2/driving_policy.onnx"
  model_merger = MergePolicyModel(model1_path, model2_path)
  model_merger.merge_model_weights(f"{base_path}/driving_policy_merged.onnx")
