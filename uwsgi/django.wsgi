# Generic WSGI application
import os
import uwsgi
from django.core.wsgi import get_wsgi_application

AUTH_USER_ID = ''
def application(environ, start):
    global AUTH_USER_ID
    uri = environ.get('REQUEST_URI', '')

    # copy any vars into os.environ
    for key in environ:
        os.environ[key] = str(environ[key])

    response = get_wsgi_application()(environ,start)
    user_id = str(response.user_id) if hasattr(response, 'user_id') else ''
    if 'login?' in uri and user_id != AUTH_USER_ID:
        AUTH_USER_ID = user_id
    elif 'logout?' in uri:
        AUTH_USER_ID = ''

    uwsgi.set_logvar('user_id', AUTH_USER_ID)

    return response
