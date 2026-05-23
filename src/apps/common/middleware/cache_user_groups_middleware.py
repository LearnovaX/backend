from django.utils.deprecation import MiddlewareMixin


class CacheUserGroupsMiddleware(MiddlewareMixin):
    """
    Middleware that caches the authenticated user's group names
    so serializers and views can check them without hitting DB repeatedly.
    """

    def process_request(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            user._cached_group_names = set(user.groups.values_list("name", flat=True))
        return None
