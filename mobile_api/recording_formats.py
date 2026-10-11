"""Validate browser PCM WAV in addition to existing native M4A uploads."""
import wave
from rest_framework.exceptions import ValidationError


def recording_extension(upload):
    head = upload.read(16)
    upload.seek(0)
    if len(head) >= 12 and head[4:8] == b'ftyp':
        return 'm4a'
    if head[:4] == b'RIFF' and head[8:12] == b'WAVE':
        try:
            with wave.open(upload, 'rb') as audio:
                if (audio.getcomptype() != 'NONE' or audio.getnchannels() not in (1, 2)
                        or audio.getsampwidth() not in (1, 2, 3, 4)
                        or not 8000 <= audio.getframerate() <= 48000
                        or not 0 < audio.getnframes() / audio.getframerate() <= 181):
                    raise ValueError
                expected = audio.getnframes() * audio.getnchannels() * audio.getsampwidth()
                if len(audio.readframes(audio.getnframes())) != expected:
                    raise ValueError
            return 'wav'
        except (wave.Error, EOFError, ValueError):
            raise ValidationError('WAV ses kaydı geçersiz veya süre sınırını aşıyor.')
        finally:
            upload.seek(0)
    raise ValidationError('M4A veya WAV ses kaydı gerekli.')


def recording_content_type(file):
    return 'audio/wav' if file.name.lower().endswith('.wav') else 'audio/mp4'
