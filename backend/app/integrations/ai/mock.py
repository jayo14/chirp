import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from backend.app.schemas.assignment import AssignmentClassification, ExtractedAssignmentInfo
from backend.app.integrations.ai.base import AIProvider


class MockAIProvider(AIProvider):
    async def classify_message(
        self,
        text: str,
        has_media: bool = False,
    ) -> AssignmentClassification:
        lower = text.lower().strip()

        # Check for deadline updates / cancellations
        if any(term in lower for term in ["moved to", "extended to", "postponed to", "new deadline", "deadline changed"]):
            match = re.search(r"\b([A-Za-z]{3}\s*\d{3})\b", text)
            course = match.group(1).upper() if match else None
            return AssignmentClassification(
                is_assignment_candidate=True,
                classification_type="deadline_update",
                confidence=0.92,
                related_course_code=course,
                reasoning="Message indicates a modification to an existing assignment deadline",
            )

        if any(term in lower for term in ["cancel", "cancelled", "no longer submitting", "call off"]):
            match = re.search(r"\b([A-Za-z]{3}\s*\d{3})\b", text)
            course = match.group(1).upper() if match else None
            return AssignmentClassification(
                is_assignment_candidate=True,
                classification_type="cancellation",
                confidence=0.88,
                related_course_code=course,
                reasoning="Message mentions assignment cancellation",
            )

        # Check for assignment indicators
        indicators = [
            "assignment",
            "take-home",
            "take home",
            "submit before",
            "submission deadline",
            "solve the following",
            "lecturer gave us",
            "homework",
            "project assignment",
            "term paper",
        ]

        has_indicator = any(ind in lower for ind in indicators)

        if has_indicator or (has_media and ("submit" in lower or "questions" in lower)):
            match = re.search(r"\b([A-Za-z]{3}\s*\d{3})\b", text)
            course = match.group(1).upper() if match else None
            return AssignmentClassification(
                is_assignment_candidate=True,
                classification_type="new_assignment",
                confidence=0.95,
                related_course_code=course,
                reasoning="Message contains explicit assignment announcements or instructions",
            )

        # Ordinary conversation
        return AssignmentClassification(
            is_assignment_candidate=False,
            classification_type="ordinary_conversation",
            confidence=0.98,
            reasoning="Regular chat message without assignment directives",
        )

    async def extract_assignment(
        self,
        text: str,
        media_base64: Optional[str] = None,
        mime_type: Optional[str] = None,
        extracted_doc_text: Optional[str] = None,
    ) -> ExtractedAssignmentInfo:
        combined_text = f"{text}\n{extracted_doc_text or ''}".strip()

        # Find course code
        match = re.search(r"\b([A-Za-z]{3})\s*(\d{3})\b", combined_text, re.IGNORECASE)
        course_code = f"{match.group(1).upper()} {match.group(2)}" if match else "GEN 101"

        # Guess course title
        course_titles = {
            "CSC 301": "Data Structures",
            "CSC 309": "Artificial Intelligence",
            "ICT 305": "Computer Networks",
            "CSC 307": "Cloud Computing",
            "MTH 201": "Linear Algebra",
        }
        course_title = course_titles.get(course_code, "Academic Course")

        # Guess title
        lines = [line.strip() for line in combined_text.split("\n") if line.strip()]
        title = "Class Assignment"
        for line in lines:
            if any(k in line.lower() for k in ["assignment:", "topic:", "title:"]):
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    title = parts[1].strip()
                    break
            elif len(line) < 60 and not line.lower().startswith("good"):
                title = line
                break

        # Extract questions
        questions: List[str] = []
        for line in lines:
            if re.match(r"^(\d+[\.\)]|[a-zA-Z][\.\)])\s+", line):
                questions.append(line)

        if not questions:
            questions = [f"Complete the task outlined in {course_code}"]

        # Extract deadline
        deadline_iso = None
        deadline_clarification = False

        if "tomorrow" in combined_text.lower():
            due = datetime.now(timezone.utc) + timedelta(days=1)
            deadline_iso = due.strftime("%Y-%m-%d 17:00")
        elif "next week" in combined_text.lower():
            due = datetime.now(timezone.utc) + timedelta(days=7)
            deadline_iso = due.strftime("%Y-%m-%d 17:00")
        elif "monday" in combined_text.lower():
            due = datetime.now(timezone.utc) + timedelta(days=5)
            deadline_iso = due.strftime("%Y-%m-%d 17:00")
        elif re.search(r"\b(\d{4}-\d{2}-\d{2})\b", combined_text):
            m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", combined_text)
            deadline_iso = f"{m.group(1)} 17:00"
        else:
            deadline_clarification = True

        return ExtractedAssignmentInfo(
            course_code=course_code,
            course_title=course_title,
            assignment_title=title,
            description=combined_text[:500] if combined_text else "Assignment details provided in attachment.",
            questions=questions,
            deadline_iso=deadline_iso,
            deadline_clarification_needed=deadline_clarification,
            submission_instructions="Submit as specified by your lecturer.",
            confidence=0.92,
        )
