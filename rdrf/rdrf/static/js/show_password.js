function initToggleShowPassword($passwordFields, $passwordToggle) {

    let timeoutId;

    const timeout_ms = 60000;
    const toggleFieldType = function(type) {
        $passwordFields.attr("type", type);
    }
    const resetPasswordFields = function() {
        toggleFieldType("password");
        $passwordToggle.prop("checked", false);
    };

    $passwordToggle.on('click', function() {
        if ($passwordToggle.is(":checked")) {
            toggleFieldType("text")
            timeoutId = setTimeout(resetPasswordFields, timeout_ms);
        } else {
            toggleFieldType("password")
            clearTimeout(timeoutId);
        }
    });
}