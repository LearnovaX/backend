from django.core.exceptions import ValidationError


def validate_days_of_week(value):
    # Expect a list of ints 0..6
    if not isinstance(value, list):
        raise ValidationError("days_of_week must be a list of integers 0..6.")
    if any(not isinstance(i, int) for i in value):
        raise ValidationError("All weekday values must be integers.")
    if any(i < 0 or i > 6 for i in value):
        raise ValidationError("Weekday integers must be in range 0..6.")
    # optional: dedupe or enforce length
    if len(set(value)) != len(value):
        raise ValidationError("Duplicate weekday values are not allowed.")
