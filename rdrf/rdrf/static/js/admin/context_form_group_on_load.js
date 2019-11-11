django.jQuery(document).ready(function() {
    var selected_values = {};
    $("select[name$='-registry_form']").each(function(value) {
        var value = $(this).val();
        if (value !== "") {
           selected_values[$(this).attr('id')]=value;
        }
    });
    $("#id_registry").change(function(){
        context_form_group_registry_change($(this).val(), selected_values);
    });
    $("#id_registry").trigger('change');
});