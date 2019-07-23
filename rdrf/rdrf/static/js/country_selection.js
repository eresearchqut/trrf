function select_country(obj) {
    var state_select;
    state_id = obj.id.replace("Country", "State");
    state_id = state_id.replace("country", "state"); // if used in demographics there are lower letter ids
    if (state_id.match(/formset/)) {
        // CDEs using this widget are named diferently in formsets
        state_select = $('#' + state_id);
    }
    else {
        state_select = $("#" + state_id);
    }

    state_select.find('option').remove();

    if (obj.value != "") {
        $.get( "/api/v1/countries/" + obj.value + "/states", function( data ) {
        if (data) {
            $.each(data, function(i, item) {
                var option_html = "<option value='" + item.code + "'>" + item.name + "</option>";
                state_select.append(option_html);
                })
            }
        });
    }
}