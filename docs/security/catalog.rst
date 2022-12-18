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
- **NoneSameSiteCookieMiddleware**: Use 'None' SameSite cookies rather than 'Strict' for some urls.
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

Decorators
==========
- **csrf_exempt**: Mark a view as being exempt from the CSRF view protection.
- **never_cache**: Add headers that stop view from being cached.
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
