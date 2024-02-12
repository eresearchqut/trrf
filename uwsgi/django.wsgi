# Generic WSGI application
import os
import uwsgi
from django.core.wsgi import get_wsgi_application

def application(environ, start):
    # copy any vars into os.environ
    for key in environ:
        os.environ[key] = str(environ[key])

    response = get_wsgi_application()(environ,start)
    user_id = str(response.user_id) if hasattr(response, 'user_id') else ''

    uwsgi.set_logvar('user_id', user_id)

    return response
