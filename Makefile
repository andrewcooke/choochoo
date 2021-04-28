MOUNT:="--mount=type=cache,target=/root/.cache/pip"
TZ:=$TZ
ID:=$(shell id -u):$(shell id -g)
DOCKER_BUILDKIT=1
PG_CONFIG_FILE:=postgres-default.conf

PHONY: run run-slow down

test:
	echo ${PG_CONFIG_FILE}

run:
	PG_CONFIG_FILE=${PG_CONFIG_FILE} docker-compose up --build
	
run-slow:
	MOUNT="" DOCKER_BUILDKIT=0 PG_CONFIG_FILE=${PG_CONFIG_FILE} docker-compose up --build

up:
	docker-compose up

down:
	docker-compose down

remove-volumes:
	docker-compose down --volumes

reset: remove-volumes run-slow
