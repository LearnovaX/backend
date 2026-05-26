from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken

from src.apps.users.models import User


class JWTAuthMiddleware:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)

        token = params.get("token", [None])[0]
        scope["user"] = None
        if token:
            try:
                access_token = AccessToken(token)
                user_id = access_token["user_id"]
                scope["user"] = await self.get_user(user_id)
            except Exception:
                scope["user"] = None

        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
