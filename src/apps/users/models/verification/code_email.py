from django.db import models

from src.apps.common.utils import default_expire_date


class CodeEmail(models.Model):
    code = models.CharField(max_length=10)
    email = models.EmailField(max_length=200)
    expire_date = models.DateTimeField(default=default_expire_date)

    class Meta:
        verbose_name = "Email Code"
        verbose_name_plural = "Email Codes"
        db_table = "CodeEmail"

    def save(self, *args, **kwargs):
        CodeEmail.objects.filter(email=self.email).delete()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Code: {self.code} for {self.email} (Expires: {self.expire_date})"
