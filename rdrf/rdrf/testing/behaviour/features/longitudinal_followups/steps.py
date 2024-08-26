from datetime import datetime, timedelta

from aloe import step, world
from nose.tools import assert_equal
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from rdrf.testing.behaviour.features.longitudinal_followups.utils import (
    EMAIL_SELECTOR,
    get_email,
    go_to_url,
    open_link_in_new_tab,
)
from rdrf.testing.behaviour.features.steps import (
    click_button_sidebar_group,
    click_link,
    click_patient_listing,
    click_submit_button,
    enter_cde_on_form,
)
from rdrf.testing.behaviour.features.utils import TEST_WAIT


@step(r'the "(.*)" form in patient "(.*)" is filled out(?: (again))?')
def fill_out_form(step, form_name, patient_name, again=None):
    if again:
        click_link(step, "Menu")
        click_link(step, f"Patient List ({world.registry})")
    click_patient_listing(step, patient_name)
    click_button_sidebar_group(step, "Add", form_name)
    enter_cde_on_form(step, "01-01-2023", form_name, " ", "Date of assessment")
    click_submit_button(step, "Save")


@step(r"(\d+) hour(?:s)? pass(?:es)?")
def pass_time(_step, hours):
    now = (datetime.now() + timedelta(hours=int(hours))).timestamp()
    go_to_url(f"mail/send_longitudinal_followups?now={int(now)}")


@step(r"(\d+) emails? (?:are|is) sent")
def emails_sent(step, count):
    check_mail(step, count)


@step("no emails are sent")
def no_emails_sent(_step):
    check_mail(_step, 0)


@step(r"email (\d+) has (\d+) links?")
def email_has_links(step, email, count):
    links = get_email(email)[:-2]
    assert_equal(len(links), int(count))


@step(r"each link in email (\d+) loads successfully")
def links_load(step, email):
    links = get_email(email)[:-2]
    for link in links:
        open_link_in_new_tab(link.get_attribute("href"))


@step("the mail is emptied")
def empty_mail(_step):
    world.browser.get(f"{world.site_url}/mail/outbox/empty")


@step(r"see (\d+) emails?")
def check_mail(_step, count):
    go_to_url("mail/outbox")
    sent_emails = len(
        world.browser.find_elements_by_css_selector(EMAIL_SELECTOR)
    )
    assert_equal(sent_emails, int(count))


@step(r"unsubscribe in email (\d+)")
def unsubscribe(_step, email):
    unsubscribe_link = get_email(email)[-2]
    unsubscribe_link.click()
    WebDriverWait(world.browser, TEST_WAIT).until(
        ec.presence_of_element_located((By.CLASS_NAME, "alert-success"))
    )
