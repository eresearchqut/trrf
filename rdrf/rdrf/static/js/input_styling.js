function setInputStyling() {
    $(":input").not(':input[type=checkbox], :input[type=radio], :input[type=button], :input[type=submit], :input[type=reset], :input[type=file]').addClass("form-control");
    $("textarea").addClass("form-control");
    $("select").addClass("form-control");
    $(":input[type=file]").addClass("form-control-file");
}
