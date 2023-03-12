import os
from setuptools import setup, find_packages

package_data = {}
start_dir = os.getcwd()


def add_file_for_package(package, subdir, f):
    full_path = os.path.join(subdir, f)
    # print "%s: %s" % (package, full_path)
    return full_path


packages = ['rdrf',
            'rdrf.account_handling',
            'rdrf.auth',
            'rdrf.context_processors',
            'rdrf.db',
            'rdrf.events',
            'rdrf.forms',
            'rdrf.forms.dynamic',
            'rdrf.forms.fields',
            'rdrf.forms.navigation',
            'rdrf.forms.progress',
            'rdrf.forms.validation',
            'rdrf.forms.widgets',
            'rdrf.helpers',
            'rdrf.models',
            'rdrf.models.definition',
            'rdrf.reports',
            'rdrf.routing',
            'rdrf.security',
            'rdrf.services',
            'rdrf.services.io',
            'rdrf.services.io.content',
            'rdrf.services.io.content.export_import',
            'rdrf.services.io.defs',
            'rdrf.services.io.notifications',
            'rdrf.services.rest',
            'rdrf.services.rest.urls',
            'rdrf.services.rest.views',
            'rdrf.services.rpc',
            'rdrf.testing',
            'rdrf.testing.behaviour',
            'rdrf.testing.unit',
            'rdrf.views',
            'rdrf.views.decorators',
            'rdrf.workflows',
            'registry',
            'registry.common',
            'registry.patients',
            'registry.groups',
            'report'
            ]

for package in ['rdrf', 'registry.common',
                'registry.groups', 'registry.patients', 'registry.humangenome', 'report']:
    package_data[package] = []
    if "." in package:
        base_dir, package_dir = package.split(".")
        os.chdir(os.path.join(start_dir, base_dir, package_dir))
    else:
        base_dir = package
        os.chdir(os.path.join(start_dir, base_dir))

    for data_dir in (
            'templates',
            'static',
            'migrations',
            'fixtures',
            'features',
            'schemas',
            'templatetags',
            'management'):
        package_data[package].extend([add_file_for_package(package, subdir, f) for (
            subdir, dirs, files) in os.walk(data_dir) for f in files])

    os.chdir(start_dir)


setup(name='trrf',
      version='1.0.0',
      packages=find_packages(),
      description='TRRF',
      long_description='Trial Ready Registry Framework',
      author='Queensland University of Technology - eResearch',
      package_data=package_data,
      zip_safe=False
      )
