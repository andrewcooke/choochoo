#!/bin/bash

source py/env/bin/activate
PYTHONPATH=py python -m unittest py/tests/*.py
