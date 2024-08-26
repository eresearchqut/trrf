import os
from argparse import ArgumentParser

from django.core.management import (
    color_style,
    find_commands,
    load_command_class,
)
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "List the available custom commands with a description and their args"
    )

    def handle(self, **options):
        command_path = os.path.dirname(
            os.path.dirname(os.path.realpath(__file__))
        )

        style = color_style()

        for command_name in find_commands(command_path):
            command = load_command_class("rdrf", command_name)
            print(f"{style.SUCCESS(command_name)}: {command.help}")

            if options.get("verbosity", 1) > 1:
                parser = ArgumentParser(command_name)
                command.add_arguments(parser)
                parser.print_help()
                print()
