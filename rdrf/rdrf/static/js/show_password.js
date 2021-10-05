function initToggleShowPassword($password_fields, $password_toggle) {
    /* Private Fields */
    let timeout_id;
    let enable_timeout = true;

    const timeout_sec = 60;
    const password_timeout_msg = gettext("Passwords will be automatically hidden after %s seconds.");
    const turn_off_timeout_msg = gettext("Don't automatically hide passwords.");
    const $timeout_message = $("<p />", {
            class: "small text-muted mb-3",
            style: "display: none",
            html: interpolate(password_timeout_msg, [timeout_sec]) + " <br />" +
                "<button id='turn_off_timeout' type='button' class='p-0 btn btn-link btn-sm'>" + turn_off_timeout_msg + "</button>"
    });

    /* Private Functions */
    const toggleFieldType = (type) => $password_fields.attr("type", type);
    const resetPasswordFields = () => {
        toggleFieldType("password");
        $timeout_message.hide();
        $password_toggle.prop("checked", false);
    };

    /* Init */
    $password_toggle.on('click', () => {
        if ($password_toggle.is(":checked")) {
            toggleFieldType("text");

            if (enable_timeout) {
                $timeout_message.show();
                timeout_id = setTimeout(resetPasswordFields, timeout_sec * 1000);
            }
        } else {
            toggleFieldType("password");
            $timeout_message.hide();
            clearTimeout(timeout_id);
        }
    });

    $timeout_message.find("#turn_off_timeout").on("click", () => {
        enable_timeout = false;
        clearTimeout(timeout_id);
        $timeout_message.hide();
    });

    $timeout_message.insertAfter($password_toggle.parent("div"));
}