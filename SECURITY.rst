TRRF Security
#############

Views
*****

TRRF views must conform to the following conventions.

Once you have ensured your view meets the requirements outlined below, add its url pattern name to the whitelist in `rdrf/rdrf/checks/url_whitelist.txt <rdrf/rdrf/checks/url_whitelist.txt>`_.

Publicly accessible views should be whitelisted for django-stronghold
=====================================================================
django-stronghold forces all views to require login by default.

Add views that should be publicly accessible in :code:`settings.STRONGHOLD_PUBLIC_URLS` and :code:`settings.STRONGHOLD_PUBLIC_NAMED_URLS`

Because TRRF uses django-stronghold, you should not use :code:`@login_required` or :code:`LoginRequiredMixin`

Note that django-stronghold provides limited security in registries in which patients can register or with varying levels of staff-member permissions.


Views with varying levels of restricted access should use the appropriate mixins or decorators
==============================================================================================

For superusers (admins):

- :code:`@superuser_required`
- :code:`SuperuserRequiredMixin`

For staff members:

- :code:`@staff_member_required`
- :code:`StaffMemberRequiredMixin`

Views used to access patient data should verify that the user has permission
=============================================================================

For complicated views, sophisticated access controls may need to be designed.
However, there are some simple conventions that all views should use:

When retrieving an object using a parameter from a url, use :code:`get_object_or_404`
--------------------------------------------------------------------------------------

.. code-block:: python

    def get(self, request, registry):
        registry = get_object_or_404(Registry, code=registry_code)
        ...

When verifying whether a patient is accessing their own data (not another patient's), use :code:`get_object_or_permission_denied` and :code:`security_check_user_patient`
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

.. code-block:: python

    def get(self, request, registry, patient):
        ...
        patient_model = get_object_or_permission_denied(Patient, pk=patient)
        security_check_user_patient(self.user, patient_model)
        ...

This raises a :code:`PermissionDenied` exception if the user is not found, or if the user is found but doesn't match the request user

When adding a non-core feature to TRRF, it should be explicitly gated behind a :code:`RegistryFeature`
======================================================================================================

Add the feature to the list of `registry features <rdrf/rdrf/helpers/registry_features.py>`_:

.. code-block:: python

    class RegistryFeatures:
        ...
        NEW_FEATURE = "new_feature"

In the view, check whether the feature is enabled in this registry:

.. code-block:: python

    def get(self, request, registry, patient):
        ...
        if not registry_model.has_feature(RegistryFeatures.NEW_FEATURE):
            raise PermissionDenied
        ...

Any Content Security Policy changes are kept to a minimum
=========================================================

Any Content Security Policy (CSP) changes should only be applied to specific views where those policies are required.

Use django-csp's :code:`@csp_update` decorator to append additional rules like so:

.. code-block:: python

   @csp_update(SCRIPT_SRC=["https://cdn.example.com/", IMG_SRC=["https://cdn.example.com/images"])

Any Global CSP updates can be applied in :code:`settings`:

.. code-block:: python

    CSP_DEFAULT_SRC = ["'self'"]
    CSP_OBJECT_SRC = ["'none'"]
    ...

For more information about how to use django-csp, refer to the `documentation <https://django-csp.readthedocs.io/en/latest/>`_.

Security mechanisms catalog
***************************

Plugins
=======
- **django-csp**: Add Content-Security-Policy headers to responses.
- **django-stronghold**: Require login for all views by default.
- **django-two-factor-auth**: Add two-factor authentication functionality.
- **django-useraudit**: User auditing utilities. Record login events, disable users, etc.

Middleware
==========

Custom middleware
-----------------
- **LaxSameSiteCookieMiddleware**: Use 'Lax' SameSite cookies rather than 'Strict' for some urls.
- **NoCacheMiddleware**: Disable browser-side view caching.
- **UserSentryMiddleware**: Enforce password-change and two-factor authentication settings.

Django middleware
-----------------
- **SessionMiddleware**
- **AuthenticationMiddleware**
- **CsrfViewMiddleware**
- **SecurityMiddleware**

Plugin middleware
-----------------
- **CSPMiddleware**
- **OTPMiddleware**
- **LoginRequiredMiddleware**

Mixins
======

Custom mixins
---------------
Use UserPassesTestMixin to block requests on dispatch that don't match condition:

- **SuperuserRequiredMixin**
- **StaffMemberRequiredMixin**
- **ReportAccessMixin**

Django
----------
- **PermissionsMixin**

Explorer
--------
- **AccessCheckMixin**: Verify that user has access to a given query.

Patient verification
--------------------
- **VerificationSecurityMixin**: Verify relevant permissions for user and registry.

Decorators
==========
- **csrf_exempt**: Mark a view as being exempt from the CSRF view protection.
- **never_cache**: Add headers that stop view from being cached.
- **patient_questionnaire_access**: Verify user can access questionnaires.
- **superuser_required**: Check if user is superuser.
- **staff_member_required**: Check if user is staff member.

Django
------
- **sensitive_post_parameters**: Indicate which params in POST request are sensitive (can be hidden in logs etc.)

Plugins
-------
- **csp_update**: Update CSP configuration for a given view.

Functions
=========
- **security_check_user_patient**: Check if request user matches patient id.
- **get_object_or_404**: Find model object by primary key, or raise 404.

Properties
==========

CustomUser
----------
- **is_patient**
- **is_parent**
- **is_carrier**
- **is_carer**
- **is_clinician**
- **is_working_group_staff**

Fields
======

CustomUser
----------

- **is_superuser**
- **groups**
- **user_permissions**
