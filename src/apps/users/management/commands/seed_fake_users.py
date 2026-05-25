from __future__ import annotations

import random
import string
from datetime import date, datetime, timedelta

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.utils import timezone
from faker import Faker

from src.apps.users.models import UserProfile  # make sure this import path matches your project
from src.apps.users.models import Role, User


def rand_datetime_between(
    start_dt: datetime,
    end_dt: datetime,
) -> datetime:
    """Return a random aware datetime between two aware datetimes."""
    total_seconds = int((end_dt - start_dt).total_seconds())
    if total_seconds <= 0:
        return start_dt
    rand_offset = random.randint(0, total_seconds)
    return start_dt + timedelta(seconds=rand_offset)


def coerce_aware(d: datetime) -> datetime:
    """Ensure datetime is timezone-aware using current TZ."""
    if timezone.is_aware(d):
        return d
    return timezone.make_aware(d, timezone.get_current_timezone())


class Command(BaseCommand):
    help = (
        "Seed fake users with profiles and varied states (authorized/not authorized/deactivated)."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--count", type=int, default=200, help="How many users" " to create (default: 200)"
        )
        parser.add_argument(
            "--from",
            dest="from_date",
            type=str,
            default=None,
            help="Start date (YYYY-MM-DD) for date_joined window (default: 2 years ago)",
        )
        parser.add_argument(
            "--to",
            dest="to_date",
            type=str,
            default=None,
            help="End date (YYYY-MM-DD) for date_joined window (default: today)",
        )
        parser.add_argument(
            "--password", type=str, default="Test1234!", help="Password for created users"
        )
        parser.add_argument("--domain", type=str, default="example.com", help="Email domain to use")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do everything except write to DB",
        )

    def handle(self, *args, **opts):
        # users = User.objects.exclude(pk__in=[1,3,4,17,6,5,16])
        count: int = opts["count"]
        email_domain: str = opts["domain"]
        password: str = opts["password"]
        dry_run: bool = opts["dry_run"]

        # Date window
        today = timezone.now().date()
        default_start = today - timedelta(days=730)  # ~2 years
        from_date_str = opts.get("from_date")
        to_date_str = opts.get("to_date")

        start_date: date = (
            datetime.strptime(from_date_str, "%Y-%m-%d").date() if from_date_str else default_start
        )
        end_date: date = datetime.strptime(to_date_str, "%Y-%m-%d").date() if to_date_str else today
        if end_date < start_date:
            raise SystemExit("--to date must be >= --from date")

        # Convert to aware datetimes spanning whole days
        start_dt = coerce_aware(datetime.combine(start_date, datetime.min.time()))
        end_dt = coerce_aware(datetime.combine(end_date, datetime.max.time()))

        fake = Faker()
        # Weighted role distribution (tweak as you like)
        role_choices = [
            (Role.STUDENT, 0.60),
            (Role.TEACHER, 0.15),
            (Role.ADMIN, 0.10),
        ]
        roles, weights = zip(*role_choices)

        # Population states:
        # - ~55% authorized (email_verified=True, must_set_password=False, recent last_login)
        # - ~30% not authorized (email_verified=False, must_set_password=True, last_login=None)
        # - ~15% deactivated (is_active=False + deactivation_time)
        def pick_state() -> str:
            r = random.random()
            if r < 0.55:
                return "authorized"
            elif r < 0.85:
                return "not_authorized"
            return "deactivated"

        # Track generated phones to avoid UniqueConstraint violations when set
        used_phones = set()

        def unique_phone() -> str | None:
            if random.random() < 0.25:
                # 25% of profiles with no phone at all (allowed)
                return None
            # Generate unique-ish E.164-like numbers
            for _ in range(10):
                num = "+9989" + "".join(random.choices(string.digits, k=8))
                if num not in used_phones:
                    used_phones.add(num)
                    return num
            return None

        created_users = []

        @transaction.atomic
        def do_create():
            for i in range(count):
                print(i)
                first_name = fake.first_name()
                last_name = fake.last_name()

                # Email uniqueness is enforced; include a counter to be safe
                email = (
                    f"{first_name.lower()}.{last_name.lower()}."
                    f"{fake.unique.pystr(min_chars=4, max_chars=6)}@{email_domain}"
                )

                role = random.choices(roles, weights=weights, k=1)[0]
                date_joined = rand_datetime_between(start_dt, end_dt)

                user = User.objects.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    password=password,
                )
                name = {
                    "admin": "Admins",
                    "teacher": "Teachers",
                    "student": "Students",
                }.get(role, "Students")
                groups, _ = Group.objects.get_or_create(name=name)
                user.groups.add(groups)

                # Choose state & set flags
                state = pick_state()
                is_active = True
                email_verified = False
                must_set_password = True
                last_login = None
                deactivation_time = None
                days_to_delete = None

                if state == "authorized":
                    email_verified = True
                    must_set_password = False
                    is_active = True
                    # last_login sometime after join
                    last_login = rand_datetime_between(date_joined, end_dt)
                elif state == "not_authorized":
                    email_verified = False
                    must_set_password = True
                    is_active = True
                else:  # deactivated
                    is_active = False
                    # Deactivated sometime after join
                    deactivation_time = rand_datetime_between(date_joined, end_dt)
                    days_to_delete = random.choice([7, 14, 30, 60, 90])

                # Persist the flags + custom dates
                user.is_active = is_active
                user.email_verified = email_verified
                user.must_set_password = must_set_password
                user.mfa_enabled = random.random() < 0.1  # ~10% with MFA
                user.date_joined = date_joined
                user.last_login = last_login

                # Sometimes set a google_id to exercise that index/uniqueness
                if random.random() < 0.2:
                    # Keep unique; keep it short-ish
                    user.google_id = fake.unique.pystr(min_chars=8, max_chars=12)

                user.save()

                # Always create a linked UserProfile (avoid 500s)
                profile = UserProfile.objects.create(
                    user=user,
                    middle_name=(fake.first_name() if random.random() < 0.5 else None),
                    interface_language=random.choice(["en", "ru", "uz"]),
                    timezone=random.choice(["UTC+5", "UTC+3", "UTC+6"]),
                    birth_date=fake.date_between(start_date="-60y", end_date="-18y"),
                    profile_edit_blocked=random.random() < 0.05,
                    deactivation_time=deactivation_time,
                    days_to_delete_after_deactivation=days_to_delete,
                    phone_number=unique_phone(),
                    company=(fake.company() if random.random() < 0.5 else None),
                    # profile_photo left empty; your validator requires real files
                )

                created_users.append((user, profile))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("[DRY RUN] Would create users, not writing to DB.")
            )
            return

        do_create()
        self.stdout.write(self.style.SUCCESS(f"Created {len(created_users)} users with profiles."))
