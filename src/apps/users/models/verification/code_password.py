from django.db import models

from src.apps.common.utils import default_expire_date
from src.apps.users.models.user import User


class CodePassword(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="User")
    code = models.CharField(max_length=10)
    expire_date = models.DateTimeField(default=default_expire_date)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Password Code"
        verbose_name_plural = "Password Codes"
        db_table = "CodePassword"

    def save(self, *args, **kwargs):
        CodePassword.objects.filter(user=self.user).delete()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Code: {self.code} for {self.user.email} (Expires: {self.expire_date})"
