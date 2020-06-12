#!/bin/bash

docker volume rm -f disk-data
docker volume create disk-data
docker volume ls

