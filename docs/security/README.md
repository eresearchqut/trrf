# TRRF Security

## Views

TRRF views must conform to the following conventions.

Once you have ensured your view meets the requirements outlined below, add its url pattern name to the whitelist in [url_whitelist.py](../../rdrf/rdrf/security/url_whitelist.py).

## Publicly accessible views should be whitelisted for django-stronghold

django-stronghold forces all views to require login by default.

Add views that should be publicly accessible in `settings.STRONGHOLD_PUBLIC_URLS` and `settings.STRONGHOLD_PUBLIC_NAMED_URLS`

Because TRRF uses django-stronghold, you should not use `@login_required` or `LoginRequiredMixin`

Note that django-stronghold provides limited security in registries in which patients can register or with varying levels of staff-member permissions.


## Views with varying levels of restricted access should use the appropriate mixins or decorators

For superusers (admins):

- `@superuser_required`
- `SuperuserRequiredMixin`

For staff members:

- `@staff_member_required`
- `StaffMemberRequiredMixin`

## Views used to access patient data should verify that the user has permission

For complicated views, sophisticated access controls may need to be designed.
However, there are some simple conventions that all views should use:

### When retrieving an object using a parameter from a url, use `get_object_or_404`

```
    def get(self, request, registry):
        registry = get_object_or_404(Registry, code=registry_code)
        ...
```

### When verifying whether a patient is accessing their own data (not another patient's), use `get_object_or_permission_denied` and `security_check_user_patient`

```
    def get(self, request, registry, patient):
        ...
        patient_model = get_object_or_permission_denied(Patient, pk=patient)
        security_check_user_patient(self.user, patient_model)
        ...
```

This raises a `PermissionDenied` exception if the user is not found, or if the user is found but doesn't match the request user

## When adding a non-core feature to TRRF, it should be explicitly gated behind a `RegistryFeature`

Add the feature to the list of [registry features](../../rdrf/rdrf/helpers/registry_features.py):

```
    class RegistryFeatures:
        ...
        NEW_FEATURE = "new_feature"
```

In the view, check whether the feature is enabled in this registry:

```
    def get(self, request, registry, patient):
        ...
        if not registry_model.has_feature(RegistryFeatures.NEW_FEATURE):
            raise PermissionDenied
        ...
```

## Any Content Security Policy changes are kept to a minimum

Any Content Security Policy (CSP) changes should only be applied to specific views where those policies are required.

Use django-csp's `@csp_update` decorator to append additional rules like so:

```
   @csp_update(SCRIPT_SRC=["https://cdn.example.com/"], IMG_SRC=["https://cdn.example.com/images"])
```

Any Global CSP updates can be applied in `settings`:

```
    CSP_DEFAULT_SRC = ["'self'"]
    CSP_OBJECT_SRC = ["'none'"]
    ...
```

For more information about how to use django-csp, refer to the [documentation](https://django-csp.readthedocs.io/en/latest/).