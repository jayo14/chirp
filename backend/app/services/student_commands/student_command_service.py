import re
import logging
from datetime import datetime, timezone
from typing import Optional
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.services.deadline_management.deadline_service import DeadlineService

logger = logging.getLogger(__name__)


class StudentCommandService:
    def __init__(self, deadline_service: Optional[DeadlineService] = None):
        self.deadline_service = deadline_service or DeadlineService()

    def is_student_query(self, text: str) -> bool:
        if not text:
            return False
        clean = text.strip().lower()
        if clean.startswith("/") or clean.startswith("!"):
            return True
        keywords = [
            "assignment",
            "assignments",
            "upcoming",
            "deadline",
            "deadlines",
            "homework",
            "what do we have",
            "due date",
        ]
        return any(k in clean for k in keywords)

    async def handle_query(
        self,
        sender_jid: str,
        text: str,
        assignment_repo: AssignmentRepository,
    ) -> str:
        clean = text.strip()
        lower = clean.lower().lstrip("/").lstrip("!")
        parts = lower.split()
        cmd = parts[0] if parts else ""

        if cmd in ["help", "start"]:
            return (
                "👋 *CHIRP STUDENT ASSISTANT*\n\n"
                "I track class assignments and deadlines so you never miss a submission!\n\n"
                "• `/upcoming` or `/assignments` - View all active upcoming assignments\n"
                "• `/course <CODE>` - View assignments for a specific course (e.g. `/course CSC 301`)\n"
                "• Forward any assignment sheet, image, or document here to have it tracked."
            )

        if cmd in ["upcoming", "assignments"] or any(k in lower for k in ["what do we have", "due date", "deadline"]):
            now_utc = datetime.now(timezone.utc)
            upcoming = await assignment_repo.list_active_upcoming(now_utc)
            if not upcoming:
                return "🎉 *Good news!* There are currently no outstanding assignments due."

            lines = ["📚 *UPCOMING CLASS ASSIGNMENTS:*\n"]
            for idx, a in enumerate(upcoming):
                c_line = f"*{idx + 1}. {a.course_code}"
                if a.course_title:
                    c_line += f" – {a.course_title}*"
                else:
                    c_line += "*"

                d_str = self.deadline_service.format_deadline_for_display(a.deadline_at)
                desc = a.description.split("\n")[0][:100]

                item = f"{c_line}\n*Title:* {a.title}\n*Due:* {d_str}\n*Details:* {desc}"
                lines.append(item)

            lines.append("━━━━━━━━━━━━━━━━━━━\n_Start early and avoid last-minute rush!_")
            return "\n\n".join(lines)

        if cmd == "course" or len(parts) >= 1:
            # Check if a course code was requested e.g. /course CSC 301 or CSC 301
            m = re.search(r"\b([A-Za-z]{3}\s*\d{3})\b", clean)
            if m:
                course_code = m.group(1).upper()
                now_utc = datetime.now(timezone.utc)
                upcoming = await assignment_repo.list_active_upcoming(now_utc)
                matched = [a for a in upcoming if a.course_code.replace(" ", "").upper() == course_code.replace(" ", "")]

                if not matched:
                    return f"ℹ️ No active upcoming assignments found for *{course_code}*."

                lines = [f"📚 *ACTIVE ASSIGNMENTS FOR {course_code}:*\n"]
                for a in matched:
                    d_str = self.deadline_service.format_deadline_for_display(a.deadline_at)
                    lines.append(
                        f"• *{a.title}*\n"
                        f"  *Due:* {d_str}\n"
                        f"  *Instructions:* {a.description}\n"
                        f"  *Submission:* {a.submission_instructions or 'As specified by lecturer'}"
                    )
                return "\n\n".join(lines)

        return (
            "🤖 I am your Class Assignment Bot.\n"
            "Type `/upcoming` to view current assignments, or `/help` for options."
        )
