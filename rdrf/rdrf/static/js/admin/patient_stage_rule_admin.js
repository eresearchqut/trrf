django.jQuery(document).ready(function() {
    $("#id_registry").change(function(){
        registry_change_handler("#id_from_stage", "#id_to_stage", $(this).val());
    });
    $("#id_registry").trigger('change');
});