$(document).ready(function() {

  var transition           = "all 0.5s ease 0.0s";
  var new_border           = "1px solid #B1B23F";
  var new_background_color = "#FEFFD7";
  var monitored_fields     = "select,input,textarea";

  // Save default colors for later recovery.
  var old_border = $('#main-form *').filter('input').first().css("border");
  var old_background_color = $('#main-form *').filter('input').first().css("background-color");

  var old_radio_border = $('#main-form *').filter(':radio').first().parent().parent().css("border");
  var old_radio_background_color = $('#main-form *').filter(':radio').first().parent().parent().css("background-color");

  // Save defaults in each DOM element's pre data and append transitions
  $('#main-form *').filter(monitored_fields).each(function() {
    if (!$(this).is(':radio')) {
      $(this).data('pre', $(this).val()+'');
      $(this).css("transition", transition);
    } else {
      $(this).parent().parent().data('pre', $(this).parent().parent().find(':checked').val());
      $(this).parent().parent().css("transition", transition);
      console.log($(this).parent().parent().children().filter(':checked').val());
    }
  });

  // Change handler, executed when any form change is made - compares
  // current value to value stored in DOM element's pre data and
  // highlights fields that have changed
  $('#main-form').change(function() {
    $('#main-form *').filter(monitored_fields).each(function() {
      if (!$(this).is(':radio')) {
        if ($(this).val() != $(this).data('pre')) {
          $(this).css("border", new_border);
          $(this).css("background-color", new_background_color);
        } else {
          $(this).css("border", old_border);
          $(this).css("background-color", old_background_color);
        }
      } else {
        if ($(this).parent().parent().find(':checked').val() != $(this).parent().parent().data('pre')) {
          $(this).parent().parent().css("border", new_border);
          $(this).parent().parent().css("background-color", new_background_color);
        } else {
          $(this).parent().parent().css("border", old_radio_border);
          $(this).parent().parent().css("background-color", old_radio_background_color);
        }

      }
    });
  });
});
