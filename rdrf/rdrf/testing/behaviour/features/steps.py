import logging
import time

from aloe import step, world
from aloe.registry import STEP_REGISTRY
from aloe_webdriver.webdriver import contains_content
from nose.tools import assert_equal, assert_true
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from . import utils
from .terrain import TEST_WAIT

logger = logging.getLogger(__name__)

# Clearing all the aloe step definitions before we register our own.
STEP_REGISTRY.clear()


@step("I try to log in")
def try_to_login(step):
    world.browser.get(world.site_url + "login?next=/router/")


@step('I should be logged in as an Angelman user called "([^"]+)"')
def login_as_angelman_user(step, user_name):
    world.expected_login_message = (
        "Welcome {0} to the Angelman Registry".format(user_name)
    )


@step('I should be at the welcome page and see a message which says "([^"]+)"')
def angelman_user_logged_in(step, welcome_message):
    login_message = world.browser.find_element_by_tag_name("h4").text

    # Ensure that the user sees the expected page after successfully logging in
    assert world.expected_login_message in login_message


@step("the administrator manually activates the user")
def try_to_manually_activate_new_user(step):
    world.browser.get(
        world.site_url + "admin/registration/registrationprofile/"
    )
    world.browser.find_element_by_id("action-toggle").send_keys(Keys.SPACE)

    world.browser.find_element(
        by=By.XPATH,
        value="//select[@name='action']/option[text()='Activate users']",
    ).click()
    world.browser.find_element(
        by=By.XPATH, value="//*[@title='Run the selected action']"
    ).click()


@step("the user should be activated")
def check_user_activated(step):
    # Ensure that the user has been successfully activated by checking for the green tick icon
    assert not (
        world.browser.find_elements_by_css_selector(
            'img[src$="/static/admin/img/icon-yes.svg"].ng-hide'
        )
    )

    # Log out as the admin user
    world.browser.get(world.site_url + "logout?next=/router/")


@step("I try to surf the site...")
def sleep_for_admin(step):
    """
    This is just a helper function to prevent the browser from closing.
    """
    time.sleep(200000)


@step("development fixtures")
def load_development_fixtures(step):
    utils.django_init_dev()


@step('export "(.*)"')
def load_export(step, export_name):
    utils.load_export(export_name)
    utils.reset_password_change_date()
    utils.reset_last_login_date()


@step('should see "([^"]+)"$')
def should_see(step, text):
    assert_true(contains_content(world.browser, text))


@step('click "(.*)"')
def click_link(step, link_text):
    link = world.browser.find_element(by=By.PARTIAL_LINK_TEXT, value=link_text)
    utils.click(link)


@step('should see a link to "(.*)"')
def should_see_link_to(step, link_text):
    return world.browser.find_element(
        by=By.XPATH, value='//a[contains(., "%s")]' % link_text
    )


@step('should NOT see a link to "(.*)"')
def should_not_see_link_to(step, link_text):
    links = world.browser.find_elements(
        by=By.XPATH, value='//a[contains(., "%s")]' % link_text
    )
    assert_equal(len(links), 0)


@step('press the "(.*)" button')
def press_button(step, button_text):
    button = world.browser.find_element(
        by=By.XPATH, value='//button[contains(., "%s")]' % button_text
    )
    utils.click(button)


@step('I click "(.*)" on patientlisting')
def click_patient_listing(step, patient_name):
    link = world.browser.find_element(
        by=By.PARTIAL_LINK_TEXT, value=patient_name
    )
    utils.click(link)


@step('I click on "(.*)" in "(.*)" group in sidebar')
def click_sidebar_group_item(step, item_name, group_name):
    # E.g. And I click "Clinical Data" in "Main" group in sidebar
    sidebar = world.browser.find_element_by_id("sidebar")
    form_group_panel = sidebar.find_element(
        by=By.XPATH,
        value='//div[@class="card-header"][contains(., "%s")]' % group_name,
    ).find_element(by=By.XPATH, value="..")
    form_link = form_group_panel.find_element(
        by=By.PARTIAL_LINK_TEXT, value=item_name
    )
    utils.click(form_link)


@step('I press "(.*)" button in "(.*)" group in sidebar')
def click_button_sidebar_group(step, button_name, group_name):
    sidebar = world.browser.find_element_by_id("sidebar")
    form_group_panel = sidebar.find_element(
        by=By.XPATH,
        value='//div[@class="card-header"][contains(., "%s")]' % group_name,
    ).find_element(by=By.XPATH, value="..")
    button = form_group_panel.find_element(
        by=By.XPATH, value='.//a[@class="btn btn-info btn-xs float-end"]'
    )
    utils.click(button)


@step('I enter value "(.*)" for form "(.*)" section "(.*)" cde "(.*)"')
def enter_cde_on_form(step, cde_value, form, section, cde):
    # And I enter "02-08-2016" for  section "" cde "Consent date"
    # location_is(step, form)  # sanity check

    utils.wait_for_first_section()

    form_block = world.browser.find_element_by_id("main-form")
    section_div_heading = form_block.find_element(
        by=By.XPATH,
        value=".//div[@class='card-header'][contains(., '%s')]" % section,
    )
    section_div = section_div_heading.find_element(by=By.XPATH, value="..")
    if utils.is_section_collapsed(section_div):
        utils.click(section_div_heading)

    label_expression = ".//label[contains(., '%s')]" % cde

    for label_element in section_div.find_elements(
        by=By.XPATH, value=label_expression
    ):
        input_div = label_element.find_element(
            by=By.XPATH, value=".//following-sibling::div"
        )
        try:
            input_element = input_div.find_element(
                by=By.XPATH, value=".//input"
            )
            input_element.send_keys(cde_value)
            return
        except BaseException:
            pass

    raise Exception("could not find cde %s" % cde)


@step(
    r'I enter value "(.*)" for form "(.*)" multisection "(.*)" cde "(.*)" in item (\d+)'
)
def enter_cde_on_form_multisection(step, cde_value, form, section, cde, item):
    formset_number = int(item) - 1
    formset_string = "-%s-" % formset_number

    def correct_item(input_element):
        input_id = input_element.get_attribute("id")
        return formset_string in input_id

    location_is(step, form)  # sanity check

    utils.wait_for_first_section()

    form_block = world.browser.find_element_by_id("main-form")
    section_div_heading = form_block.find_element(
        by=By.XPATH,
        value=".//div[@class='card-header'][contains(., '%s')]" % section,
    )
    if utils.is_section_collapsed(section_div_heading):
        utils.click(section_div_heading)
    section_div = section_div_heading.find_element(by=By.XPATH, value="..")

    label_expression = ".//label[contains(., '%s')]" % cde

    for label_element in section_div.find_elements(
        by=By.XPATH, value=label_expression
    ):
        input_div = label_element.find_element(
            by=By.XPATH, value=".//following-sibling::div"
        )
        try:
            input_element = input_div.find_element(
                by=By.XPATH, value=".//input"
            )
            if not correct_item(input_element):
                continue
            input_element.send_keys(cde_value)
            input_id = input_element.get_attribute("id")
            print("input id %s sent keys '%s'" % (input_id, cde_value))

            return
        except BaseException:
            pass

    raise Exception("could not find cde %s" % cde)


@step('I click the "(.*)" button')
def click_submit_button(step, value):
    """click submit button with given value
    This enables us to click on button, input or a elements that look like buttons.
    """
    submit_element = world.browser.find_element(
        by=By.XPATH,
        value="//*[@id='submit-btn' and @value='{0}']".format(value),
    )
    utils.click(submit_element)


@step('error message is "(.*)"')
def error_message_is(step, error_message):
    # <div class="alert alert-alert alert-danger">Patient Fred SMITH not saved due to validation errors</div>
    world.browser.find_element(
        by=By.XPATH,
        value='//div[@class="alert alert-alert alert-danger" and contains(text(), "%s")]'
        % error_message,
    )


@step('location is "(.*)"')
def location_is(step, location_name):
    sidebar = world.browser.find_element_by_id("sidebar")
    location_parts = location_name.split("/")
    if len(location_parts) == 1:
        sidebar.find_element(
            by=By.XPATH,
            value='//div[@class="card-body"][contains(., "%s")]'
            % location_name,
        )
    else:
        sidebar.find_element(
            by=By.XPATH,
            value='//div[@class="card-header"][contains(., "%s")]'
            % location_parts[0],
        )
        sidebar.find_element(
            by=By.XPATH,
            value='//div[@class="card-body"][contains(., "%s")]'
            % location_parts[1],
        )


@step('When I click Module "(.*)" for patient "(.*)" on patientlisting')
def click_module_dropdown_in_patient_listing(step, module_name, patient_name):
    # module_name is "Main/Clinical Form" if we indicate context group  or
    # "FormName" is just Modules list ( no groups)
    if "/" in module_name:
        button_caption, form_name = module_name.split("/")
    else:
        button_caption, form_name = "Modules", module_name

    patients_table = world.browser.find_element_by_id("patients_table")

    patient_row = patients_table.find_element(
        by=By.XPATH,
        value="//tr[td[1]//text()[contains(., '%s')]]" % patient_name,
    )

    form_group_button = patient_row.find_element(
        by=By.XPATH, value='//button[contains(., "%s")]' % button_caption
    )

    utils.click(form_group_button)
    form_link = form_group_button.find_element(
        by=By.XPATH, value=".."
    ).find_element(by=By.PARTIAL_LINK_TEXT, value=form_name)
    utils.click(form_link)


@step("press the navigate back button")
def press_back_button(step):
    button = world.browser.find_element_by_css_selector("a.previous-form")
    utils.click(button)


@step("press the navigate forward button")
def press_forward_button(step):
    button = world.browser.find_element_by_css_selector("a.next-form")
    utils.click(button)


@step('select "(.*)" from "(.*)"')
def select_from_list(step, option, dropdown_label_or_id):
    select_id = dropdown_label_or_id
    if dropdown_label_or_id.startswith("#"):
        select_id = dropdown_label_or_id.lstrip("#")
    else:
        label = world.browser.find_element(
            by=By.XPATH,
            value='//label[contains(., "%s")]' % dropdown_label_or_id,
        )
        select_id = label.get_attribute("for")
    option = world.browser.find_element(
        by=By.XPATH,
        value='//select[@id="%s"]/option[contains(., "%s")]'
        % (select_id, option),
    )
    utils.click(option)


@step('option "(.*)" from "(.*)" should be selected')
def option_should_be_selected(step, option, dropdown_label):
    label = world.browser.find_element(
        by=By.XPATH, value='//label[contains(., "%s")]' % dropdown_label
    )
    option = world.browser.find_element(
        by=By.XPATH,
        value='//select[@id="%s"]/option[contains(., "%s")]'
        % (label.get_attribute("for"), option),
    )
    assert_true(option.get_attribute("selected"))


@step('fill in "(.*)" with "(.*)"')
def fill_in_textfield(step, textfield_label, text):
    label = world.browser.find_element(
        by=By.XPATH, value='//label[contains(., "%s")]' % textfield_label
    )
    textfield = world.browser.find_element(
        by=By.XPATH, value='//input[@id="%s"]' % label.get_attribute("for")
    )
    textfield.send_keys(text)


@step('fill "(.*)" with "(.*)" in MultiSection "(.*)" index "(.*)"')
def fill_in_textfield2(step, label, keys, multi, index):
    multisection = multi + "-" + index
    label = world.browser.find_element(
        by=By.XPATH,
        value='//label[contains(@for, "{0}") and contains(., "{1}")]'.format(
            multisection, label
        ),
    )
    textfield = world.browser.find_element(
        by=By.XPATH, value='//input[@id="%s"]' % label.get_attribute("for")
    )
    textfield.send_keys(keys)


@step('value of "(.*)" should be "(.*)"')
def value_is(step, textfield_label, expected_value):
    label = world.browser.find_element(
        by=By.XPATH, value='//label[contains(., "%s")]' % textfield_label
    )
    textfield = world.browser.find_element(
        by=By.XPATH, value='//input[@id="%s"]' % label.get_attribute("for")
    )
    assert_equal(textfield.get_attribute("value"), expected_value)


@step('form value of section "(.*)" cde "(.*)" should be "(.*)"')
def value_is2(step, section, cde, expected_value):
    utils.wait_for_first_section()

    form_block = world.browser.find_element_by_id("main-form")
    section_div_heading = form_block.find_element(
        by=By.XPATH,
        value=".//div[@class='card-header'][contains(., '%s')]" % section,
    )
    if utils.is_section_collapsed(section_div_heading):
        utils.click(section_div_heading)
    section_div = section_div_heading.find_element(by=By.XPATH, value="..")
    label_expression = ".//label[contains(., '%s')]" % cde
    label_element = section_div.find_element(
        by=By.XPATH, value=label_expression
    )
    input_div = label_element.find_element(
        by=By.XPATH, value=".//following-sibling::div"
    )
    input_element = input_div.find_element(by=By.XPATH, value=".//input")
    assert_equal(input_element.get_attribute("value"), expected_value)


@step('check "(.*)"')
def check_checkbox(step, checkbox_label):
    label = world.browser.find_element(
        by=By.XPATH, value='//label[contains(., "%s")]' % checkbox_label
    )
    checkbox = world.browser.find_element(
        by=By.XPATH, value='//input[@id="%s"]' % label.get_attribute("for")
    )
    if not checkbox.is_selected():
        utils.click(checkbox)


@step("Sign consent")
def sign_consent(step):
    signature_div = world.browser.find_element_by_id("signature")
    utils.click(signature_div)


@step('the "(.*)" checkbox should be checked')
def checkbox_should_be_checked(step, checkbox_label):
    label = world.browser.find_element(
        by=By.XPATH, value='//label[contains(., "%s")]' % checkbox_label
    )
    checkbox = world.browser.find_element(
        by=By.XPATH, value='//input[@id="%s"]' % label.get_attribute("for")
    )
    assert_true(checkbox.is_selected())


@step('a registry named "(.*)" with code "(.*)"')
def create_registry_with_code(step, name, registry_code):
    world.registry = name
    world.registry_code = registry_code


@step('a registry named "(.*)"')
def create_registry(step, name):
    world.registry = name


@step('a user named "(.*)"')
def create_user(step, username):
    world.user = username


@step('a patient named "(.*)"')
def set_patient(step, name):
    world.patient = name


@step("navigate to the patient's page")
def goto_patient(step):
    click_link(step, world.patient)


@step('the page header should be "(.*)"')
def the_page_header_should_be(step, header):
    sidebar = world.browser.find_element_by_id("sidebar")
    panel_body = sidebar.find_element(
        by=By.XPATH, value='//div[@class="card-body"]'
    )
    panel_body.find_element(
        by=By.XPATH,
        value='//a[contains(., "%s")][@class="selected-link"]' % header,
    )


@step("I am logged in as (.*)")
def login_as_role(step, role):
    # Could map from role to user later if required

    world.user = role  # ?
    go_to_registry(step, world.registry)
    login_as_user(step, role, role)


@step('log in as "(.*)" with "(.*)" password')
def login_as_user(step, username, password):
    utils.click(world.browser.find_element_by_link_text("Log in"))
    username_field = world.browser.find_element(
        by=By.XPATH, value='.//input[@name="auth-username"]'
    )
    username_field.send_keys(username)
    password_field = world.browser.find_element(
        by=By.XPATH, value='.//input[@name="auth-password"]'
    )
    password_field.send_keys(password)
    password_field.submit()


@step("should be logged in")
def should_be_logged_in(step):
    user_link = world.browser.find_element(
        by=By.PARTIAL_LINK_TEXT, value=world.user
    )
    utils.click(user_link)
    world.browser.find_element_by_link_text("Logout")


@step("should be on the login page")
def should_be_on_the_login_page(step):
    world.browser.find_element(
        by=By.XPATH,
        value='.//div[@class="card-header"][text()[contains(.,"Login")]]',
    )
    world.browser.find_element(
        by=By.XPATH, value='.//label[text()[contains(.,"Email Address")]]'
    )
    world.browser.find_element(
        by=By.XPATH, value='.//label[text()[contains(.,"Password")]]'
    )


@step("click the User Dropdown Menu")
def click_user_menu(step):
    click_link(step, world.user)


@step('the progress indicator should be "(.*)"')
def the_progress_indicator_should_be(step, percentage):
    progress_bar = world.browser.find_element_by_css_selector(
        ".progress .progress-bar"
    )

    logger.info(progress_bar.text.strip())
    logger.info(percentage)

    assert_equal(progress_bar.text.strip(), percentage)


@step("I go home")
def go_home(step):
    world.browser.get(world.site_url)


@step('go to the registry "(.*)"')
def go_to_registry(step, name):
    world.browser.get(world.site_url)
    utils.click(
        world.browser.find_element_by_link_text("Registries on this site")
    )
    utils.click(world.browser.find_element(by=By.PARTIAL_LINK_TEXT, value=name))


@step('go to page "(.*)"')
def go_to_page(setp, page_ref):
    if page_ref.startswith("/"):
        page_ref = page_ref[1:]
    url = world.site_url + page_ref
    world.browser.get(url)


@step("navigate away then back")
def refresh_page(step):
    current_url = world.browser.current_url
    world.browser.get(world.site_url)
    world.browser.get(current_url)


@step("accept the alert")
def accept_alert(step):
    Alert(world.browser).accept()


@step('When I click "(.*)" in sidebar')
def sidebar_click(step, sidebar_link_text):
    utils.click(world.browser.find_element_by_link_text(sidebar_link_text))


@step("I click Cancel")
def click_cancel(step):
    link = world.browser.find_element(
        by=By.XPATH,
        value='//a[@class="btn btn-danger" and contains(., "Cancel")]',
    )
    utils.click(link)


@step('enter value "(.*)" for "(.*)"')
def enter_value_for_named_element(step, value, name):
    # try to find place holders, labels etc
    for element_type in ["placeholder"]:
        xpath_expression = '//input[@placeholder="{0}"]'.format(name)
        input_element = world.browser.find_element(
            by=By.XPATH, value=xpath_expression
        )
        if input_element:
            input_element.send_keys(value)
            return
    raise Exception("can't find element '%s'" % name)


@step('click radio button value "(.*)" for section "(.*)" cde "(.*)"')
def click_radio_button(step, value, section, cde):
    # NB. this is actually just clicking the first radio at the moment
    # and ignores the value
    section_div_heading = world.browser.find_element(
        by=By.XPATH,
        value=".//div[@class='card-header'][contains(., '%s')]" % section,
    )
    if utils.is_section_collapsed(section_div_heading):
        utils.click(section_div_heading)
    section_div = section_div_heading.find_element(by=By.XPATH, value="..")
    label_expression = ".//label[contains(., '%s')]" % cde
    label_element = section_div.find_element(
        by=By.XPATH, value=label_expression
    )
    input_div = label_element.find_element(
        by=By.XPATH, value=".//following-sibling::div"
    )
    # must be getting first ??
    input_element = input_div.find_element(by=By.XPATH, value=".//input")
    input_element.click()


@step(r'upload file "(.*)" for multisection "(.*)" cde "(.*)" in item (\d+)')
def upload_file(step, upload_filename, section, cde, item):
    utils.wait_for_first_section()

    input_element = utils.scroll_to_multisection_cde(section, cde, item)
    input_element.send_keys(upload_filename)


@step('upload file "(.*)" for section "(.*)" cde "(.*)"')
def upload_file2(step, upload_filename, section, cde):
    input_element = utils.scroll_to_element(step, section, cde)
    input_element.send_keys(upload_filename)


@step('scroll to section "(.*)" cde "(.*)"')
def scroll_to_element(step, section, cde):
    input_element = utils.scroll_to_cde(section, cde)
    if not input_element:
        raise Exception(
            "could not scroll to section %s cde %s" % (section, cde)
        )
    return input_element


@step('should be able to download "(.*)"')
def should_be_able_to_download(step, download_name):
    import re

    link_pattern = re.compile(r".*\/uploads\/\d+$")
    download_link_element = world.browser.find_element_by_link_text(
        download_name
    )
    if not download_link_element:
        raise Exception("Could not locate download link %s" % download_name)

    download_link_href = download_link_element.get_attribute("href")
    if not link_pattern.match(download_link_href):
        raise Exception(
            "%s does not look like a download link: href= %s"
            % download_link_href
        )


@step('should not be able to download "(.*)"')
def should_not_be_able_download(step, download_name):
    can_download = False
    try:
        should_be_able_to_download(step, download_name)
        can_download = True
    except BaseException:
        pass

    if can_download:
        raise Exception("should NOT be able to download %s" % download_name)
    else:
        print("%s is not downloadable as expected" % download_name)


@step('History for form "(.*)" section "(.*)" cde "(.*)" shows "(.*)"')
def check_history_popup(step, form, section, cde, history_values_csv):
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait

    history_values = history_values_csv.split(",")
    form_block = world.browser.find_element_by_id("main-form")
    section_div_heading = form_block.find_element(
        by=By.XPATH,
        value=".//div[@class='card-header'][contains(., '%s')]" % section,
    )

    section_div = section_div_heading.find_element(by=By.XPATH, value="..")
    label_expression = ".//label[contains(., '%s')]" % cde
    label_element = section_div.find_element(
        by=By.XPATH, value=label_expression
    )
    history_widget = label_element.find_element(
        by=By.XPATH,
        value=".//a[@onclick='rdrf_click_form_field_history(event, this)']",
    )

    utils.scroll_element_into_view(label_element, True)

    # Hover over the label element to make history link visible
    ActionChains(world.browser).move_to_element(label_element).click(
        history_widget
    ).perform()

    WebDriverWait(world.browser, TEST_WAIT).until(
        ec.visibility_of_element_located(
            (By.XPATH, ".//a[@href='#cde-history-table']")
        )
    )

    def find_cell(historical_value):
        element = world.browser.find_element(
            by=By.XPATH, value='//td[@data-value="%s"]' % historical_value
        )
        if element is None:
            raise Exception(
                "Can't locate history value '%s'" % historical_value
            )

    for historical_value in history_values:
        find_cell(historical_value)


@step('check the clear checkbox for multisection "(.*)" cde "(.*)" file "(.*)"')
def clear_file_upload(step, section, cde, download_name):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait

    download_link_element = world.browser.find_element_by_link_text(
        download_name
    )
    clear_checkbox_path = ".//following-sibling::input[@type='checkbox']"
    WebDriverWait(world.browser, TEST_WAIT).until(
        ec.element_to_be_clickable((By.XPATH, clear_checkbox_path))
    )

    clear_checkbox = download_link_element.find_element(
        by=By.XPATH, value=clear_checkbox_path
    )
    clear_checkbox.click()


@step('when I scroll to section "(.*)"')
def scroll_to_section(step, section):
    from selenium.webdriver.common.action_chains import ActionChains

    mover = ActionChains(world.browser)
    print("scrolling to section %s" % section)
    section_xpath = (
        ".//div[@class='panel panel-default' and contains(.,'%s') and not(contains(., '__prefix__')) and not(contains(.,'View previous values'))]"
        % section
    )
    section_element = world.browser.find_element(
        by=By.XPATH, value=section_xpath
    )
    if not section_element:
        raise Exception("could not find section %s" % section)
    y = utils.scroll_to(section_element)
    mover.move_to_element(section_element)
    print("scrolled to section %s y = %s" % (section, y))


@step('I click the add button for multisection "(.*)"')
def add_multisection_item(step, section):
    xpath = (
        ".//div[@class='card-header' and contains(.,'%s') and not(contains(., '__prefix__')) and not(contains(.,'View previous values'))]"
        % section
    )
    div = world.browser.find_element(by=By.XPATH, value=xpath)
    utils.scroll_element_into_view(div, True)
    add_link_xpath = """.//a[starts-with(@onclick,"add_form(")]"""
    add_link = div.find_element(by=By.XPATH, value=add_link_xpath)
    add_link.click()
    # sometimes the next cde send keys was going to the wrong item
    wait_n_seconds(step, 5)


@step(r"I wait (\d+) seconds")
def wait_n_seconds(step, seconds):
    import time

    n = int(seconds)
    time.sleep(n)


@step(r'I mark multisection "(.*)" item (\d+) for deletion')
def mark_item_for_deletion(step, multisection, item):
    formset_string = "-%s-" % (int(item) - 1)
    xpath = "//div[@class='card-header' and contains(., '%s')]" % multisection
    default_panel = world.browser.find_element(
        by=By.XPATH, value=xpath
    ).find_element(by=By.XPATH, value="..")
    # now locate the delete checkbox for the item
    checkbox_xpath = (
        ".//input[@type='checkbox' and contains(@id, '-DELETE') and contains(@id, '%s')]"
        % formset_string
    )
    delete_checkbox = default_panel.find_element(
        by=By.XPATH, value=checkbox_xpath
    )

    if delete_checkbox:
        print(
            "found delete_checkbox for multisection %s item %s"
            % (multisection, item)
        )
    else:
        raise Exception(
            "Could not found delete checkbox for multisection %s item %s"
            % (multisection, item)
        )

    utils.click(delete_checkbox)


@step(r'the value of multisection "(.*)" cde "(.*)" item (\d+) is "(.*)"')
def check_multisection_value(step, multisection, cde, item, expected_value):
    """
    Check the value of an entered field in a multisection
    """
    utils.wait_for_first_section()

    input_element = utils.scroll_to_multisection_cde(multisection, cde, item)
    actual_value = input_element.get_attribute("value")
    error_msg = (
        "Multisection %s cde %s item %s expected value %s - actual value %s"
        % (multisection, cde, item, expected_value, actual_value)
    )

    assert actual_value == expected_value, error_msg


@step(r'I expand the "(.*)" section')
def expand_section(step, section_name):
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait

    utils.wait_for_first_section()

    section_div_heading = world.browser.find_element(
        by=By.XPATH,
        value=".//div[@class='card-header'][contains(., '%s')]" % section_name,
    )

    if utils.is_section_collapsed(section_div_heading):
        utils.click(section_div_heading)

    section_div_body = WebDriverWait(world.browser, TEST_WAIT).until(
        ec.visibility_of(
            section_div_heading.find_element(
                by=By.XPATH,
                value="../div[contains(@class, 'card-body') and contains(@class, 'show')]",
            )
        )
    )
    utils.scroll_element_into_view(section_div_body)
