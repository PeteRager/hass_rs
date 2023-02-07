#/bin/bash -xv
HASSNAME="test"
TARGET="/mnt/c/github/ha_test"
source ./module_scripts.sh

build_init

build_switch switch_1 10
build_climate thermostat_1 5
build_fan fan_1 5

cp rs_simulation_package.yaml $TARGET/packages/

build_finish

