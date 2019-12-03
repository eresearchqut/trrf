$(document).ready(function() {

  var transition           = "all 0.5s ease 0.0s";
  var new_border           = "1px solid #B1B23F";
  var new_background_color = "#FEFFD7";
  var monitored_fields     = "select,input,textarea";

  // Save default colors for later recovery.
  // TS: Moved these into the change handler below as they were called before the elements
  // get styled on Chromium which resulted in saving an incorrect border of 0
  // https://eresearchqut.atlassian.net/browse/TRRFFDA-449
  var old_border;
  var old_background_color;

  // Save defaults in each DOM element's pre data and append transitions
  $('#main-form *').filter(monitored_fields).each(function() {
    if ($(this).is(':radio')) {
      $(this).parent().parent().data('pre', $(this).parent().parent().find(':checked').val());
      $(this).parent().parent().css("transition", transition);
    } else if ($(this).is(':checkbox')) {
      $(this).data('pre', $(this).is(":checked") ? $(this).val() : '');
    } else {
      $(this).data('pre', $(this).val()+'');
      $(this).css("transition", transition);
    }
  });

  // Change handler, executed when any form change is made - compares
  // current value to value stored in DOM element's pre data and
  // highlights fields that have changed
  $('#main-form').change(function() {
    if (!old_border) {
      old_border = $('#main-form *').filter('input').first().css("border");
    }
    if (!old_background_color) {
      old_background_color = $('#main-form *').filter('input').first().css("background-color");
    }

    $('#main-form *').filter(monitored_fields).each(function() {
      if ($(this).hasClass('timepicki-input')) {
        return;
      }

      function didChange(el) {
        var pre, curVal;
        if (el.is(':radio')) {
          pre = el.parent().parent().data('pre');
          curVal = el.parent().parent().find(':checked').val();
        } else if (el.is(':checkbox')) {
          pre = el.data('pre');
          curVal = el.is(":checked") ? el.val() : '';
        } else {
          pre = el.data('pre');
          curVal = el.val();
        }
        return pre !== curVal;
      }

      var didValueChange = didChange($(this));

      var border = didValueChange ? new_border : old_border;
      var background_color = didValueChange ? new_background_color : old_background_color;

      var elementToHighlight = ($(this).is(':radio') || $(this).is(':checkbox')) ? $(this).parent().parent() : $(this);

      if (!($(this).is(':radio') || $(this).is(':checkbox'))) {
        // No border changes for radio boxes and checkboxes
        elementToHighlight.css('border', border);
      }
      elementToHighlight.css('background-color', background_color);
    });
  });
});
