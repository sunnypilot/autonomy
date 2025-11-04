# Driving Policy Model Merge Module

Welcome to the Driving Policy Model Merge Module by Sunnypilot Autonomy. This tool simplifies the process of merging two policy driving models with minimal effort.

## Overview

This script automates the merging of two driving policy models. It performs model validation, merging, and unit testing—all without requiring manual intervention.

## How It Works

1. Place your two models in the provided `model1/` and `model2/` directories.
2. Run the merge script using the default weight of `0.5`.

## Running the Script

```bash
python3 -m driving_model_scripts.merge
```

## Post-Merge Testing

After merging, test the resulting model in the MetaDrive simulator on sunnypilot/sunnypilot to verify appropriate driving behavior. This step ensures the merged model is compatible with the Comma3X device and meets runtime expectations.
