django.jQuery(document).ready(function() {
    var initiallySelectedValues = {};
    $("select[name$='-registry_form']").each(function(value) {
        var value = $(this).val();
        if (value !== "") {
            initiallySelectedValues[$(this).attr('id')] = value;
        }
    });

    $("#id_registry").change(function() {
        contextFormGroupRegistryChange($(this).val(), initiallySelectedValues);
    });
    $("#id_registry").trigger('change');
});