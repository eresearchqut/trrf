function update_cde($target_cde, visibility) {
    switch(visibility) {
        case "enabled":
        case "disabled":
            $target_cde.parents('.form-group').prop('disabled', visibility == "disabled");
            break;
        case "visible":
            $target_cde.parents('.form-group').show();
            break;
        case "hidden":
            $target_cde.parents('.form-group').hide();
    }
}

function update_section($target_section, visibility) {
    switch(visibility) {
        case "visible":
            $target_section.parents('.panel').show();
            break;
        case "hidden":
            $target_section.parents('.panel').hide();
    }
}

function get_cde_name(base_name, index) {
    var entry = cdeNameMapping[base_name];
    if (!entry) {
        return base_name;
    }
    if (entry.formset && entry.formset.length > 0) {
        return entry.formset + "-" + index + "-" + cdeNamePrefix + base_name;
    }
    return cdeNamePrefix + base_name;
}

function get_cde_value(name, type, allow_multiple) {
    if (type == 'RadioSelect') {
        return $("[name='" + name + "']:checked").val();
    }
    if (allow_multiple) {
        var result = [];
        $("[name='" + name + "']:checked").each(function() {{
            result.push($(this).val());
        }});
        result.sort();
        return result.join(", ");
    }
    var el = $("[name='" + name +"']");
    if (el.length && el[0].type == 'checkbox') {
        return el.is(":checked") ? "checked": "";
    }
    return el.val();
}


function render_changes(visibility_map) {
    for (var prop in visibility_map) {
        if (visibility_map.hasOwnProperty(prop)) {
            var visibility = visibility_map[prop];
            var $target_cde = $("[name=" + prop + "]");
            var $target_section = $("[data-name=" + prop + "]");
            if ($target_section.length) {
                update_section($target_section, visibility);
            } else {
                update_cde($target_cde, visibility);
            }
        }
    }
}


function compare(actual_value, value, operator) {
    var actual_value_num = Number(actual_value);
    var value_num = Number(value);
    var valid_numbers = !isNaN(actual_value_num) && !isNaN(value_num);
    switch(operator) {
        case '>=':
            return valid_numbers ? actual_value_num >= value_num : actual_value >= value;
        case '<=':
            return valid_numbers ? actual_value_num <= value_num : actual_value <= value;
        case '>':
            return valid_numbers ? actual_value_num > value_num : actual_value > value;
        case '<':
            return valid_numbers ? actual_value_num < value_num : actual_value < value;
    }
}

function date_compare(actual_value, value, operator) {
    var first_date = moment(actual_value, "DD-MM-YYYY");
    var second_date = moment(value, "DD-MM-YYYY");
    switch(operator) {
        case "==":
            return first_date.isSame(second_date);
        case "!=":
            return !first_date.isSame(second_date);
        case ">=":
            return first_date.isSameOrAfter(second_date);
        case "<=":
            return first_date.isSameOrBefore(second_date);
        case ">":
            return first_date.isAfter(second_date);
        case "<":
            return first_date.isBefore(second_date);
    }
}

function set_unset_test(actual_value, value) {
    switch (value) {
        case "set": return actual_value !== undefined && actual_value.trim() != '';
        case "unset": return actual_value === undefined || actual_value.trim() == '';
    }
}

function test_cde_value(name, base_name, op, value) {
    var entry = cdeNameMapping[base_name];
    var fullName = name.includes(cdeNamePrefix) ? name: cdeNamePrefix + name;
    if (!entry.allow_multiple) {
        var actual_value = get_cde_value(fullName, entry.type, entry.allow_multiple);
        if (op == "is") {
            return set_unset_test(actual_value, value);
        }
        if (entry.type == "DateWidget") {
            return date_compare(actual_value, value, op);
        } else {
            switch(op) {
                case "==":
                    return actual_value == value;
                case "!=":
                    return actual_value != value;
                case ">=":
                case "<=":
                case ">":
                case "<":
                    return compare(actual_value, value, op);
            }
        }
    } else {
        var ret_val = get_cde_value(fullName, entry.type, entry.allow_multiple);
        if (op == "is") {
            return set_unset_test(ret_val, value);
        }
        cde_values = ret_val.split(",").map(function(v){ return v.trim();});
        target_values = value.split(",").map(function(v){ return v.trim();});
        equal_values = false;
        equal_len = cde_values.length == target_values.length
        switch(op) {
            case "==":
                return equal_len && cde_values.find(function(value) { return !target_values.includes(value);}) === undefined;
            case "!=":
                return !equal_len || cde_values.find(function(value) { return !target_values.includes(value);}) !== undefined;
            case "includes":
                return cde_values.some(function(el) {
                    return target_values.includes(el);
                 });
            case "does not include":
                return cde_values.every( function(el) {
                    return !target_values.includes(el);
                });
        }
    }
}

function test_cde_value_simple(name, op, value) {
    return test_cde_value(name, name, op, value);
}


function test_conditions(results, boolean_ops) {
    var result, partial_result;
    var previous_op = '';
    while (results.length > 0) {
        var op = boolean_ops.shift();
        var first = results.shift();
        var second = results.shift();
        if (second === undefined) {
            switch (op) {
                case '&&':
                    result = result && first;
                    break;
                case '||':
                    result = result || first;
                    break;
            }
        } else {
            switch(op) {
                case '&&':
                    partial_result = first && second;
                    break;
                case '||':
                    partial_result = first || second;
                    break;
            }
            switch (previous_op) {
                case '':
                    result = partial_result;
                    break;
                case '&&':
                    result = result && partial_result;
                    break;
                case '||':
                    result = result || partial_result;
                    break;
            }
        }
        previous_op = op;
    }
    return result;
}

function visibility_map_update(visibility_map, name, action, is_section) {
    var entry = is_section ? undefined : cdeNameMapping[name];
    if (!entry) {
        visibility_map[name] = action;
    } else {
        if (entry.formset && entry.formset.length > 0) {
            for (var idx = 0; idx < total_forms_count(entry.formset); idx ++) {
                var full_name = get_cde_name(name, idx);
                visibility_map[full_name] = action;
            }
        } else {
            var full_name = get_cde_name(name);
            visibility_map[full_name] = action;
        }
    }
}

function add_change_handler(name) {
    $("[name='" + name +"']").change(function() {
        render_changes(visibility_handler());
    });
}
