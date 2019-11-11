function makeUrl(path_param, suffix) {
    var url = window.localStorage.getItem("baseAPIRegistryUrl");
    if (url !== undefined) {
        return url + path_param + "/" + suffix + "/";
    }
    return "";
}

function context_form_group_registry_change(registry_id, selected_values) {
    url = makeUrl(registry_id, "registry_forms");
    $("select[name$='-registry_form']").empty();
    if (registry_id !== "" && url !== "") {
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