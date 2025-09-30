# Autonomy

This repository contains machine learning components and tools to advance sunnypilot's capabilities in autonomous driving.

## Overview

The repository includes implementations and tools for:

- **Vision Encoders**: Neural network components for processing visual data from cameras.
- **Vision Classifiers**: Models for classifying objects and scenes in driving environments, such as street lights, pedestrians, etc...
- **Machine Learning Tests**: Test suites for validating ML models and modeld codebase.
- **Testing Capabilities**: Validated integration testing for troubleshooting and analyzing model performance.
- **Driving Model Merge Scripts**: Tools to combine multiple driving models into one.
- **Quantizers**: Algorithms for model quantization to optimize performance and size, able to downsample 1 GB models to 200MiB models.
- **Model-Specific Code**: Offloaded code from the sunnypilot repository to help better the dev experience.

## Setting up environment

To set up the development environment, run the appropriate setup script for your operating system:

- **macOS**: `./tools/setup/mac_setup.sh`
- **Ubuntu**: `./tools/setup/ubuntu_setup.sh`

After running the script, activate the virtual environment in your shell:
`source .venv/bin/activate`

The params module uses a compiled C++ library for default values. Build it with:
`scons`

## Repository Structure

- `navigation`: module containing mapbox navigation features created to be transitioned to sunnypilot as a semi-offline navigation naemon. This module will map turn desires, keep left/right, and eventually auto lane changes to navigation instructions to provide a more comfortable user experience.

- `tools`: setup scripts and test runners. 

## Contributing

We welcome both pull requests and issues on GitHub. Bug fixes are encouraged.

Pull requests should be against the most current `master` branch.

## License

sunnypilot autonomy is released under the [MIT License](LICENSE).

> **THIS IS ALPHA QUALITY SOFTWARE FOR RESEARCH PURPOSES ONLY. THIS IS NOT A PRODUCT.
> YOU ARE RESPONSIBLE FOR COMPLYING WITH LOCAL LAWS AND REGULATIONS.
> NO WARRANTY EXPRESSED OR IMPLIED.**

For full license terms, please see the [`LICENSE`](LICENSE) file.
