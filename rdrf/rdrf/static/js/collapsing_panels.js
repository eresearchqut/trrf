/*
Collapsing panel support for TRRF form panels.

Call CollapsingPanels.setUp() on document ready and set .collapsible CSS class on .card's you want to be collapsible/expandable.

If the page has a .trrf-page-header we also add a collapse/expand all button to the header.
*/

var CollapsingPanels = function() {
    var collapsiblePanelsSelector = "form .card.collapsible";
    var currentPromise = Promise.resolve();

    function getAllPanelBodies() {
        return $(collapsiblePanelsSelector +  ' > .card-body');
    }

    function getFirstPanelBody() {
        return $(collapsiblePanelsSelector +  ' > .card-body').first();
    }


    function expandAll() {
        currentPromise = Promise.all(getAllPanelBodies().map(function () {
            return new Promise((resolve) => {
                const panel = $(this);
                panel.one("shown.bs.collapse", resolve);
                panel.collapse('show');
            });
        }));
    }

    function expandFirst() {
        currentPromise = new Promise((resolve) => {
            const panel = getFirstPanelBody();
            panel.one("shown.bs.collapse", resolve);
            panel.collapse('show');
        });
    }


    function collapseAll() {
        currentPromise = Promise.all(getAllPanelBodies().map(function () {
            return new Promise((resolve) => {
                const panel = $(this);
                panel.one("hidden.bs.collapse", resolve);
                panel.collapse('hide');
            });
        }));
    }

    function expandParentPanel(el, handler) {
        var parentPanel = $(el).parents(collapsiblePanelsSelector);
        if (!parentPanel.length) {
            return;
        }
        var panelBody = parentPanel.find('.card-body');
        panelBody.collapse('show');
        if (typeof(handler) !== 'undefined') {
            handler();
        };
    }

    function setUpCollapseAllButton() {
        // Adding the collapse button works only if we have one and only one <hx> element in the page header.
        // Otherwise, we might mess up the layout. This can be further customise as needed later on (ie. pass in selector of the button etc.)
        var pageHeader = $('.trrf-page-header > .card-body > :header');
        if (pageHeader.length != 1) {
            return;
        }
        var collapseAllToggleBtn = $('<span class="badge bg-secondary float-end"><span class="fa fa-sort"></span></span>');
        // var collapseAllToggleBtn = $('<button type="button" class="btn btn-secondary"><span class="fa fa-sort"></span></button>');

        function onCollapseAll() {
            var panelBodies = $(collapsiblePanelsSelector +  ' > .card-body');
            var allCollapsed = panelBodies.filter('.collapse.show').length == 0;
            if (allCollapsed) {
                expandAll();
            } else {
                collapseAll();
            }
        }

        collapseAllToggleBtn.on('click', onCollapseAll);
        pageHeader.after(collapseAllToggleBtn);
    }

    function setUpCollapsiblePanel() {
        var panel = $(this);
        var header = panel.children(".card-header");
        var body = panel.children(".card-body");
        var iconParent = header;
        if (header.find(".card-title").length == 1) {
            iconParent = header.find(".card-title");
        }

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
        });

        function createIconElement(panel) {
            var body = panel.children(".card-body");
            var isCollapsed = !body.hasClass('in');
            var icon = isCollapsed ? 'fa-caret-right' : 'fa-caret-down';
            return '<span class="panel-collapse-icon fa ' + icon + '"></span>';
        }

        function toggleIcon() {
            header.find('span[class*="panel-collapse-icon"]').toggleClass('fa-caret-right fa-caret-down');
        }

        function available() {
            panel.addClass("section-available");
        }

        panel.on('hide.bs.collapse', toggleIcon);
        panel.on('show.bs.collapse', toggleIcon);
        panel.on('shown.bs.collapse', available);

        iconParent.prepend(createIconElement(panel));
   }


    function setUp() {
        var collapsiblePanels = $(collapsiblePanelsSelector);
        // Apply only when we have more than 1 collapsible panel
        // if (collapsiblePanels.length <= 1)
        //    return;

        collapsiblePanels.each(setUpCollapsiblePanel);
        setUpCollapseAllButton();
    }

    return {
        setUp: setUp,
        expandParentPanel: expandParentPanel,
        expandAll: expandAll,
        collapseAll: collapseAll,
        expandFirst: expandFirst,
        currentPromise: currentPromise,
    };
}();

