function setupTimepicker($target, hasAMPM, startTimeStr) {
    var params = {
        on_change: function() { $("#main-form").trigger('change'); },
        show_meridian: hasAMPM,
        min_hour_value: hasAMPM ? 1:0,
        max_hour_value: hasAMPM ? 12:23
    }
    if (startTimeStr != "") {
        params.start_time = startTimeStr.split(",").map(Number);
    }
    $target.timepicki(params);
    $target.addClass("form-control");
    $(".meridian .mer_tx input").css("padding","0px"); // fix padding for meridian display
}

function setupDurationWidget(inputName, attributesStr) {
    var initAttrs = attributesStr.split(",");
    var textInput = "#id_" + inputName + "_text";
    var durationInput = "#id_" + inputName + "_duration";
    var initParams = {
        css: {
            width:"200px"
        },
        defaultValue: function() {
            return $(durationInput).val();
        },
        onSelect: function(element, seconds, duration, text) {
            $(durationInput).val(duration);
            $(textInput).val(text);
            $(durationInput).trigger('change');
        },
        years: initAttrs[0] == "true",
        months: initAttrs[1] == "true",
        days: initAttrs[2] == "true",
        hours: initAttrs[3] == "true",
        minutes: initAttrs[4] == "true",
        seconds: initAttrs[5] == "true",
        weeks: initAttrs[6] == "true"
    };
    $(textInput).timeDurationPicker(initParams);
    $(textInput).addClass("form-control");
}

$.timeDurationPicker.langs.en_US = {
  years: gettext("years"),
  months: gettext("months"),
  days: gettext("days"),
  hours: gettext("hours"),
  minutes: gettext("minutes"),
  seconds: gettext("seconds"),
  and: gettext("and"),
  button_ok: gettext("ok"),
  units: {
    year: {
      one: gettext("year"),
      other: gettext("years")
    },
    month: {
      one: gettext("month"),
      other: gettext("months")
    },
    day: {
      one: gettext("day"),
      other: gettext("days")
    },
    hour: {
      one: gettext("hour"),
      other: gettext("hours")
    },
    minute: {
      one: gettext("minute"),
      other: gettext("minutes")
    },
    second: {
      one: gettext("second"),
      other: gettext("seconds")
    }
  }
}
