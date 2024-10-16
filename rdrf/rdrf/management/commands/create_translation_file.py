import json
import re
import sys

import yaml
from django.core.management import BaseCommand
from django.core.management.base import CommandError

sys.stdout = open(1, "w", encoding="utf-8", closefd=False)
explanation = """
Usage:

This command extracts English strings used in RDRF pages, forms and CDEs and creates a "Django message 'po' file.

CDE labels and values translation: Extract strings from a yaml file and pump out to standard output:

> django-admin create_translation_file --yaml_file=<yaml file path> [--system_po_file <app level po file> ]  > <output po file>

NB. --system_po_file is the path the "standard po file" created by running django makemessages. By passing it
in the script avoids creating duplicate message ids  which prevent compilation.

"""


class Command(BaseCommand):
    help = "Creates a translation po file for a given registry"

    def add_arguments(self, parser):
        parser.add_argument(
            "--yaml_file",
            action="store",
            dest="yaml_file",
            default=None,
            help="Registry Yaml file name",
        )

        parser.add_argument(
            "--system_po_file",
            action="store",
            dest="system_po_file",
            default=None,
            help="System po file",
        )

    def _usage(self):
        print(explanation)

    def handle(self, *args, **options):
        file_name = options.get("yaml_file", None)
        system_po_file = options.get("system_po_file", None)
        self.msgids = set([])
        self.number = re.compile(r"^\d+$")

        if not file_name:
            self._usage()
            raise CommandError("Must provide yaml file")

        if system_po_file:
            # splurp in existing messages in the system file so we don't dupe
            # when we cat this file to it
            self._load_system_messages(system_po_file)

        self._emit_strings_from_yaml(file_name)

    def _load_system_messages(self, system_po_file):
        message_pattern = re.compile('^msgid "(.*)"$')
        with open(system_po_file, encoding="utf-8") as spo:
            for line in spo.readlines():
                line = line.strip()
                m = message_pattern.match(line)
                if m:
                    msgid = m.groups(1)[0]
                    self.msgids.add(msgid)

    def _load_yaml_file(self, file_name):
        with open(file_name, encoding="utf-8") as f:
            try:
                self.data = yaml.load(f, Loader=yaml.FullLoader)
            except Exception as ex:
                print("could not load yaml file %s: %s" % (file_name, ex))

                sys.exit(1)

    def _emit_strings_from_yaml(self, file_name):
        self._load_yaml_file(file_name)

        for comment, msgid in self._get_strings_for_translation():
            self._print(comment, msgid)

    def _emit_strings_from_registry(self, registry_model):
        pass

    def _print(self, comment, message_string):
        if not message_string:
            return

        # multiple blank lines
        if not message_string.strip():
            return

        if message_string in self.msgids:
            return
        else:
            self.msgids.add(message_string)

        if self.number.match(message_string):
            return

        if comment:
            print("# %s" % comment)

        if "\n" in message_string:
            # probably wrong but compiler fails
            # if there are multilined messages
            # message_string = message_string.replace('\n',' ')
            lines = [
                line.replace('"', '\\"') for line in message_string.split("\n")
            ]
            first_line = lines[0]
            lines = lines[1:]

            print('msgid "%s"' % first_line)
            for line in lines:
                print('"\\n%s"' % line)
            print('msgstr ""')
            return

        # again we need to escape somwhow
        if '"' in message_string:
            message_string = message_string.replace('"', '\\"')

        print('msgid "%s"' % message_string)
        print('msgstr ""')
        print()

    def _get_strings_for_translation(self):
        yield from self._yield_registry_level_strings()
        yield from self._yield_form_strings()
        yield from self._yield_context_form_group_strings()
        yield from self._yield_consent_strings()
        yield from self._yield_menu_items()
        yield from self._yield_permission_strings()
        yield from self._yield_next_of_kin_relationship_strings()
        yield from self._yield_misc_strings()
        yield from self._yield_dashboard_strings()

    def _yield_registry_level_strings(self):
        yield None, self.data["name"]
        yield None, self.data["splash_screen"]

    def _yield_form_strings(self):
        if self.data is None:
            raise Exception("No data?")

        for form_dict in self.data["forms"]:
            yield None, form_dict["display_name"]

            yield None, form_dict["header"]
            yield from self._yield_section_strings(form_dict)

    def _yield_context_form_group_strings(self):
        if self.data is None:
            raise Exception("No data?")

        for cfg in self.data["context_form_groups"]:
            yield None, cfg["name"]

    def _yield_section_strings(self, form_dict):
        for section_dict in form_dict["sections"]:
            comment = None
            display_name = section_dict["display_name"]
            header = section_dict.get("header")
            yield comment, display_name
            yield comment, header
            yield from self._yield_cde_strings(section_dict)

    def _yield_cde_strings(self, section_dict):
        for cde_code in section_dict["elements"]:
            cde_dict = self._get_cde_dict(cde_code)
            if cde_dict is None:
                continue

            cde_label = cde_dict["name"]

            instruction_text = cde_dict["instructions"]

            comment = None

            yield comment, cde_label
            yield comment, instruction_text

            yield from self._yield_cde_settings_strings(cde_dict)
            yield from self._yield_pvg_strings(cde_dict)

    def _get_cde_dict(self, cde_code):
        for cde_dict in self.data["cdes"]:
            if cde_dict["code"] == cde_code:
                return cde_dict

    @staticmethod
    def _yield_cde_settings_strings(cde_dict):
        widget_name = cde_dict["widget_name"]
        widget_settings = json.loads(cde_dict["widget_settings"] or "null")

        if widget_name == "SliderWidget":
            yield "Slider left", widget_settings["left_label"]
            yield "Slider right", widget_settings["right_label"]

    def _yield_consent_strings(self):
        for consent_section_dict in self.data["consent_sections"]:
            yield None, consent_section_dict["section_label"]
            yield None, consent_section_dict["information_text"]
            for question_dict in consent_section_dict["questions"]:
                yield None, question_dict["question_label"]
                yield None, question_dict["instructions"]

    def _yield_pvg_strings(self, cde_dict):
        # we need to emit display values of drop down lists
        pvg_code = cde_dict["pv_group"]
        if pvg_code:
            # range exists
            pvg_dict = self._get_pvg_dict(pvg_code)
            if pvg_dict is None:
                comment = "missing pvg"
                yield comment, "???"
                return
            for value_dict in pvg_dict["values"]:
                display_value = value_dict["value"]

                comment = None
                yield comment, display_value

    def _get_pvg_dict(self, pvg_code):
        for pvg_dict in self.data["pvgs"]:
            if pvg_dict["code"] == pvg_code:
                return pvg_dict

    def _get_field(self, thing, field):
        if isinstance(thing, dict):
            return thing[field]
        else:
            # assume a model
            return getattr(thing, field)

    def _yield_menu_items(self):
        # consent
        registry_name = self.data["name"]

        msgid = "Consents (%s)" % registry_name
        yield None, msgid

        # permission matrix
        msgid = "Permissions (%s)" % registry_name
        yield None, msgid

    def _yield_misc_strings(self):
        # Couldn't  get these strings to extract for some reason
        yield None, "Next of kin country"
        yield None, "Next of kin state"
        yield None, "Permission Matrix for %(registry)s"
        yield None, "Welcome"

    def _yield_permission_strings(self):
        from django.contrib.auth.models import Permission

        # These aren't in the yaml but depend on the configured auth groups
        for column_heading in [
            "Permission",
            "Clinical Staff",
            "Parents",
            "Patients",
            "Working Group Curators",
        ]:
            yield None, column_heading

        for permission_object in Permission.objects.all():
            yield None, permission_object.name

    def _yield_next_of_kin_relationship_strings(self):
        for relationship in self.data.get("next_of_kin_relationships", []):
            yield None, relationship

    def _yield_dashboard_strings(self):
        for dashboard_dict in self.data.get("registry_dashboards", []):
            for widget_dict in dashboard_dict.get("widgets", []):
                yield None, widget_dict["title"]
                yield None, widget_dict["free_text"]

                for demo_dict in widget_dict.get("demographics", []):
                    yield None, demo_dict["label"]

                for link_dict in widget_dict.get("links", []):
                    yield None, link_dict["label"]

                for cde_dict in widget_dict.get("cdes", []):
                    yield None, cde_dict["label"]
