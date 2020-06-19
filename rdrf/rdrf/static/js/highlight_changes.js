$(document).ready(function() {

  var transition           = "all 0.5s ease 0.0s";
  var newBorder           = "1px solid #B1B23F";
  var newBackgroundColor = "#FEFFD7";
  var monitoredFields     = "select,input,textarea";

  // Save defaults in each DOM element's pre data and append transitions
  $('#main-form *').filter(monitoredFields).each(function() {
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
    $('#main-form *').filter(monitoredFields).each(function() {
      if ($(this).hasClass('timepicki-input') || $(this).hasClass("duration-input")) {
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

      var elementToHighlight = $(this);
      var highlightBorder = true;
      if ($(this).is(':radio') || $(this).is(':checkbox')) {
        elementToHighlight = $(this).parent().parent();
        highlightBorder = false;
      }

      function handleHighlighting(el, propertyName, newValue) {
        var savedPropertyName = 'saved-' + propertyName;
        var savedValue = el.data(savedPropertyName);

        if (didValueChange) {
          if (typeof savedValue === 'undefined') {
            // Save original CSS property value before overwriting it
            el.data(savedPropertyName, el.css(propertyName));
          }
          el.css(propertyName, newValue);
          return;
        }

        // Value didn't change and original CSS property intact -> nothing to do
        if (typeof savedValue === 'undefined') {
            return;
        }

        // Value changed back to original value -> restore saved CSS property and remove saved value
        el.css(propertyName, savedValue);
        el.removeData(savedPropertyName);
      }

      handleHighlighting(elementToHighlight, 'background-color', newBackgroundColor);
      if (highlightBorder) {
        handleHighlighting(elementToHighlight, 'border', newBorder);
      }
    });
  });
});
