from django.utils.log import AdminEmailHandler
from logging import StreamHandler


# An AdminEmainHandler that removes potentially sensitive information from the Error emails
# sent to Django Admins.
class AdminShortEmailHandler(AdminEmailHandler):
    def send_mail(self, subject, message, *args, **kwargs):
        try:
            message = message[:message.index('\nRequest information:')]
        except ValueError:
            pass
        super().send_mail(subject, message, fail_silently=True)


# Can be used to log to stderr all the information that is normally included
# in the Error emails sent to Django admins.
class StreamDetailedErrorHandler(StreamHandler):
    def emit(self, record):
        email_handler = _NoMailErrorHandler(include_html=False)
        email_handler.emit(record)
        msg = '\n'.join((email_handler.subject, email_handler.message))

        record.args = None
        record.msg = msg
        super().emit(record)


class _NoMailErrorHandler(AdminEmailHandler):

    def send_mail(self, subject, message, *args, **kwargs):
        self.subject = subject
        self.message = message
