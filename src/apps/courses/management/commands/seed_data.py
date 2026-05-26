from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from src.apps.assignments.models import Task
from src.apps.courses.models import Category, Course, CourseEnrollment, CourseGroup
from src.apps.submissions.models import Answer
from src.apps.users.models import Role, User, UserProfile


class Command(BaseCommand):
    help = "Seed demo data: admin, teachers, students, courses, groups, tasks, and answers"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("👥 Creating users...")
        admin_user = self._create_admin_user()
        teachers = self._create_teachers()
        students = self._create_students()

        self.stdout.write("📚 Creating courses...")
        courses = self._create_courses(admin_user)

        self.stdout.write("👥 Creating course groups...")
        self._create_course_groups(courses, teachers, students)

        self.stdout.write("📋 Creating tasks...")
        tasks = self._create_tasks(courses, teachers)

        self.stdout.write("✅ Creating answers...")
        self._create_answers(tasks, students)

        self.stdout.write(
            self.style.SUCCESS(
                "✨ Demo data seeded successfully!\n\n"
                "📋 Summary:\n"
                f"  • 1 Admin user: admin@example.com\n"
                f"  • 2 Teacher users: teacher1@example.com, teacher2@example.com\n"
                f"  • 10 Student users: student1@example.com - student10@example.com\n"
                f"  • 3 Courses\n"
                f"  • 2 Course Groups per course\n"
                f"  • 10 Tasks (2-4 per course)\n"
                f"  • 10-20 Sample Answers\n\n"
                "🔐 All passwords: 12"
            )
        )



    def _create_admin_user(self):
        """Create a single admin user"""
        User.objects.create_superuser(
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            password="12"
        )
        # Fetch the user after creation since create_superuser doesn't return
        user = User.objects.get(email="admin@example.com")
        return user

    def _create_teachers(self):
        """Create 2 teacher users"""
        teachers = []
        for i in range(1, 3):
            email = f"teacher{i}@example.com"
            user = User.objects.create_user(
                email=email,
                first_name=f"Teacher{i}",
                last_name=f"Last{i}",
                password="12",
                role=Role.TEACHER
            )
            user.email_verified = True
            user.must_set_password = False
            user.is_active = True
            user.save()

            # Create profile
            UserProfile.objects.get_or_create(user=user)

            # Add to teachers group
            teacher_group, _ = Group.objects.get_or_create(name="Teachers")
            user.groups.add(teacher_group)

            teachers.append(user)

        return teachers

    def _create_students(self):
        """Create 10 student users"""
        students = []
        for i in range(1, 11):
            email = f"student{i}@example.com"
            user = User.objects.create_user(
                email=email,
                first_name=f"Student{i}",
                last_name=f"Last{i}",
                password="12",
                role=Role.STUDENT
            )
            user.email_verified = True
            user.must_set_password = False
            user.is_active = True
            user.save()

            # Create profile
            UserProfile.objects.get_or_create(user=user)

            # Add to students group
            student_group, _ = Group.objects.get_or_create(name="Students")
            user.groups.add(student_group)

            students.append(user)

        return students

    def _create_courses(self, author):
        """Create 3 sample courses"""
        courses = []
        course_data = [
            {
                "name": "Introduction to Python",
                "description": "Learn the basics of Python programming including variables, data types, "
                              "control flow, and functions.",
            },
            {
                "name": "Web Development with Django",
                "description": "Master Django framework for building robust web applications with "
                              "databases, authentication, and REST APIs.",
            },
            {
                "name": "Data Science Fundamentals",
                "description": "Explore data analysis, visualization, and machine learning concepts "
                              "using Python libraries like Pandas and Scikit-learn.",
            },
        ]

        for data in course_data:
            course = Course.objects.create(
                name=data["name"],
                description=data["description"],
                author=author,
                is_active=True,
                free_order=True,
                is_certificated=True,
            )
            courses.append(course)

        return courses

    def _create_course_groups(self, courses, teachers, students):
        """Create course groups and enroll users"""
        teacher_idx = 0
        student_idx = 0

        for course in courses:
            # Create 2 groups per course
            for group_num in range(1, 3):
                group = CourseGroup.objects.create(
                    name=f"{course.name} - Group {group_num}",
                    course=course,
                    students_limit=5,
                    is_active=True,
                )

                # Assign a teacher to the group
                teacher = teachers[teacher_idx % len(teachers)]
                CourseEnrollment.objects.create(
                    user=teacher,
                    course=course,
                    group=group,
                    role="teacher"
                )
                teacher_idx += 1

                # Enroll 2-3 students in the group
                for _ in range(2 if group_num == 1 else 3):
                    if student_idx < len(students):
                        student = students[student_idx]
                        CourseEnrollment.objects.create(
                            user=student,
                            course=course,
                            group=group,
                            role="student"
                        )
                        student_idx += 1

    def _create_tasks(self, courses, teachers):
        """Create sample tasks/assignments"""
        tasks = []
        task_templates = [
            {
                "name": "Assignment 1: Basic Concepts Quiz",
                "description": "<p>Complete a quiz covering the basic concepts introduced in the course. "
                              "You have 60 minutes to complete 20 multiple choice questions.</p>",
            },
            {
                "name": "Assignment 2: Practical Exercise",
                "description": "<p>Write a small program that demonstrates your understanding of the core concepts. "
                              "Submit your code with comments explaining each section.</p>",
            },
            {
                "name": "Assignment 3: Project Work",
                "description": "<p>Complete a comprehensive project that integrates multiple concepts learned "
                              "in the course. Submit a detailed report with your findings.</p>",
            },
            {
                "name": "Assignment 4: Code Review",
                "description": "<p>Review the provided code sample and identify issues, suggest improvements, "
                              "and explain best practices you would apply.</p>",
            },
        ]

        for course_idx, course in enumerate(courses):
            teacher = teachers[course_idx % len(teachers)]
            # Create 2-4 tasks per course
            num_tasks = 2 + (course_idx % 3)
            for task_num in range(num_tasks):
                template = task_templates[task_num % len(task_templates)]
                task = Task.objects.create(
                    number=task_num + 1,
                    name=f"{template['name']} - {course.name}",
                    description=template["description"],
                    course=course,
                    created_by=teacher,
                    enable_context_menu_for_students=True,
                    allow_resubmitting_task=True,
                )
                tasks.append(task)

        return tasks

    def _create_answers(self, tasks, students):
        """Create sample answers/submissions"""
        answer_descriptions = [
            "I have completed this assignment according to the requirements. I used best practices "
            "and tested the code thoroughly.",
            "Here is my solution to the problem. I followed the instructions and added comments "
            "for better code readability.",
            "I have submitted my work. Please review and provide feedback for improvement.",
            "This is my implementation of the task. I have learned a lot from doing this exercise.",
            "I have finished the assignment and made sure all test cases pass successfully.",
        ]

        statuses = [Answer.Status.in_review, Answer.Status.approved, Answer.Status.have_flaws]

        for task in tasks:
            # Create 1-2 answers per task from different students
            num_answers = 1 + (task.id % 2)
            for answer_num in range(num_answers):
                if answer_num < len(students):
                    student = students[answer_num]
                    description = answer_descriptions[answer_num % len(answer_descriptions)]
                    status = statuses[answer_num % len(statuses)]

                    Answer.objects.create(
                        task=task,
                        user=student,
                        description=description,
                        status=status,
                        plagiarism_status=Answer.PlagiarismStatus.analyzed,
                    )

