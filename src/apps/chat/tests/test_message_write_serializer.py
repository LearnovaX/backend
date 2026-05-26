import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from src.api.chat.serializers import MessageWriteSerializer


def test_message_requires_text_or_file():
    serializer = MessageWriteSerializer(data={"content": ""})
    assert not serializer.is_valid()
    assert "non_field_errors" in serializer.errors


def test_message_allows_file_only():
    uploaded_file = SimpleUploadedFile("sample.txt", b"hello", content_type="text/plain")
    serializer = MessageWriteSerializer(data={"content": "", "file": uploaded_file})
    assert serializer.is_valid()

