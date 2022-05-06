function cde_field_selector($cfg_selector) {

    function getParentGroup($childGroup) {
        return $childGroup.closest('.list-group').closest('.list-group-item');
    }

    function listItemsInGroup($group) {
        return $group.children('.list-group').children('.list-group-item');
    }

    function setCheckboxState($groups) {
        $groups.each(function() {
            const $group = $(this);
            const $items = listItemsInGroup($group);
            const $checkboxes = $items.children(':checkbox')
            const $checked = $checkboxes.filter(':checked');
            const $indeterminate = $checkboxes.filter(function() { return this.indeterminate });

            if ($checkboxes.length == $checked.length) {
                $group.children(':checkbox').prop('checked', true);
                $group.children(':checkbox').prop('indeterminate', false );
            } else if ($checked.length > 0 || $indeterminate.length > 0) {
                $group.children(':checkbox').prop('checked', false);
                $group.children(':checkbox').prop('indeterminate', true );
            } else {
                $group.children(':checkbox').prop('checked', false);
                $group.children(':checkbox').prop('indeterminate', false );
            }
        });
    }

    function toggleSelectAllItemsIn($group) {
        const groupIsSelected = $group.children(':checkbox').is(':checked');
        const $itemCheckboxes = listItemsInGroup($group).find(':checkbox');

        $itemCheckboxes.prop('indeterminate', false);
        $itemCheckboxes.prop('checked', groupIsSelected);
    }

    function doForAncestors($startingChild, ancestorFunction) {
        let $child = $startingChild;

        while (true) {
            const $parent = getParentGroup($child);

            if (!$parent.length) break;

            ancestorFunction($parent);
            $child = $parent;
        }
    }

    function initCheckboxStates() {
        const $cde_groups = $cfg_selector.find('.list-group-cdes');
        doForAncestors($cde_groups, setCheckboxState);
    }

    function initExpandSelected() {
        const $selected_cdes = $cfg_selector.find(".list-group-cdes :checkbox:checked");
        const expandGroup = function($group) {
            $group.find(">button[data-bs-toggle]").removeClass('collapsed');
            $group.find(">.list-group").addClass('show');
        }
        doForAncestors($selected_cdes, expandGroup);
    }

    function initEventHandlers() {
        $cfg_selector.find('ul.list-group').addBack().find('>.list-group-item>:checkbox').on('click', function() {
            const $group = $(this).closest('.list-group-item');
            toggleSelectAllItemsIn($group);
            doForAncestors($group, setCheckboxState);
        })
    }

    return {
        init: function() {
            initCheckboxStates();
            initExpandSelected();
            initEventHandlers();
        }
    }
}