from django.urls import include, path

urlpatterns = [
    path("accounts/", include("src.api.users.urls")),
    path("tasks/", include("src.api.assignments.urls")),
    path("course/", include("src.api.courses.urls")),
    path("answers/", include("src.api.submissions.urls")),
    path("notifications/", include("src.api.notifications.urls")),
    path("chat/", include("src.api.chat.urls")),
    path("grades/", include("src.api.grades.urls")),
    path("plagiarism/", include("src.api.plagiarism.urls")),
]
