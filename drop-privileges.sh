#!/bin/bash

set -e

USER=$(stat -c %U "${1}")
shift
exec sudo -u "${USER}" ${@}
