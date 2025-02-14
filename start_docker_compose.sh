#!/bin/bash

docker compose -f compose.yml build --build-arg UID="$(id -u)" --build-arg GID="$(id -g)" --build-arg USERNAME="$(id -un)" --build-arg GROUPNAME="$(id -gn)" && docker compose -f compose.yml up --force-recreate