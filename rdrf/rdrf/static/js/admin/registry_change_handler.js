function registry_change_handler(first_stage_id, second_stage_id, registry_id, add_stage_empty_option) {
    $(first_stage_id).empty();
    $(second_stage_id).empty();
    if (add_stage_empty_option) {
        $(first_stage_id).append($("<option>").attr('value','').text('------'));
        $(second_stage_id).append($("<option>").attr('value','').text('------'));
    }
    var url = '/api/v1/registries/' + registry_id + '/stages/';
    if (registry_id !== "" && url != "") {
        $.getJSON(url, function(data) {
            $.each(data, function(key, value) {
                $(first_stage_id).append($("<option>").attr('value',value.id).text(value.name));
                $(second_stage_id).append($("<option>").attr('value',value.id).text(value.name));
            });
        });
    }
}
