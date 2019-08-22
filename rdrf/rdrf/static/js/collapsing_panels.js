/*
Collapsing panel support for TRRF form panels.

Call setUpCollapsingPanels() on document ready and set .collapsible CSS class on .panel's you want to be collapsible/expandable.

If the page has a .trrf-page-header we also add a collapse/expand all button to the header.
*/

function setUpCollapsingPanels() {
    var collapsiblePanelsSelector = "form .panel.collapsible";
    var collapsiblePanels = $(collapsiblePanelsSelector);

    // Apply only when we have more than 1 collapsible panel
    // if (collapsiblePanels.size() <= 1)
    //    return;

    function setUpCollapseAllButton() {
        // Adding the collapse button works only if we have one and only one <hx> element in the page header.
        // Otherwise, we might mess up the layout. This can be further customise as needed later on (ie. pass in selector of the button etc.)
        var pageHeader = $('.trrf-page-header > .panel-body > :header');
        if (pageHeader.size() != 1) {
            return;
        }
        var collapseAllToggleBtn = $('<span class="badge pull-right"><span class="glyphicon glyphicon-sort"></span></span>');
        function collapseAll() {
            var panelBodies = $(collapsiblePanelsSelector +  ' > .panel-body');
            var allCollapsed = panelBodies.filter('.collapse.in').size() == 0;
            panelBodies.collapse(allCollapsed ? 'show' : 'hide');
        }

        collapseAllToggleBtn.on('click', function() {
            collapseAll();
        })
        pageHeader.append(collapseAllToggleBtn);
    }

    function setUpCollapsiblePanel() {
        var panel = $(this);
        var header = panel.children(".panel-heading");
        var body = panel.children(".panel-body");

        header.css("cursor", "pointer");
        body.addClass("collapse");

        header.find("a").each(function() {
            $(this).on('click', function(evt) {
                evt.stopPropagation();
                return true;
            });
        });

        header.on('click', function(evt) {
            body.collapse('toggle');
        })
    }

    collapsiblePanels.each(setUpCollapsiblePanel);
    setUpCollapseAllButton();
}