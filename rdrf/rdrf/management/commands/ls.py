import os

from django.core.management import load_command_class, find_commands, color_style
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'List the available custom commands with a description and their args'

    def handle(self, **options):
        command_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        style = color_style()

        for command_name in find_commands(command_path):
            command = load_command_class("rdrf", command_name)
            print(f"{style.SUCCESS(command_name)}: {command.help}")
