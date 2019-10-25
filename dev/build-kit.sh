#!/bin/bash

gawk -f dev/build-doc.awk docs/kit.md-template > docs/kit.md
