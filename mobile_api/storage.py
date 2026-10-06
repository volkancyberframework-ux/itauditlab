from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateVoiceStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.MOBILE_VOICE_ROOT, base_url=None)

    def url(self, name):
        raise ValueError(
            "Private recordings must be accessed through the authorized API."
        )
