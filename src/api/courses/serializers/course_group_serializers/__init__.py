from .course_group_read_serializer import CourseGroupReadSerializer
from .course_group_write_serializer import CourseGroupWriteSerializer
from .course_group_read_light_serializer import CourseGroupReadLightSerializer
from .members import (
    AddTeachersSerializer,
    RemoveTeachersSerializer,
    AddStudentsSerializer,
    RemoveStudentsSerializer,
    TeacherStudentsSerializer,
    StudentTasksStatusSerializer
)