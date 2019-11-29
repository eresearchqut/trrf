django.jQuery(document).ready(function() {
    var $registry = $("#id_registry");
    $registry.change(function(){
        registry_change_handler("#id_allowed_prev_stages", "#id_allowed_next_stages", $(this).val(), false);
    });
    if ($registry.val() == '') {
        $registry.trigger('change');
    }
});
