import random
from datetime import timedelta

from django.utils import timezone


def default_expire_date():
    return timezone.now() + timedelta(minutes=10)


def generate_random_code():
    return random.randint(1000, 9999)
