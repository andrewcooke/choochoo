#!/bin/bash

source py/env/bin/activate
pip install grip
cd docs
grip index.md
