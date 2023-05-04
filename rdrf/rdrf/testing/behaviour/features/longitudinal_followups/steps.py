from datetime import datetime, timedelta

from aloe import step, world
from nose.tools import assert_equal
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from rdrf.testing.behaviour.features.longitudinal_followups.utils import go_to_url, open_link_in_new_tab, get_email, \
    EMAIL_SELECTOR
from rdrf.testing.behaviour.features.steps import click_patient_listing
from rdrf.testing.behaviour.features.utils import TEST_WAIT


@step(r'open the patient (\w+) in the (\w+) registry')
def open_patient(_step, patient_name, registry_code):
    go_to_url(f"{registry_code}/patientslisting")
    WebDriverWait(world.browser, TEST_WAIT).until_not(
        ec.presence_of_element_located((By.ID, "patients_table_processing"))
    )
    click_patient_listing(_step, patient_name)


@step(r'see (\d+) emails?')
def check_mail(_step, count):
    go_to_url("mail/outbox")
    sent_emails = len(world.browser.find_elements_by_css_selector(EMAIL_SELECTOR))
    assert_equal(sent_emails, int(count))


@step(r'open (\d+) links? in email (\d+)')
def open_links(_step, count, email):
    links = get_email(email)[:-2]
    assert_equal(len(links), int(count))
    for link in links:
        open_link_in_new_tab(link.get_attribute("href"))


@step(r'unsubscribe in email (\d+)')
def unsubscribe(_step, email):
    unsubscribe_link = get_email(email)[-2]
    unsubscribe_link.click()
    WebDriverWait(world.browser, TEST_WAIT).until(ec.presence_of_element_located((By.CLASS_NAME, "alert-success")))


@step('empty the mail')
def empty_mail(_step):
    world.browser.get(f"{world.site_url}/mail/outbox/empty")


@step(r'send emails (\d+) hours? later')
def send_emails(_step, hours):
    now = (datetime.now() + timedelta(hours=int(hours))).timestamp()
    go_to_url(f"mail/send_longitudinal_followups?now={int(now)}")
