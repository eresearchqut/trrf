#!/usr/bin/env python

import argparse
import sys

import django

django.setup()

from registry.groups.models import CustomUser  # noqa: E402

DESCRIPTION = """
Force users to change their password on next login.

Without any arguments it forces ALL users to change their password on next login.
"""


USAGE = """
Usage examples:

* Force password change for ALL users:

$ force_password_change.py

* Force password change for the admin and bobby@example.com users:

$ force_password_change.py --users admin bobby@example.com

* Force password change for ALL users but admin and clinical:

$ force_password_change.py --except admin bobby@example.com
"""


parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=DESCRIPTION,
    epilog=USAGE,
)
parser.add_argument(
    "--users",
    type=str,
    nargs="*",
    metavar="username",
    help="Usernames of users who will be forced to change their password",
)
parser.add_argument(
    "--except",
    type=str,
    nargs="*",
    dest="except_users",
    metavar="username",
    help="Usernames to exclude - ALL users BUT these will be forced to change their password",
)
parser.add_argument(
    "--verbosity", "-v", action="count", default=0, help="Verbosity level"
)


def force_password_change(args):
    print_message = message_printer(args.verbosity)
    if args.users and args.except_users:
        print("You can't specify both --users AND --except.", file=sys.stderr)
        sys.exit(1)

    if args.users:
        users = CustomUser.objects.filter(username__in=args.users)
    elif args.except_users:
        users = CustomUser.objects.exclude(username__in=args.except_users)
    else:
        users = CustomUser.objects.all()

    user_count = users.count()
    print_message(
        f"Forcing password change for {user_count} users", verbosity=1
    )
    not_forced = [u for u in users.filter(force_password_change=False)]
    updated_count = CustomUser.objects.filter(
        pk__in=(u.pk for u in not_forced)
    ).update(force_password_change=True)
    if updated_count < user_count:
        print_message(
            f"Updated {updated_count} of {user_count} users ({user_count - updated_count} were already set up correctly)."
        )
    else:
        print_message(f"Updated {updated_count} users.")
    if not_forced:
        print_message("Updated users:", verbosity=3)
        print_message("\n".join(u.username for u in not_forced), verbosity=3)


def message_printer(requested_verbosity):
    def print_message(msg, verbosity=1):
        if verbosity <= requested_verbosity:
            print(msg)

    return print_message


if __name__ == "__main__":
    force_password_change(parser.parse_args())
