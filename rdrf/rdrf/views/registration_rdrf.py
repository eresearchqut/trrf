from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from registration.backends.default.views import RegistrationView
from django.db import transaction
import time
import logging


logger = logging.getLogger(__name__)


class RdrfRegistrationView(RegistrationView):

    registry_code = None

    def get(self, request, *args, **kwargs):
        self.registry_code = kwargs['registry_code']
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(RdrfRegistrationView, self).get_context_data(**kwargs)
        context['registry_code'] = self.registry_code
        context["preferred_languages"] = self._get_preferred_languages()
        return context

    def _get_preferred_languages(self):
        # Registration allows choice of preferred language
        # But we allow different sites to expose different values
        # over time without code change via env --> settings

        # The default list is english only which we don't bother to show
        from rdrf.helpers.utils import get_supported_languages
        languages = get_supported_languages()

        if len(languages) == 1 and languages[0].code == "en":
            return []
        else:
            return languages

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
                username = new_user.username
                success_url = self.get_success_url(new_user)
            except Exception as ex:
                logger.error("Unhandled error in registration for user %s: %s" % (username,
                                                                                  ex))
                return redirect(failure_url)

        try:
            to, args, kwargs = success_url
        except ValueError:
            return redirect(success_url)
        else:
            return redirect(to, *args, **kwargs)
