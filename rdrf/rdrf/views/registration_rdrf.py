import logging
import requests
from csp.decorators import csp_update

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.module_loading import import_string

from registration.backends.default.views import RegistrationView

from rdrf.models.definition.models import Registry
from rdrf.helpers.utils import get_preferred_languages

logger = logging.getLogger(__name__)


class RdrfRegistrationView(RegistrationView):

    registry_code = None
    registration_class = None

    def load_registration_class(self, request, form):
        if hasattr(settings, "REGISTRATION_CLASS"):
            registration_class = import_string(settings.REGISTRATION_CLASS)
            return registration_class(request, form)

    @csp_update(DEFAULT_SRC=("https://www.google.com", "https://www.gstatic.com"))
    def dispatch(self, request, *args, **kwargs):
        self.registry_code = kwargs['registry_code']
        form_class = self.get_form_class()
        self.form = self.get_form(form_class)
        self.registration_class = self.load_registration_class(request, self.form)
        self.template_name = self.registration_class.get_template_name()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registry_code'] = self.registry_code
        context['preferred_languages'] = get_preferred_languages()
        context['is_mobile'] = self.request.user_agent.is_mobile
        return context

    def post(self, request, *args, **kwargs):
        if self.is_form_valid():
            logger.debug("RdrfRegistrationView post form valid")
            return self.form_valid(self.form)
        else:
            return self.form_invalid(self.form)

    def is_form_valid(self):
        if not self.is_recaptcha_valid():
            self.form.add_error(None, _("Please complete the I'm not a robot reCAPTCHA validation and try to Submit again"))
            return False

        return self.form.is_valid()

    def is_recaptcha_valid(self):
        response_value = self.request.POST['g-recaptcha-response']
        resp_data = validate_recaptcha(response_value)
        return resp_data.get('success', False)

    def form_valid(self, form):
        failure_url = reverse("registration_failed")
        username = None
        with transaction.atomic():
            try:
                new_user = self.register(form)
                logger.debug("RdrfRegistrationView form_valid - new_user registered")
                if self.registration_class:
                    self.registration_class.process(new_user)
                username = new_user.username
                success_url = self.get_success_url(new_user)
            except Exception:
                logger.exception("Unhandled error in registration for user %s", username)
                return redirect(failure_url)

        try:
            to, args, kwargs = success_url
        except ValueError:
            logger.debug("RdrfRegistrationView post - redirecting to success url %s" % success_url)
            return redirect(success_url)
        else:
            logger.debug("RdrfRegistrationView post - redirecting to sucess url %s" % str(success_url))
            return redirect(to, *args, **kwargs)

    def registration_allowed(self):
        registry = get_object_or_404(Registry, code=self.registry_code)
        return registry.registration_allowed()


def validate_recaptcha(response_value):
    payload = {"secret": settings.RECAPTCHA_SECRET_KEY, "response": response_value}
    response = requests.post("https://www.google.com/recaptcha/api/siteverify", data=payload)
    try:
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        logger.exception('Re-captcha validation failed')
        return {'success': False}

    if not data.get('success', False):
        logger.info(f'Re-captcha validation failed: \n{data}')

    return data
