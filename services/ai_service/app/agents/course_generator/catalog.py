"""Course Generator catalog helpers (example learning paths)."""

from __future__ import annotations

from app.agents.course_generator.schemas import CourseExampleResponse


def list_examples() -> list[CourseExampleResponse]:
    return [
        CourseExampleResponse(
            id="python-ai-engineer",
            title="Python → AI Engineer",
            skill="Python",
            goal="Become AI Engineer",
            level="Beginner",
            duration_days=60,
            daily_hours=2.0,
            learning_style="Hands-on",
            programming_language="Python",
            icon="brain",
        ),
        CourseExampleResponse(
            id="fullstack-web",
            title="Full-Stack Web Developer",
            skill="Web Development",
            goal="Become Full-Stack Developer",
            level="Beginner",
            duration_days=90,
            daily_hours=2.5,
            learning_style="Project-based",
            programming_language="JavaScript",
            icon="code",
        ),
        CourseExampleResponse(
            id="data-analyst",
            title="Data Analyst Path",
            skill="Data Analysis",
            goal="Become Data Analyst",
            level="Intermediate",
            duration_days=45,
            daily_hours=1.5,
            learning_style="Hands-on",
            programming_language="Python",
            icon="chart",
        ),
    ]


__all__ = ["list_examples"]
