function lookup(element, source_url) {
    element.autocomplete({
      source: source_url,
      minLength: 1,
      select: function(event, ui) {
      }
    }).data("ui-autocomplete")._renderItem = function(ul, item) {
      item.value = item.label;
      return $("<li>")
        .append("<a>" + item.label + "</a>")
        .appendTo(ul);
    };
}
