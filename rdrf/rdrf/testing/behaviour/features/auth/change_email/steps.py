from aloe import step, world
from aloe.tools import guess_types
from nose.tools import assert_equal, assert_in

from rdrf.testing.behaviour.features.auth.page import ChangeEmailAddressPage


@step('my current email is displayed "(.*)"')
def assert_current_username(_step, expected_current_email):
    actual_current_email = ChangeEmailAddressPage(
        world.browser
    ).get_current_email()
    assert_equal(actual_current_email, expected_current_email)


@step('enter a new email address "(.*)"')
def set_new_email_address(_step, new_email_address):
    ChangeEmailAddressPage(world.browser).set_new_email(new_email_address)


@step('confirm the new email address as "(.*)"')
def set_confirm_email_address(_step, confirm_email_address):
    ChangeEmailAddressPage(world.browser).set_confirm_new_email(
        confirm_email_address
    )


@step('enter a password "(.*)"')
def set_password(_step, password):
    ChangeEmailAddressPage(world.browser).set_current_password(password)


@step('get an error "(.*)"')
def assert_error(_step, error_text):
    messages = ChangeEmailAddressPage(world.browser).get_page_error()
    assert_in(error_text, messages)


@step("submit the form")
def submit_the_form(_step):
    ChangeEmailAddressPage(world.browser).submit()


@step(
    'my "Current Email Change Request" is displayed, with the following details:'
)
def assert_current_email_request(_step):
    current_request = ChangeEmailAddressPage(
        world.browser
    ).get_current_request()
    for i, expected_message in enumerate(guess_types(_step.hashes)):
        assert_equal(
            current_request["email"],
            expected_message["Requested email address"],
        )
        assert_equal(current_request["status"], expected_message["Status"])
