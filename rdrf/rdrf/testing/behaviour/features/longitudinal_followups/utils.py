from aloe import world

from rdrf.testing.behaviour.features.utils import wait_for_first_section

EMAIL_SELECTOR = "#id_messages > tbody > tr"


def get_email(n):
    return world.browser.find_elements_by_css_selector(
        f"{EMAIL_SELECTOR}:nth-child({n}) > td a"
    )


def go_to_url(path):
    world.browser.get(f"{world.site_url}/{path}")


def open_link_in_new_tab(link):
    """
    Opens the link in a new tab, waits for the page to load, closes the tab
    """
    original_window = world.browser.current_window_handle
    world.browser.switch_to.new_window("tab")
    world.browser.get(link)
    wait_for_first_section()
    world.browser.close()
    world.browser.switch_to.window(original_window)
