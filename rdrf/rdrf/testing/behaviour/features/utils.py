import logging
import os
import subprocess

from aloe import world
from selenium.webdriver.common.by import By

TEST_WAIT = int(os.environ.get("TEST_WAIT") or "10")

logger = logging.getLogger(__name__)


def utils_path():
    return os.path.dirname(os.path.realpath(__file__))


def exported_data_path():
    return os.path.join(utils_path(), "exported_data")


def stellar_config_path():
    return os.path.join(utils_path(), "stellar")


def reset_password_change_date():
    logger.info("")
    from django.utils import timezone
    from registry.groups.models import CustomUser

    CustomUser.objects.update(password_change_date=timezone.now())


def reset_last_login_date():
    logger.info("")
    from django.utils import timezone
    from registry.groups.models import CustomUser

    CustomUser.objects.update(last_login=timezone.now())


def subprocess_logging(command):
    logger.info(f"command: {command}")
    p = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = p.communicate()
    if stdout:
        logger.info(str(stdout))
    if stderr:
        logger.error(str(stderr))
    if p.returncode != 0:
        logger.error("Return code {0}".format(p.returncode))
    return (p.returncode, str(stdout), str(stderr))


def reset_database_connection():
    from django import db

    db.connection.close()


def have_snapshot(export_name):
    code, out, err = stellar_multidb(["stellar", "list"])
    return out.find(export_name) != -1


def stellar_multidb(args):
    """Use stellar across multiple databases
    A hack that searches for stellar configs in multiple dirs to allow for snapshot/restore in a multidb setup
    """
    logger.info(args)
    cwd = os.getcwd()
    rval_code = 0
    rval_out = ""
    rval_err = ""

    for work_dir in [
        some_dir[0] for some_dir in os.walk(stellar_config_path())
    ]:
        # ignore dirs that don't have a stellar config
        if not os.path.isfile(os.path.join(work_dir, "stellar.yaml")):
            continue

        # cd and invoke stellar
        os.chdir(work_dir)
        code, out, err = subprocess_logging(args)

        # some calling methods want to parse the output so, lets preserve that
        rval_out += out
        rval_err += err
        if rval_code == 0:
            rval_code = code

    os.chdir(cwd)

    return (rval_code, rval_out, rval_err)


def remove_snapshot(snapshot_name):
    logger.info(snapshot_name)
    stellar_multidb(["stellar", "remove", snapshot_name])


def save_snapshot(snapshot_name):
    logger.info(snapshot_name)
    if have_snapshot(snapshot_name):
        remove_snapshot(snapshot_name)
    stellar_multidb(["stellar", "snapshot", snapshot_name])


def save_minimal_snapshot():
    # delete everything so we can import clean later
    django_flush()
    django_flush(["--database", "clinical"])
    django_migrate()
    django_migrate(["--database", "clinical"])
    save_snapshot("minimal")


def restore_minimal_snapshot():
    restore_snapshot("minimal")


def restore_snapshot(snapshot_name):
    logger.info(snapshot_name)
    stellar_multidb(["stellar", "restore", snapshot_name])


def load_export(export_name):
    django_init_cache()

    """
    To save time cache the stellar snapshots ( one per export file )
    Create / reset on first use
    """
    if have_snapshot(export_name):
        restore_snapshot(export_name)
    else:
        django_import(export_name)
        save_snapshot(export_name)

    reset_database_connection()
    django_init_default_site()
    show_stats(export_name)


def django_import(export_name):
    django_admin(
        ["import", "{0}/{1}".format(exported_data_path(), export_name)],
        fail_on_error=True,
    )


def django_init_dev():
    django_admin(["init", "DEV"])


def django_init_cache():
    django_admin(["createcachetable"])


def django_init_default_site():
    domain = os.environ["TRRF_SITE_DOMAIN"]
    name = os.environ["TRRF_SITE_NAME"]
    args = ["--name", name, "--domain", domain]
    django_admin(["set_default_site"] + args)


def django_flush(args=None):
    if args is None:
        args = []
    django_admin(["flush", "--noinput"] + args)


def django_migrate(args=None):
    if args is None:
        args = []
    django_admin(["migrate", "--noinput"] + args)


def django_admin(args, fail_on_error=False):
    logger.info(args)
    return_code, _, _ = subprocess_logging(["django-admin"] + args)

    if fail_on_error and return_code != 0:
        raise Exception(
            "'%s' command failed with error code %d"
            % (" ".join(["django-admin"] + args), return_code)
        )


def show_stats(export_name):
    """
    show some stats after import
    """
    from registry.patients.models import Patient

    from rdrf.models.definition.models import Registry

    logger.info("Stats after import of export file %s:" % export_name)
    for r in Registry.objects.all():
        logger.info("\tregistry = %s" % r)

    for p in Patient.objects.all():
        logger.info("\t\tPatient %s" % p)


def click(element):
    from selenium.common.exceptions import WebDriverException

    try:
        element.click()
    except WebDriverException:
        # Make sure the element is accessible before clicking it
        scroll_element_into_view(element, True)
        element.click()


def scroll_element_into_view(element, execute_pause=False):
    world.browser.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});", element
    )
    if execute_pause:
        pause(2)


def pause(seconds):
    import time

    n = int(seconds)
    time.sleep(n)


def debug_links():
    for link in world.browser.find_elements(by=By.XPATH, value="//a"):
        logger.debug(
            "link {0} {1}".format(link.text, link.get_attribute("href"))
        )


def scroll_to_y(y):
    world.browser.execute_script("window.scrollTo(0, %s)" % y)


def scroll_to(element):
    loc = element.location_once_scrolled_into_view
    y = loc["y"]
    scroll_to_y(y)
    return y


def scroll_to_multisection_cde(section, cde, item=1):
    # item 1 means the 1st block of cdes in the multisection
    print(
        "Attempting to scroll to section %s cde %s item %s"
        % (section, cde, item)
    )
    formset_string = "-%s-" % (int(item) - 1)
    print("formset_string = %s" % formset_string)
    xpath = "//div[@class='card-header' and contains(., '%s')]" % section
    panel_heading = world.browser.find_element(
        by=By.XPATH, value=xpath
    ).find_element(by=By.XPATH, value="..")
    if is_section_collapsed(
        world.browser.find_element(by=By.XPATH, value=xpath)
    ):
        click(panel_heading)
    default_panel = world.browser.find_element(
        by=By.XPATH, value=xpath
    ).find_element(by=By.XPATH, value="..")
    label_expression = ".//label[contains(., '%s')]" % cde

    for label_element in default_panel.find_elements(
        by=By.XPATH, value=label_expression
    ):
        print("found a label element for cde %s" % cde)
        input_div = label_element.find_element(
            by=By.XPATH, value=".//following-sibling::div"
        )
        # NB. We avoid matching against the clear checkbox for an uploaded file cde
        try:
            input_element = input_div.find_element(
                by=By.XPATH,
                value=".//input[contains(@id, '%s') and not(contains(@id, '-clear_id'))]"
                % formset_string,
            )
            scroll_to(input_element)
            print(
                "found input element: id = %s"
                % input_element.get_attribute("id")
            )
            return input_element
        except BaseException:
            continue

    raise Exception(
        "Could not locate multsection %s cde %s item %s" % (section, cde, item)
    )


def scroll_to_cde(section, cde, item=None):
    """
    navigate to a given section and cde, scrolling to make the field visible
    return the input element
    """
    input_element = None
    section_div_heading = world.browser.find_element(
        by=By.XPATH,
        value=".//div[@class='card-header'][contains(., '%s') and not(contains(.,'__prefix__'))]"
        % section,
    )
    if is_section_collapsed(section_div_heading):
        click(section_div_heading)

    section_div = section_div_heading.find_element(by=By.XPATH, value="..")

    label_expression = ".//label[contains(., '%s')]" % cde
    label_element = section_div.find_element(
        by=By.XPATH, value=label_expression
    )
    input_div = label_element.find_element(
        by=By.XPATH, value=".//following-sibling::div"
    )
    input_elements = input_div.find_elements(by=By.XPATH, value=".//input")

    if len(input_elements) >= 0:
        if not item:
            input_element = input_elements[0]
        else:
            formset_string = "-%s-" % (int(item) - 1)
            for ie in input_elements:
                input_id = ie.get_attribute("id")
                if formset_string in input_id:
                    input_element = ie
                    break
            raise Exception(
                "Could not locate section %s input %s item %s"
                % (section, cde, item)
            )

    if not input_element:
        raise Exception("could not locate element to scroll to")
    input_id = input_element.get_attribute("id")
    if "__prefix__" in input_id:
        # hack to avoid this error
        input_id = input_id.replace("__prefix__", "0")
        input_element = world.browser.find_element_by_id(input_id)
        if not input_element:
            raise Exception("could not locate input with id %s" % input_id)

    scroll_to(input_element)
    return input_element


def is_section_collapsed(section):
    section_body = section.find_element(
        by=By.XPATH,
        value=".//following-sibling::div[contains(@class, 'card-body')]",
    )
    css_class = section_body.get_attribute("class")
    if css_class is None:
        return False
    css_classes = css_class.split(" ")
    return "collapse" in css_classes and "show" not in css_classes


def wait_for_first_section():
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait

    WebDriverWait(world.browser, TEST_WAIT).until(
        ec.visibility_of_element_located(
            (By.CSS_SELECTOR, ".section-available")
        )
    )
