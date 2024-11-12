#!/bin/bash

# Remove existing lambda_layer if it exists
rm -rf lambda_layer

# Create a temporary directory for dependencies
mkdir -p lambda_layer/python

# Create a temporary virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies into the virtual environment
pip install -r requirements.txt

# Copy installed packages to lambda layer
cp -r venv/lib/python*/site-packages/* lambda_layer/python/

# Deactivate and remove virtual environment
deactivate
rm -rf venv

# Clean up unnecessary files to reduce package size
cd lambda_layer/python
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# Create __init__.py files in all directories to ensure proper module imports
find . -type d -exec touch {}/__init__.py \; 2>/dev/null

cd ../..
