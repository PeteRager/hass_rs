build_init()
{
    mkdir -p $TARGET/.storage 
    mkdir -p $TARGET/packages 
    mkdir -p $TARGET/scripts 
    build_rs_services
    rm -rf temp
    mkdir temp
    cp lovelace.dashboard_services.json temp/        
}

build_finish()
{
    cp temp/lovelace.dashboard_services.json $TARGET/.storage/lovelace.dashboard_services
    rm -rf temp
}

build_rs_no_param_template_script()
# DOMAIN
# METHOD
# TARGET
{
    sed "s/MESSAGE_DETAILS//g;s/COMPARISON_OPERATION/is_state(entity_id, 'TARGET')/g" rs_call_master_script.yaml |
    sed "s/DOMAIN/$1/g;s/METHOD/$2/g;s/TARGET/$3/g" > $TARGET/scripts/rs_call_$1_$2_script.yaml
}


build_rs_one_param_condition_template_script()
# DOMAIN
# METHOD
# DATA_TARGET_NAME
# CONDITION
{
    yq --from-file rs_one_param_attr_template.yq rs_call_master_script.yaml |
    sed "s/MESSAGE_DETAILS/{{target_value}}/g;s/COMPARISON_OPERATION/$4/g" |
    sed "s/DOMAIN/$1/g;s/METHOD/$2/g;s/DATA_TARGET_NAME/$3/g" > $TARGET/scripts/rs_call_$1_$2_script.yaml
}

build_rs_services()
# ZWAVE Entity
# ENTITY_ID to monitor 
# TIMEOUT
# COMMAND_CLASS
# PROPERTY_NAME
# Output file
{
    # switch
    build_rs_no_param_template_script switch turn_on on
    build_rs_no_param_template_script switch turn_off off
    # climate
    build_rs_one_param_condition_template_script climate set_hvac_mode hvac_mode "is_state(entity_id, target_value)"
    build_rs_one_param_condition_template_script climate set_temperature temperature "state_attr(entity_id, 'temperature')|int == target_value"
    # fan
    build_rs_no_param_template_script fan turn_off off
    build_rs_one_param_condition_template_script fan turn_on percentage "is_state(entity_id,'on')"
}

lovelace_template_all_entity_methods()
# DOMAIN
# NAME
{
    if [ "$1" = "switch" ]     
    then
        VIEW=1
    fi

    if [ "$1" = "climate" ]     
    then
        VIEW=2
    fi
    if [ "$1" = "fan" ]     
    then
        VIEW=3
    fi


    jq --arg VIEW $VIEW -f metric-cards.jq temp/lovelace.dashboard_services.json | sed "s/DOMAIN/$1/g" | sed "s/NAME/$2/g" > temp/temp.json
    cp temp/temp.json temp/lovelace.dashboard_services.json
}


build_rs_entity_no_param_domain_method()
# DOMAIN
# METHOD
# NAME
# TIMEOUT
{
    cat rs_entity_call_no_param_template_script.yaml |
    sed "s/MESSAGE_DETAILS/{{target_value}} /g" |
    sed "s/DOMAIN/$1/g;s/METHOD/$2/g;s/NAME/$3/g;s/TIMEOUT/$4/g" > $TARGET/scripts/rs_entity_call_$3_$1_$2_script.yaml
}

build_rs_entity_one_param_domain_method()
# DOMAIN
# METHOD
# NAME
# DATA_TARGET_NAME
# TIMEOUT
{
    cat rs_entity_call_one_param_template_script.yaml |
    sed "s/DOMAIN/$1/g;s/METHOD/$2/g;s/NAME/$3/g;s/DATA_TARGET/$4/g;s/TIMEOUT/$5/g" > $TARGET/scripts/rs_entity_call_$3_$1_$2_script.yaml
}

build_switch()
# NAME
# TIMEOUT
{
    build_rs_entity_no_param_domain_method switch turn_on $1 $2
    build_rs_entity_no_param_domain_method switch turn_off $1 $2

    sed "s/DOMAIN/switch/g;s/NAME/$1/g" rs_entity_call_template_package.yaml > $TARGET/packages/rs_entity_call_template_switch_$1_package.yaml
    lovelace_template_all_entity_methods switch $1
}

build_climate()
# NAME
# TIMEOUT
{
    build_rs_entity_one_param_domain_method climate set_hvac_mode $1 hvac_mode $2
    build_rs_entity_one_param_domain_method climate set_temperature $1 temperature $2

    sed "s/DOMAIN/climate/g;s/NAME/$1/g" rs_entity_call_template_package.yaml  > $TARGET/packages/rs_entity_call_template_climate_$1_package.yaml
    lovelace_template_all_entity_methods climate $1
}

build_fan()
# NAME
# TIMEOUT
{
    build_rs_entity_one_param_domain_method fan turn_on $1 percentage $2
    build_rs_entity_no_param_domain_method fan turn_off $1 $2

    sed "s/DOMAIN/fan/g;s/NAME/$1/g" rs_entity_call_template_package.yaml  > $TARGET/packages/rs_entity_call_template_fan_$1_package.yaml
    lovelace_template_all_entity_methods fan $1
}
