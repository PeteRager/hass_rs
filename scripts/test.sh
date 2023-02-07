#/bin/bash -xv

# change these entries 
HASSNAME="test"
TARGET="/mnt/c/github/ha_test"

# do not change
source ./module_scripts.sh
build_init

# add your entities here and replace the examples
# domain, entity, timeout in seconds
build_switch switch_1 10
build_climate thermostat_1 5
build_fan fan_1 5

# remove this unless you are trying this in simulation mode
cp rs_simulation_package.yaml $TARGET/packages/

# do not remove
build_finish

