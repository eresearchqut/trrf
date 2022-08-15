from selenium.webdriver.common.by import By


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
        return self

    def submit(self):
        self._get_element(self.SUBMIT_BUTTON).click()


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
        message_row = self._get_message_rows()[index]
        return {
            'to': message_row.find_element(By.CLASS_NAME, 'messageTo').text,
            'from': message_row.find_element(By.CLASS_NAME, 'messageFrom').text,
            'subject': message_row.find_element(By.CLASS_NAME, 'messageSubject').text,
            'body': message_row.find_element(By.CLASS_NAME, 'messageBody').text
        }

    def is_displayed(self):
        return self.browser.find_element(*self.PAGE_TITLE).text == "Mail Outbox"


def get_site_links(site_url, registry_code):
    def _make_url(resource):
        return f'{"/".join([site_url, resource])}'

    return {key: _make_url(resource)
            for key, resource in {'registration': f'{registry_code}/register',
                                  'login': 'account/login?next=/router/',
                                  'logout': 'logout?next=/router/',
                                  'mailbox': 'mail/outbox',
                                  'mailbox_empty': 'mail/outbox/empty'}.items()}
