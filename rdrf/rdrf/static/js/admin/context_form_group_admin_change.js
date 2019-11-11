function context_form_group_registry_change(registry_id, selected_values) {
    $("select[name$='-registry_form']").empty();
    if (registry_id !== "") {
        url = "/api/v1/registries/" + registry_id + "/registry_forms/"
        $.getJSON(url, function(data) {
            $.each(data.forms, function(key, value) {
                $("select[name$='-registry_form']").append($("<option>").attr('value',value.id).text(value.name));
            });
            $.each(selected_values, function(key, value) {
                var values = $.map($('#' + key +' option'), function(option) {
                    return option.value;
                });
                if (values.includes(value)) {
                    $('#' + key).val(value).change();
                }
            });
        });
    }
}