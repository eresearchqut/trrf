
function setSelectedValues(selectValues) {
    $.each(selectValues, function(key, value) {
        var values = $.map($('#' + key +' option'), function(option) {
            return option.value;
        });
        if (values.includes(value)) {
            $('#' + key).val(value).change();
        }
    });
}

function contextFormGroupRegistryChange(registryId, selectValues) {
    var url = Urls['v1:registry-forms'](registryId);

    $("select[name$='-registry_form']").empty();
    $("select[name$='-registry_form']").append($("<option>").attr('value', '').text('--------'));

    if (registryId !== "" && url !== "") {
        $.getJSON(url, function(data) {
            $.each(data, function(key, value) {
                $("select[name$='-registry_form']").append($("<option>").attr('value', value.id).text(value.nice_name));
            });

            setSelectedValues(selectValues);
       });
    }
}