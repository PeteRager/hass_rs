.data.config.views[0].cards[0].entities += [ "counter.rs_DOMAIN_NAME_err" ] |
.data.config.views[0].cards[1].entities += [ {"entity":"counter.rs_DOMAIN_NAME_err"} ] |
.data.config.views[$VIEW|tonumber].cards += 
[
    { "type" : "entities", "entities" : 
    [
        {"entity":"input_text.rs_DOMAIN_NAME_message"},
        {"entity":"counter.rs_DOMAIN_NAME_err"},
        {"entity":"counter.rs_DOMAIN_NAME_retry"},
        {"entity":"counter.rs_DOMAIN_NAME_calls"},
        {"entity":"sensor.rs_DOMAIN_NAME_duration"},
        {"entity":"sensor.rs_DOMAIN_NAME_last"} 
    ] 
    }
] |
.data.config.views[0].cards[1].entities += [ {"entity":"sensor.rs_DOMAIN_NAME_duration"} ]