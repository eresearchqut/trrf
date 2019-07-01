import json
import logging

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _

from registration.backends.default.views import RegistrationView

from rdrf.workflows.registration import get_registration_workflow
from rdrf.models.definition.models import Registry
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.helpers.utils import get_preferred_languages

from .lookup_views import validate_recaptcha

logger = logging.getLogger(__name__)


class RdrfRegistrationView(RegistrationView):

    registry_code = None
    registration_class = None

    def load_registration_class(self, user, request, form):
        from django.conf import settings
        if hasattr(settings, "REGISTRATION_CLASS") and not self.registration_class:
            from django.utils.module_loading import import_string
            registration_class = import_string(settings.REGISTRATION_CLASS)
            self.registration_class = registration_class(user, request, form)

    def dispatch(self, request, *args, **kwargs):
        self.registry_code = kwargs['registry_code']
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        logger.debug("RdrfRegistrationView get")
        self.registry_code = kwargs['registry_code']
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        self.load_registration_class(None, request, form)
        token = request.GET.get("t", None)
        if token:
            logger.debug("token = %s" % token)
            workflow = get_registration_workflow(token)
            if workflow:
                logger.debug("workflow found")
                request.session["token"] = token
                self.template_name = workflow.get_template()
            else:
                logger.debug("no workflow")
        else:
            workflow = self.registration_class.get_registration_workflow()
            self.template_name = workflow.get_template()

        context = self.get_context_data(form=form)
        context["is_mobile"] = request.user_agent.is_mobile
        if workflow:
            context["username"] = workflow.username
            context["first_name"] = workflow.first_name
            context["last_name"] = workflow.last_name

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        token = request.session.get("token", None)
        logger.debug("token = %s" % token)
        form_class = self.get_form_class()
        logger.debug("form class = %s" % form_class)
        form = self.get_form(form_class)
        self.load_registration_class(None, request, form)
        workflow = get_registration_workflow(token) or self.registration_class.get_registration_workflow()
        logger.debug("workflow = %s" % workflow)
        self.template_name = workflow.get_template()
        response_value = request.POST['g-recaptcha-response']
        resp_json = json.loads(validate_recaptcha(response_value).content)
        if not resp_json.get('success', False):
            form.add_error(None, _("Invalid re-captcha value !"))
            return self.form_invalid(form)

        if form.is_valid():
            logger.debug("RdrfRegistrationView post form valid")
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(RdrfRegistrationView, self).get_context_data(**kwargs)
        context['registry_code'] = self.registry_code
        context["preferred_languages"] = get_preferred_languages()
        return context

    def form_valid(self, form):
        # this is only for user validation
        # if any validation errors occur server side
        # on related object creation in signal handler occur
        # we roll back here
        failure_url = reverse("registration_failed")
        username = None
        with transaction.atomic():
            try:
                new_user = self.register(form)
                logger.debug("RdrfRegistrationView form_valid - new_user registered")
                if self.registration_class:
                    self.registration_class.set_user(new_user)
                    self.registration_class.process()
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
        return registry.has_feature(RegistryFeatures.REGISTRATION)
