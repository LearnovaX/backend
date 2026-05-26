from django.db import models

from src.apps.common.utils import default_expire_date
from src.apps.users.models import User


class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    new_email = models.EmailField()
    code = models.CharField(max_length=10)
    expire_date = models.DateTimeField(default=default_expire_date)

    class Meta:
        db_table = "Email Verifications"

    def save(self, *args, **kwargs):
        EmailVerification.objects.filter(new_email=self.new_email).delete()
        super().save(*args, **kwargs)
