function hide_empty_menu() {
    var menu_element_count = $(".dropdown-menu-button ul li").length;

    if (menu_element_count == 0) {
        $(".dropdown-menu-button").hide();
    }
}

// Some pages can have larger banners than others, adjusting the top padding of the main content
// so that the banner doesn't overflow
function adjustContentTopPadding() {
    var navbarHeight = $(".navbar").height();
    var bannerHeight = $(".banner").height();
    if (navbarHeight == null || bannerHeight == null) {
        // Can't find navbar or banner, better not do anything
        return
    }
    $("#content").css({"padding-top": navbarHeight + bannerHeight});
}
