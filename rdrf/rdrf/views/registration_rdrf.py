import logging

import requests
from csp.decorators import csp_update
from django.conf import settings
from django.contrib.auth import login
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from django.utils.translation.trans_real import parse_accept_lang_header, language_code_re
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView
from registration.backends.default.views import RegistrationView, ActivationView

from rdrf.helpers.utils import get_all_language_codes
from rdrf.models.definition.models import Registry

logger = logging.getLogger(__name__)

registration_csp_script_src = ["https://www.google.com/recaptcha/", "https://www.gstatic.com/recaptcha/"]
registration_csp_frame_src = ["https://www.google.com/recaptcha/"]


class RdrfRegistrationView(RegistrationView):

    registry_code = None
    registration_class = None

    def load_registration_class(self, request, form):
        if hasattr(settings, "REGISTRATION_CLASS"):
            registration_class = import_string(settings.REGISTRATION_CLASS)
            return registration_class(request, form)

    def get_user_requested_language(self):
        # 1. If user has activated a language, this takes precedence as the requested language
        site_language = self.request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if site_language:
            return site_language

        # 2. Otherwise, get the default browser language
        accept = self.request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        for accept_lang, unused in parse_accept_lang_header(accept):
            if accept_lang == '*':
                break

            if not language_code_re.search(accept_lang):
                continue

            try:
                return accept_lang
            except LookupError:
                continue

        # Not expected to get to this point, but if so then use the default language
        return settings.LANGUAGE_CODE

    @csp_update(SCRIPT_SRC=registration_csp_script_src,
                FRAME_SRC=registration_csp_frame_src)
    def dispatch(self, request, *args, **kwargs):
        self.registry_code = kwargs['registry_code']
        form_class = self.get_form_class()
        self.form = self.get_form(form_class)
        self.registration_class = self.load_registration_class(request, self.form)
        self.template_name = self.registration_class.get_template_name()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        languages_dict = get_all_language_codes()
        context = super().get_context_data(**kwargs)
        context['registry_code'] = self.registry_code
        context['preferred_languages'] = [{'code': lang.code, 'name': lang.name} for lang in languages_dict]
        context['preferred_language'] = self.get_user_requested_language()
        context['is_mobile'] = self.request.user_agent.is_mobile
        context['all_language_codes'] = [language.code for language in languages_dict]

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
        response_value = self.request.POST.get('g-recaptcha-response')
        if not response_value:
            return False
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
            logger.debug("RdrfRegistrationView post - redirecting to success url %s" % str(success_url))
            return redirect(to, *args, **kwargs)

    def registration_allowed(self):
        registry = get_object_or_404(Registry, code=self.registry_code)
        if registry.registration_allowed():
            if self.registration_class:
                return self.registration_class.registration_allowed()
            return True
        return False


class EmbeddedRegistrationCompletedView(TemplateView):

    @csp_update(FRAME_ANCESTORS=settings.EMBED_FRAME_ANCESTORS)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class EmbeddedRegistrationView(RdrfRegistrationView):

    @csp_update(SCRIPT_SRC=registration_csp_script_src,
                FRAME_SRC=registration_csp_frame_src,
                FRAME_ANCESTORS=settings.EMBED_FRAME_ANCESTORS)
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)

        # Activate a different language if the language URL parameter has been passed in
        if 'language' in request.GET:
            language_code = request.GET.get('language')

            from django.utils import translation
            translation.activate(language_code or settings.LANGUAGE_CODE)
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language_code)

        return response

    def load_registration_class(self, request, form):
        if hasattr(settings, "REGISTRATION_CLASS_EMBEDDED"):
            registration_class = import_string(settings.REGISTRATION_CLASS_EMBEDDED)
            return registration_class(request, form)
        return super().load_registration_class(request, form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['embedded_view'] = True
        return context

    def get_success_url(self, user=None):
        return 'embedded_registration_complete', {}, {'registry_code': self.registry_code}


class PatientActivationView(ActivationView):
    def get_success_url(self, user):
        if not user.has_usable_password():
            login(self.request, user, 'django.contrib.auth.backends.ModelBackend')
        return f'{reverse("two_factor:login")}?next={reverse("login_router")}?new_activation=True'


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
