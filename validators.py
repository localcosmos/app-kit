from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def file_size(value): # add this to some file where you can import it from
    limit = settings.APP_KIT_MAXIMUM_IMAGE_UPLOAD_SIZE

    limit_mb = limit / 1024 / 1024
    if value.size > limit:
        raise ValidationError(_('File too large. Size should not exceed %(size)s MiB.') % {'size': limit_mb})
