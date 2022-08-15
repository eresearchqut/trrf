import logging
import re
from collections import OrderedDict

from aloe import step, world
from aloe.tools import guess_types
from nose.tools import assert_equal, assert_true
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from rdrf.models.definition.models import Registry
from rdrf.testing.behaviour.features.auth import utils
from rdrf.testing.behaviour.features.auth.page import LoginPage, RequestPasswordResetPage, MailOutboxPage, \
    ResetPasswordPage, BasePage, TwoFactorTokenGeneratorPage, TwoFactorLoginTokenPage, DisableTwoFactorAuthPage, \
    get_site_links
from rdrf.testing.behaviour.features.steps import click_link
from rdrf.testing.behaviour.features.terrain import TEST_WAIT
from rdrf.testing.behaviour.features.utils import scroll_to_y
from registry.groups.models import CustomUser

logger = logging.getLogger(__name__)


@step('expecting to receive email')
def setup_email(_step):
    go_to_url(_step, 'mailbox_empty')
    assert_true(MailOutboxPage(world.browser).is_displayed())


@step('the registry is closed to registrations')
def close_registration(_step):
    utils.close_registration(world.registry)


@step('the registry is open to registrations')
def open_registration(_step):
    utils.open_registration(world.registry)


@step('go to the "([^"]+)" page')
def go_to_url(_step, page_name):
    page_url = get_site_links(world.site_url, world.registry_code).get(page_name)
    world.browser.get(page_url)


@step('try to register as a user called "([^"]+)" using the email address "([^"]+)" and the password "([^"]+)"')
def patient_self_registration(_step, client_name, email_address, password):
    go_to_url(_step, 'registration')

    client_first_name = client_name.split()[0]
    client_last_name = client_name.split()[1]

    world.user_first_name = client_first_name
    world.user_last_name = str.upper(client_last_name)

    # Plain text field parameters
    params = OrderedDict([
        ('id_username', email_address),
        ('id_password1', password),
        ('id_password2', password),
        ('id_first_name', client_first_name),
        ('id_surname', client_last_name),
        ('id_date_of_birth', '1980-09-01'),
    ])

    # Populate plain text fields
    for key, value in params.items():
        world.browser.find_element_by_id(key).send_keys(value + Keys.TAB)

    # Select the gender radio button
    # 1 - Male, 2 - Female, 3 - Indeterminate
    world.browser.find_element_by_css_selector("input[name='gender'][value='1']").click()

    captcha_iframe_element = world.browser.find_element(
        by=By.XPATH,
        value="//iframe[@role='presentation']"
    )

    world.browser.switch_to.frame(captcha_iframe_element)
    scroll_to_y(500)

    world.browser.find_element_by_id('recaptcha-anchor').send_keys(Keys.SPACE)

    world.browser.switch_to.default_content()

    submit_button_locator = (By.ID, 'registration-submit')

    WebDriverWait(world.browser, TEST_WAIT).until(
        expected_conditions.element_to_be_clickable(submit_button_locator)
    )

    world.browser.find_element(*submit_button_locator).click()


@step('login with username "([^"]+)" and password "([^"]+)"')
def login(_step, username, password):
    LoginPage(world.browser).set_username(username)\
                            .set_password(password)\
                            .submit()


@step('reauthenticate with username "([^"]+)" and password "([^"]+)"')
def reauthenticate(_step, username, password):
    open_option_from_menu(_step, 'Logout', 'user')
    login(_step, username, password)


@step('am logged in successfully')
def assert_is_logged_in(self):
    assert_equal(BasePage(world.browser).get_user_menu_text(), f'{world.user_first_name} {world.user_last_name}')


@step('user "([^"]+) ([^"]+)" with username "([^"]+)" and password "([^"]+)"')
def create_user(_step, first_name, last_name, username, password):
    user = CustomUser.objects.create_user(username=username,
                                          email=username,
                                          password=password,
                                          first_name=first_name,
                                          last_name=last_name,
                                          is_active=True)
    registry = Registry.objects.get(code=world.registry_code)
    user.registry.set([registry])
    world.user_first_name = first_name
    world.user_last_name = last_name


@step('request to reset my password for "([^"]+)"')
def request_password_reset(_step, username):
    RequestPasswordResetPage(world.browser).set_email(username).submit()


@step('have received an email:')
def assert_email_received(_step):
    go_to_url(_step, 'mailbox')
    mail_outbox_page = MailOutboxPage(world.browser)
    assert_equal(mail_outbox_page.get_message_count(), 1)

    for i, expected_message in enumerate(guess_types(_step.hashes)):
        actual_message = mail_outbox_page.get_message(i)
        assert_equal(actual_message['to'], expected_message['To'])
        assert_equal(actual_message['from'], expected_message['From'])
        assert_equal(actual_message['subject'], expected_message['Subject'])

        world.email_link = re.search(r'https?://\S*', actual_message['body'])[0]


@step('visit the provided link to .*')
def visit_provided_link(_step):
    world.browser.get(re.sub(r'https', 'http', world.email_link))


@step('set my new password to "([^"]+)"')
def set_new_password(_step, new_password):
    ResetPasswordPage(world.browser).set_new_password(new_password)\
                                    .set_confirm_password(new_password)\
                                    .submit()


@step('choose "([^"]+)" from the "([^"]+)" menu')
def open_option_from_menu(_step, option, menu):
    BasePage(world.browser).open_menu(menu)
    click_link(_step, option)


@step('"([^"]+)" image is displayed')
def assert_is_image_displayed(_step, image_alt):
    image = world.browser.find_element_by_css_selector(f'img[alt="{image_alt}"]')
    assert_true(image.is_displayed())


@step('time based key is displayed')
def assert_is_time_based_key_displayed(_step):
    time_based_key = TwoFactorTokenGeneratorPage(world.browser).get_time_based_key()
    world.key = time_based_key
    assert_true(len(time_based_key) > 0)


@step('enter my first generated OTP token')
def setup_initial_otp_token(_step):
    utils.set_otp_token(TwoFactorTokenGeneratorPage(world.browser), world.key)


@step('enter my generated OTP token')
def enter_otp_token(_step):
    utils.set_otp_token(TwoFactorLoginTokenPage(world.browser), world.key)


@step('confirm to disable two-factor auth')
def confirm_disable_2fa(_step):
    DisableTwoFactorAuthPage(world.browser).check_confirm().disable()
