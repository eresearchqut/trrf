function initToggleShowPassword($passwordFields, $passwordToggle) {
    $passwordToggle.on('click', function() {
        if ($(this).is(":checked")) {
            $passwordFields.attr("type", "text");
        } else {
            $passwordFields.attr("type", "password");
        }
    });
}