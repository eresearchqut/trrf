import django
import logging

logger = logging.getLogger(__name__)

django.setup()


def force_password_change():
    from registry.groups.models import CustomUser
    logger.info("Forcing password change for all users")
    count = CustomUser.objects.update(force_password_change=True)
    logger.info(f"Updated {count} users")


if __name__ == '__main__':
    force_password_change()
