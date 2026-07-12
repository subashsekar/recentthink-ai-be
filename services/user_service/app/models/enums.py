"""User Service domain enums."""

from __future__ import annotations

from enum import StrEnum


class CurrentStatus(StrEnum):
    """Allowed professional/current-status values for a profile."""

    STUDENT = "Student"
    WORKING_PROFESSIONAL = "Working Professional"
    JOB_SEEKER = "Job Seeker"
    FREELANCER = "Freelancer"
    CAREER_SWITCHER = "Career Switcher"
    OTHER = "Other"


class PrimarySkill(StrEnum):
    """Allowed primary-skill values for a profile."""

    PYTHON = "Python"
    JAVA = "Java"
    JAVASCRIPT = "JavaScript"
    CPP = "C++"
    GO = "Go"
    RUST = "Rust"
    AI_ML = "AI/ML"
    BACKEND = "Backend"
    FRONTEND = "Frontend"
    FULL_STACK = "Full Stack"
    DATA_SCIENCE = "Data Science"
