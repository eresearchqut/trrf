/**
 * Hierarchical checkbox tree selector widget
 * Usage:
 * * Checkboxes should be structured within nested ul.list-groups
 * * The root of the hierarchy needs to have the class .tree-selector-root
 * * The tip of the hierarchy (the most deeply nested) needs to have the class .tree-selector-root
 * * e.g.
 * ```
 * <ul class="list-group tree-selector-root>
 *     <li class="list-group-item">
 *         ...
 *         <ul class="list-group">
 *             <li class="list-group-item">
 *                 ...
 *                 <ul class="list-group tree-selector-tip>
 *                     <li class="list-group-item">
 *                         ...
 *                     </li>
 *                 </ul>
 *             </li>
 *         </ul>
 *     </li>
 * </ul>
 * ```
 *
 * Initialise the selector for you element with tree_selector($(".your-jq-selector")).init({expandSelected: true})
 * Options:
 * * expandSelected: boolean to indicate whether to expand the hierarchy for selected tip items.
 *
 * @param $root
 * @returns {{init: init}}
 */
function tree_selector($root) {

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
        const $cde_groups = $root.find('.tree-selector-tip');
        doForAncestors($cde_groups, setCheckboxState);
    }

    function initExpandSelected() {
        const $selected_cdes = $root.find(".tree-selector-tip :checkbox:checked");
        const expandGroup = function($group) {
            $group.find(">button[data-bs-toggle]").removeClass('collapsed');
            $group.find(">.list-group").addClass('show');
        }
        doForAncestors($selected_cdes, expandGroup);
    }

    function initEventHandlers() {
        $root.find('ul.list-group').addBack().find('>.list-group-item>:checkbox').on('click', function() {
            const $group = $(this).closest('.list-group-item');
            toggleSelectAllItemsIn($group);
            doForAncestors($group, setCheckboxState);
        })
    }

    return {
        init: function(opts={expandSelected: true}) {
            initCheckboxStates();

            if (opts.expandSelected) {
                initExpandSelected();
            }

            initEventHandlers();
        }
    }
}