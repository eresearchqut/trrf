import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import text_to_be_present_in_element_value
from selenium.webdriver.support.wait import WebDriverWait

from rdrf.testing.behaviour.features.utils import TEST_WAIT


class BasePage:
    SITE_MENU = {'menu': (By.LINK_TEXT, 'Menu'),
                 'settings': (By.LINK_TEXT, 'Settings'),
                 'user': (By.ID, 'authMenuDropdown')}

    def __init__(self, browser):
        self.browser = browser

    def _get_element(self, locator):
        return self.browser.find_element(*locator)

    def _set_element(self, locator, value, clear_existing=True):
        element = self._get_element(locator)

        if clear_existing:
            element.clear()

        element.send_keys(value)

        return self

    def open_menu(self, menu_key):
        element = self._get_element(self.SITE_MENU.get(menu_key))
        element.click()

    def get_user_menu_text(self):
        return self._get_element(self.SITE_MENU.get('user')).text

    def get_page_error(self):
        return self._get_element((By.XPATH, '//div[@class="alert alert-danger"][1]')).text


class LoginPage(BasePage):
    USERNAME_ELEMENT = (By.ID, 'id_auth-username')
    PASSWORD_ELEMENT = (By.ID, 'id_auth-password')
    NEXT_BUTTON = (By.CSS_SELECTOR, 'button[type="submit"]')

    def set_username(self, username):
        return self._set_element(self.USERNAME_ELEMENT, username, clear_existing=True)

    def set_password(self, password):
        return self._set_element(self.PASSWORD_ELEMENT, password, clear_existing=True)

    def submit(self):
        self.browser.find_element(*self.NEXT_BUTTON).click()


class RequestPasswordResetPage(BasePage):
    EMAIL_ELEMENT = (By.ID, 'id_email')
    SUBMIT_BUTTON = (By.CSS_SELECTOR, 'input[type="submit"]')

    def set_email(self, email):
        return self._set_element(self.EMAIL_ELEMENT, email)

    def submit(self):
        self.browser.find_element(*self.SUBMIT_BUTTON).click()


class ResetPasswordPage(BasePage):
    NEW_PWD_ELEMENT = (By.ID, 'id_new_password1')
    CONFIRM_PWD_ELEMENT = (By.ID, 'id_new_password2')
    SUBMIT_BUTTON = (By.CSS_SELECTOR, 'input[type="submit"]')

    def set_new_password(self, password):
        return self._set_element(self.NEW_PWD_ELEMENT, password)

    def set_confirm_password(self, password):
        return self._set_element(self.CONFIRM_PWD_ELEMENT, password)

    def submit(self):
        self.browser.find_element(*self.SUBMIT_BUTTON).click()


class TwoFactorLoginTokenPage(BasePage):
    TOKEN_ELEMENT = (By.ID, 'id_token-otp_token')
    SUBMIT_BUTTON = (By.XPATH, '//button[text()="Next"]')

    def set_token(self, token):
        self._set_element(self.TOKEN_ELEMENT, token)
        # Hoping this will stop errors where the next instruction happens before the keys are finished sending
        WebDriverWait(self.browser, TEST_WAIT).until(
            text_to_be_present_in_element_value(self.TOKEN_ELEMENT, token)
        )
        return self

    def submit(self):
        self._get_element(self.SUBMIT_BUTTON).submit()


class TwoFactorTokenGeneratorPage(TwoFactorLoginTokenPage):
    TIME_BASED_KEY_ELEMENT = (By.CSS_SELECTOR, '.card-body .lead')
    TOKEN_ELEMENT = (By.ID, 'id_generator-token')

    def get_time_based_key(self):
        return self._get_element(self.TIME_BASED_KEY_ELEMENT).text


class DisableTwoFactorAuthPage(BasePage):
    CONFIRM_CHECKBOX = (By.CSS_SELECTOR, 'input[name="understand"]')
    DISABLE_BUTTON = (By.XPATH, '//button[text()="Disable"]')

    def check_confirm(self):
        self._get_element(self.CONFIRM_CHECKBOX).click()
        return self

    def disable(self):
        self._get_element(self.DISABLE_BUTTON).click()


class MailOutboxPage(BasePage):
    PAGE_TITLE = (By.TAG_NAME, 'h1')
    MESSAGES_TABLE = (By.ID, 'id_messages')

    def _get_message_rows(self):
        messages_table = self.browser.find_element(*self.MESSAGES_TABLE)
        return messages_table.find_elements(By.CSS_SELECTOR, 'tbody tr')

    def get_message_count(self):
        return len(self._get_message_rows())

    def get_message(self, index):
        def _get_links(web_element):
            # Pull out links from the email, regardless of whether they are semantic links <a href=.../> or plain text
            links = [link.get_attribute('href') for link in web_element.find_elements(By.TAG_NAME, 'a')]
            text_link_search = re.search(r'https?://\S*', web_element.text)
            if text_link_search:
                links.append(text_link_search[0])
            return links

        message_row = self._get_message_rows()[index]
        message_body = message_row.find_element(By.CLASS_NAME, 'messageBody')

        return {
            'to': message_row.find_element(By.CLASS_NAME, 'messageTo').text,
            'from': message_row.find_element(By.CLASS_NAME, 'messageFrom').text,
            'subject': message_row.find_element(By.CLASS_NAME, 'messageSubject').text,
            'body': message_body.text,
            'links': _get_links(message_body)
        }

    def is_displayed(self):
        return self.browser.find_element(*self.PAGE_TITLE).text == "Mail Outbox"


class ChangeEmailAddressPage(BasePage):

    CURRENT_EMAIL = (By.ID, 'id_current_email')
    NEW_EMAIL = (By.ID, 'id_new_email')
    CONFIRM_NEW_EMAIL = (By.ID, 'id_new_email2')
    CURRENT_PASSWORD = (By.ID, 'id_current_password')
    SUBMIT_BTN = (By.XPATH, '//button[text()="Initiate change of email address"]')

    CURRENT_REQUEST = (By.ID, 'id_current_request')

    def get_current_request(self):
        current_request = self._get_element(self.CURRENT_REQUEST)

        return {
            'email': current_request.find_element(By.ID, 'id_current_request_email').text,
            'date': current_request.find_element(By.ID, 'id_current_request_date').text,
            'status': current_request.find_element(By.ID, 'id_current_request_status').text
        }

    def get_current_email(self):
        return self._get_element(self.CURRENT_EMAIL).text

    def set_new_email(self, new_email):
        self._set_element(self.NEW_EMAIL, new_email)
        return self

    def set_confirm_new_email(self, confirm_email):
        self._set_element(self.CONFIRM_NEW_EMAIL, confirm_email)
        return self

    def set_current_password(self, current_password):
        self._set_element(self.CURRENT_PASSWORD, current_password)
        return self

    def submit(self):
        self._get_element(self.SUBMIT_BTN).click()


def get_site_links(site_url, registry_code):
    def _make_url(resource):
        return f'{"/".join([site_url, resource])}'

    return {key: _make_url(resource)
            for key, resource in {'registration': f'{registry_code}/register',
                                  'login': 'account/login?next=/router/',
                                  'logout': 'logout?next=/router/',
                                  'mailbox': 'mail/outbox',
                                  'mailbox_empty': 'mail/outbox/empty'}.items()}
