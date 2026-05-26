from django.db import models
from django.utils import timezone


class TemporaryUser(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=255, unique=True, null=True, blank=True)
    region = models.CharField(max_length=255)
    date_joined = models.DateTimeField(default=timezone.now)
    role = models.CharField(max_length=50)
    password = models.CharField(max_length=255)
    re_password = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.first_name} - {self.email}"

    class Meta:
        db_table = "TemporaryUser"
