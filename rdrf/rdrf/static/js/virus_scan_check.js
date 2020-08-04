function update_status_div(base_id, status, is_visible) {
    var target = $("#" + base_id + "_" + status);
    is_visible ? target.show(): target.hide();
}

function check_virus_scan_status(base_url, base_id, value, interval) {
    $.ajax({
        url: base_url + "?check_status=true",
        type: "GET",
        success: function(data) {
            var status = data['response'];
            if (status == 'scanning') {
                update_status_div(base_id, 'scanning', true);
            } else {
                update_status_div(base_id, 'scanning', false);
                clearInterval(interval);
                if (status == 'infected') {
                    update_status_div(base_id, 'infected', true);
                } else if (status == 'not found') {
                    update_status_div(base_id, 'notfound', true);
                } else if (status == 'clean') {
                    $("#" + base_id + "_link").html('<a href="' + base_url + '" target="_blank" rel="noreferrer noopener">' + value + '</a>');
                }
            }
        }
    });
}

function setup_virus_status_check(base_url, base_id, value, interval_ms) {
    var _interval = setInterval( function() {
        check_virus_scan_status(base_url, base_id, value, _interval);
    }, interval_ms);
}
