#!/bin/bash

gawk -f dev/build-doc.awk docs/fit-cookbook.md-template > docs/fit-cookbook.md
