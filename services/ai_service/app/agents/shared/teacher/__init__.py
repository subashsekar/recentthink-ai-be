"""Teacher module — mentor-style response formatting."""

from app.agents.shared.teacher.formatter import TeacherFormatter
from app.agents.shared.teacher.module import TeacherModule
from app.agents.shared.teacher.schemas import TeacherCard, TeacherOutput

__all__ = ["TeacherCard", "TeacherFormatter", "TeacherModule", "TeacherOutput"]
