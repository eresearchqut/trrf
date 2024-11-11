function hide_empty_menu() {
  var menu_element_count = $(".dropdown-menu-button ul li").length;

  if (menu_element_count == 0) {
    $(".dropdown-menu-button").hide();
  }
}

// Some pages can have larger banners than others, adjusting the top padding of the main content
// so that the banner doesn't overflow
function adjustContentTopPadding(contentId = "content") {
  var fixedTopSectionHeight = $(".fixed-top").height() || 0;
  var bannerHeight = $(".banner").height() || 0;
  var relativePadding = 36;

  if (fixedTopSectionHeight === 0 && bannerHeight === 0) {
    // Both navbar and banner are missing, better not do anything
    return;
  } else if (fixedTopSectionHeight !== 0) {
     if (bannerHeight !== 0) {
         $('.banner').css("top", fixedTopSectionHeight);
     }
     $('.sidebar').css("top", fixedTopSectionHeight);
  }

  $(`#${contentId}`).css(
    "padding-top", fixedTopSectionHeight + bannerHeight + relativePadding
  );
}
