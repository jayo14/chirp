# Product Requirements Document (PRD)
# Class Assignment Bot

**Product type:** WhatsApp-based academic utility  
**Initial deployment:** LASUSTECH class WhatsApp group  
**Platform:** WhatsApp  
**Status:** Ready for development planning  
**Version:** 1.0

---

## 1. Product Overview

### 1.1 Product Description

Class Assignment Bot is an AI-powered WhatsApp assistant designed to help university students keep track of academic assignments, understand their requirements, and avoid missing submission deadlines.

The bot monitors a designated class WhatsApp group and accepts assignments forwarded directly to its private chat.

Using AI and multimodal processing, it identifies assignment-related messages, extracts relevant information from text, images and documents, and submits detected assignments for administrator approval.

Once approved, the bot publishes a structured assignment announcement to the class group and automatically manages deadline reminders and weekly assignment summaries.

### 1.2 Problem Statement

Students frequently miss assignments or submit them late because:

- Assignment announcements get buried in busy WhatsApp group conversations.
- Students forget assignments shortly after they are announced.
- Some students miss announcements entirely.
- Submission deadlines are forgotten or misunderstood.
- Assignment instructions, especially those shared as photographs, are difficult to retrieve later.
- Students sometimes don't understand what an assignment requires.
- Students often discover outstanding assignments when there is very little time left.

The existing class WhatsApp group serves as the primary communication channel, but it does not provide a reliable assignment tracking mechanism.

### 1.3 Proposed Solution

Introduce an intelligent WhatsApp bot that acts as a centralized assignment tracker for the class.

It automatically discovers potential assignments, processes them, obtains administrator approval, publishes them in an organized format, and reminds students before submission deadlines.

The bot should work independently of any single student. It must continue monitoring, tracking and reminding students even when the person who initially introduced it is offline.

---

## 2. Product Goals

### Primary Goals

1. Ensure students are aware of assignments announced in the class group.
2. Reduce forgotten and missed assignments.
3. Make assignment instructions easier to retrieve.
4. Ensure submission deadlines are clearly communicated.
5. Automatically remind students before deadlines.
6. Provide a consolidated weekly overview of outstanding assignments.
7. Minimize the manual effort required to manage class assignments.

### Success Metrics

| Metric | Initial target |
|---|---|
| Assignment detection precision | At least 95% |
| Assignment extraction accuracy | At least 95% on clearly readable inputs |
| Duplicate publications | Zero |
| Reminder delivery | At least 99% of successfully queued messages |
| Weekly digest delivery | Every Sunday |
| Manual administrator effort | Minimal |
| Missed assignment reports | Track and reduce over time |

These are target metrics, not established performance claims. Detection precision and extraction accuracy should be measured separately using real class messages.

### Non-Goals

The initial product is NOT intended to:

- Manage student grades or GPAs.
- Track individual assignment submissions.
- Automatically solve assignments.
- Replace lecturers or academic administrators.
- Manage attendance.
- Manage course registration.
- Become a general-purpose WhatsApp chatbot.
- Support multiple institutions or tenants in the initial release.

The product must remain focused on assignments.

---

## 3. Target Users

### 3.1 Students

Students are the primary beneficiaries.

They should be able to:
- Receive assignment announcements.
- View assignment descriptions.
- See submission deadlines.
- Receive deadline reminders.
- Access original assignment photographs and documents.
- Receive weekly summaries of outstanding assignments.

Students should not need to register or create accounts.

### 3.2 Administrators

Administrators oversee assignment publication and bot configuration.

They should be able to:
- Receive notifications about detected assignments.
- Review extracted assignment information.
- Correct inaccurate information.
- Approve or reject assignments.
- Manage assignment deadlines.
- Review pending assignments.
- Configure reminders and weekly digests.

The initial administrator count and appointment process are configurable product decisions.

### 3.3 Bot

The bot is responsible for:
- Monitoring incoming messages.
- Detecting potential assignments.
- Extracting assignment information.
- Maintaining assignment records.
- Sending administrator notifications.
- Publishing approved assignments.
- Scheduling and sending reminders.
- Generating weekly summaries.

---

## 4. Core Product Features

### 4.1 WhatsApp Integration

WhatsApp is the primary interface.

The system must support two input channels.

**A. Class Group Monitoring**

The bot joins the designated class WhatsApp group and listens for incoming messages.

It should:
- Receive text messages.
- Receive images.
- Receive documents, including PDFs.
- Identify the sender and source message.
- Identify forwarded messages where the platform exposes that metadata.
- Process relevant messages.
- Ignore unrelated conversations.
- Recognize replies and contextual references where possible.

**B. Private Assignment Forwarding**

Administrators and students can forward assignment announcements directly to the bot's private WhatsApp chat.

The bot should accept:
- Text assignments.
- Photographs of handwritten assignments.
- Screenshots.
- PDF documents.
- Images containing diagrams.
- Multiple related images or documents.

Both input channels must feed into the same assignment processing pipeline.

**Important:** The system must not depend on the administrator manually forwarding every assignment.

### 4.2 Assignment Detection

The system must identify messages that contain potential assignment announcements.

Examples of assignment indicators include:

- "Assignment"
- "Take-home"
- "Submit before..."
- "Solve the following questions"
- "Your lecturer gave us..."
- Course-specific assignment instructions.

The detection engine should consider message content, attachments and relevant conversation context.

It must distinguish between:

1. New assignments.
2. Discussions about existing assignments.
3. Assignment clarifications.
4. Deadline modifications.
5. Assignment cancellations.
6. Ordinary conversations.

A message discussing an existing assignment must not automatically create another assignment.

The system should support contextual detection where a student sends a follow-up message such as:

"The submission date has been moved to Wednesday."

The bot should attempt to associate this with the existing assignment.

### 4.3 Multimodal Assignment Processing

The system must process assignments regardless of whether they are submitted as text or visual documents.

Supported input formats:

- Plain text.
- JPEG/JPG.
- PNG.
- PDF.
- Other common WhatsApp-supported document formats where processing is supported.

Processing capabilities:

**Text extraction**
- Extract assignment instructions.
- Identify course codes.
- Identify questions.
- Extract submission instructions.
- Identify deadlines.

**Image understanding**
- Interpret photographs of handwritten assignments.
- Read screenshots.
- Recognize mathematical expressions where possible.
- Understand the relationship between text and diagrams.

**Document processing**
- Extract readable PDF content.
- Preserve the original document.
- Handle multi-page documents.
- Associate multiple attachments with one assignment.

**Diagram preservation**

Original images and diagrams must be retained.

The system must never silently discard diagrams or replace original academic diagrams with AI-generated interpretations.

When text extraction is incomplete, the original attachment must remain accessible.

### 4.4 Assignment Information Extraction

Each detected assignment should be converted into a structured record.

Required information:

| Field | Description |
|---|---|
| Assignment ID | Unique identifier |
| Course code | E.g. CSC 301 |
| Course title | E.g. Data Structures |
| Assignment title | Short descriptive title |
| Description | General assignment instructions |
| Questions | Extracted questions, where applicable |
| Deadline date | Submission date |
| Deadline time | Submission time, if specified |
| Submission instructions | How and where to submit |
| Original attachments | Source photographs and documents |
| Source information | Original WhatsApp message metadata |
| Detection confidence | AI confidence information |
| Review status | Current approval state |

Optional fields must remain optional.

The system must not invent missing course information, questions or deadlines.

If the deadline is unclear or absent, it must be marked as requiring clarification.

### 4.5 Administrator Review and Approval

Every newly detected assignment must enter a review queue.

No new assignment should be automatically published without administrator approval.

The administrator should receive a private WhatsApp notification containing:

- Detected course.
- Assignment title.
- Extracted description.
- Questions.
- Submission deadline.
- Original attachments.
- Source group or sender.
- Any extraction warnings.

Available actions:

**Approve**

Approves the assignment and triggers publication.

**Edit**

Allows the administrator to correct extracted information before publication.

**Reject**

Rejects the candidate and prevents publication.

**Clarify**

Allows the administrator to request clarification or leave the candidate pending.

The system must preserve the original extracted data and record subsequent administrator modifications.

### 4.6 Assignment Publishing

Once approved, the bot publishes a structured message to the designated class WhatsApp group.

Suggested announcement format:

---

📚 *NEW ASSIGNMENT*

*Course:* CSC 301 – Data Structures

*Assignment:* Stack Implementation

*Instructions:*

1. Implement a stack using arrays.
2. Explain the operations.
3. Provide the time complexities.

*Submission Deadline:* Monday, 23 November 2026

*Submission Instructions:* As specified by your lecturer.

📎 *Original Assignment:* Attached.

⏰ A reminder will be sent before the submission deadline.

Please start early!

---

The announcement should:

- Be readable.
- Clearly identify the course.
- Clearly communicate the deadline.
- Preserve the original assignment attachment.
- Avoid unnecessary formatting.
- Avoid misleading or invented information.

The system should retain the published WhatsApp message ID.

If supported by the integration, the bot may mention relevant group members. Group-wide tagging is desirable but not a mandatory MVP requirement.

### 4.7 Deadline Management

Every assignment must have a manageable deadline record.

The system must support:

- Explicit submission dates.
- Explicit submission times.
- Date-only deadlines.
- Deadline modifications.
- Deadline clarification.
- Assignment cancellation.

All dates must be interpreted using the `Africa/Lagos` timezone.

The backend should store timestamps in UTC and convert them for display and scheduling.

If an assignment has no confirmed deadline, it should still be publishable after administrator review, provided the missing deadline is clearly communicated.

However, no deadline reminder should be scheduled until a valid deadline is established.

### 4.8 Automatic Deadline Reminders

The bot must send a reminder approximately 24 hours before each assignment deadline.

Example:

Assignment deadline: Monday, 23 November, 5 PM.

Reminder: Sunday, 22 November, 5 PM.

Reminder format:

---

⏰ *ASSIGNMENT REMINDER*

*Course:* CSC 301 – Data Structures

*Assignment:* Stack Implementation

*Deadline:* Tomorrow, Monday, 23 November, 5 PM.

Don't forget to complete and submit your assignment!

---

Requirements:

- Reminders must be scheduled automatically.
- Each assignment should receive only one standard pre-deadline reminder by default.
- The reminder time should be configurable.
- The scheduler must account for deadline modifications.
- Cancelled assignments must not receive reminders.
- Duplicate reminders must be prevented.
- Failed deliveries must be retried.
- The system must recover pending reminders after restarts.

### 4.9 Weekly Assignment Digest

Every Sunday, the bot must publish a summary of outstanding assignments.

Initial default schedule: Sunday, 5 PM WAT.

The digest should include:
- All upcoming assignments.
- Course codes.
- Assignment titles.
- Submission deadlines.
- Remaining time.
- Original assignment links or attachments where practical.

Example:

---

📚 *WEEKLY ASSIGNMENT UPDATE*

Here are the assignments you should keep track of this week.

*1. CSC 301 – Data Structures*

Implement a stack using arrays.

Deadline: Monday, 23 November.

*2. CSC 309 – Artificial Intelligence*

Explain the applications of machine learning.

Deadline: Tuesday, 24 November.

*3. ICT 305 – Computer Networks*

Discuss network topologies.

Deadline: Wednesday, 25 November.

*4. CSC 307 – Cloud Computing*

Compare cloud deployment models.

Deadline: Friday, 27 November.

---

*Don't wait until the last minute. Start early!*

The digest must:
- Include all eligible upcoming assignments.
- Exclude cancelled assignments.
- Exclude assignments whose deadlines have passed.
- Avoid duplicate entries.
- Be generated from the database, not manually maintained.
- Continue operating when the original administrator is offline.

If there are no outstanding assignments, the bot may send a short message indicating that there are no upcoming assignments.

### 4.10 Assignment Updates

The system must support changes to existing assignments.

Examples:

- Deadline extension.
- Corrected assignment description.
- Additional questions.
- Updated submission instructions.
- Assignment cancellation.

An update should be associated with an existing assignment rather than creating a new record.

Administrator approval is required before publishing significant corrections.

When a deadline changes, existing reminder jobs must be cancelled and recalculated.

The system should publish an update notification to the class group.

---

## 5. Assignment Lifecycle

Every assignment follows a defined lifecycle.

1. `detected`
2. `pending_review`
3. `approved`
4. `published`
5. `updated`
6. `overdue` or `completed`
7. `cancelled` where applicable

A rejected candidate should have a separate rejection state and remain available for audit purposes.

The lifecycle must not lose assignment history.

An assignment should not be deleted merely because its deadline has passed.

---

## 6. User Interaction and Commands

The initial version should use WhatsApp as its primary interface.

A dedicated web dashboard is not required.

Suggested administrator commands:

| Command | Action |
|---|---|
| `/pending` | View pending assignments |
| `/approve ID` | Approve an assignment |
| `/reject ID` | Reject an assignment |
| `/edit ID` | Edit an assignment |
| `/assignments` | View tracked assignments |
| `/upcoming` | View upcoming deadlines |
| `/help` | Display available commands |

The system should also support interactive review through structured WhatsApp messages where the integration permits it.

Commands must only work for authorized administrators.

Ordinary class members must not be able to approve, reject or modify assignments.

Student-facing commands may be introduced later.

---

## 7. Technical Architecture

### 7.1 Architecture Overview

Use a lightweight modular architecture.

The application consists of two main services:

1. WhatsApp Gateway.
2. Python Backend.

The WhatsApp Gateway handles WhatsApp connectivity and communication.

The Python Backend handles business logic, AI processing, storage, scheduling and administration.

### 7.2 Technology Stack

| Layer | Technology |
|---|---|
| WhatsApp integration | Baileys |
| Gateway language | TypeScript |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| AI processing | Vision-capable LLM |
| File storage | Supabase Storage |
| Scheduling | APScheduler with persistent scheduling |
| Deployment | Persistent application services |

The project should not introduce microservices, Kubernetes or unnecessary infrastructure.

### 7.3 Proposed Repository Structure

```text
class-assignment-bot/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   │   ├── assignment_detection/
│   │   │   ├── assignment_extraction/
│   │   │   ├── assignment_review/
│   │   │   ├── assignment_publishing/
│   │   │   ├── deadline_management/
│   │   │   ├── notifications/
│   │   │   └── media_processing/
│   │   ├── integrations/
│   │   ├── scheduler/
│   │   └── main.py
│   │
│   ├── migrations/
│   ├── tests/
│   └── requirements.txt
│
├── whatsapp-gateway/
│   ├── src/
│   │   ├── connection.ts
│   │   ├── message-handler.ts
│   │   ├── media-handler.ts
│   │   ├── group-handler.ts
│   │   ├── sender.ts
│   │   └── webhook-client.ts
│   └── package.json
│
├── docs/
│
├── .env.example
├── .gitignore
└── README.md
```

This structure is a starting point. Modules should remain cohesive and should not be split into unnecessary abstractions.

### 7.4 Backend Responsibilities

The Python backend is responsible for:

- Receiving normalized WhatsApp events.
- Identifying assignment candidates.
- Processing text and attachments.
- Extracting structured assignment information.
- Managing approval workflows.
- Managing assignment records.
- Publishing announcements.
- Scheduling reminders.
- Generating weekly digests.
- Managing administrators and configuration.

### 7.5 WhatsApp Gateway Responsibilities

The gateway is responsible for:

- Establishing WhatsApp connections.
- Maintaining authentication sessions.
- Listening for group messages.
- Receiving private messages.
- Downloading media.
- Sending normalized events to FastAPI.
- Sending approved outgoing messages.
- Reporting connection health.
- Handling reconnection and delivery failures.

The gateway must not contain core assignment business logic.

---

## 8. Database Requirements

The initial database should contain the following entities:

### Assignments
Stores assignment details, deadlines and lifecycle state.

### Assignment Sources
Stores the original WhatsApp message identifiers, group information, sender metadata and source timestamps.

### Attachments
Stores media metadata, file locations, MIME types and relationships to assignments.

### Review Queue
Tracks candidates awaiting administrator decisions.

### Administrators
Stores authorized administrator WhatsApp identifiers and permissions.

### Scheduled Notifications
Tracks reminders, weekly digests, delivery status, retry counts and scheduling information.

### Bot Settings
Stores:
- WhatsApp group identifier.
- Timezone.
- Weekly digest schedule.
- Default reminder policy.
- Administrator configuration.
- Bot operating status.

Important database requirements:

- Use UUIDs for primary identifiers.
- Use foreign keys and appropriate indexes.
- Prevent duplicate source messages.
- Track assignment modification history.
- Track notification delivery status.
- Use database transactions for important state changes.

---

## 9. AI Requirements

The AI system should be structured into independent processing stages.

### Assignment Classification

Determines whether incoming messages contain:

- New assignments.
- Existing assignment discussions.
- Deadline updates.
- Clarifications.
- Cancellations.
- Irrelevant conversations.

### Assignment Extraction

Converts assignment content into structured information.

### Contextual Matching

Associates new messages with existing assignment records when they are updates or clarifications.

### Confidence and Uncertainty

The AI should report uncertainty explicitly.

It must not:
- Invent missing deadlines.
- Invent course codes.
- Fabricate assignment questions.
- Assume an assignment exists from an ambiguous conversation.
- Automatically publish uncertain information.

### Provider Independence

The AI provider must be configurable through environment variables or application configuration.

Avoid coupling business logic to one specific AI provider.

---

## 10. Security and Reliability

### Security

- Secure WhatsApp authentication credentials.
- Keep API secrets outside source control.
- Protect administrative commands.
- Validate incoming webhook requests.
- Restrict access to administrative operations.
- Store media securely.
- Avoid exposing private sender information unnecessarily.
- Use HTTPS for service communication.

### Privacy

The bot should be introduced transparently to the class.

Students should know that the bot processes messages and attachments for assignment detection.

The system should process only what is needed for the assignment-management purpose.

It should not retain unrelated conversations or use class messages for unrelated AI training.

### Reliability

The application must:

- Recover after backend restarts.
- Recover after gateway disconnections.
- Prevent duplicate publications.
- Prevent duplicate reminders.
- Retry temporary delivery failures.
- Preserve pending review records.
- Preserve scheduled notifications.
- Log important events and errors.
- Expose basic service health information.

WhatsApp delivery should be treated as an external operation whose success must be confirmed and recorded.

---

## 11. Deployment Requirements

The system requires two persistent running services:

**Service 1: Backend**

Runs FastAPI, AI processing, database interactions and scheduling.

**Service 2: WhatsApp Gateway**

Maintains the WhatsApp connection and handles message events.

PostgreSQL and persistent media storage must remain available.

The deployment must support:
- Persistent WhatsApp authentication.
- Environment-based configuration.
- Secure communication.
- Application logging.
- Health checks.
- Process restarts.
- Database backups.

A sleeping serverless or free-tier service must not be used for the always-on WhatsApp gateway.

### Initial Configuration

```env
APP_ENV=production
TIMEZONE=Africa/Lagos

DATABASE_URL=

WHATSAPP_GATEWAY_URL=
WHATSAPP_GATEWAY_SECRET=

AI_PROVIDER=
AI_API_KEY=
AI_MODEL=

SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_STORAGE_BUCKET=

DEFAULT_REMINDER_HOURS=24
WEEKLY_DIGEST_DAY=sunday
WEEKLY_DIGEST_TIME=17:00
```

Never commit actual credentials or WhatsApp authentication sessions.

---

## 12. MVP Scope

The following features are mandatory for the first release.

| Feature | Priority |
|---|---|
| WhatsApp group connection | P0 |
| Private message forwarding | P0 |
| Text message processing | P0 |
| Image processing | P0 |
| PDF processing | P0 |
| Assignment detection | P0 |
| Assignment extraction | P0 |
| Admin approval | P0 |
| Assignment publishing | P0 |
| Original attachment preservation | P0 |
| Deadline management | P0 |
| Automatic reminders | P0 |
| Sunday digest | P0 |
| Duplicate prevention | P0 |
| Deadline modification | P0 |
| Basic logging and recovery | P0 |
| Admin dashboard | P2 |
| Individual student tracking | Out of scope |
| Assignment solving | Out of scope |
| Multi-school support | Out of scope |

P0 means required for the initial release.

P2 means a possible later enhancement.

---

## 13. Acceptance Criteria

The MVP is considered complete when all the following conditions are met.

### WhatsApp
- The bot successfully connects to a dedicated WhatsApp account.
- It can monitor the designated class group.
- It can receive privately forwarded assignments.
- It can send messages and attachments to the group.

### AI
- It identifies relevant assignment messages.
- It ignores ordinary conversations.
- It extracts structured assignment information.
- It processes images and PDFs.
- It preserves original diagrams and documents.
- It recognizes potential updates to existing assignments.

### Administration
- Administrators receive pending assignment notifications.
- They can approve, reject and edit assignments.
- Unauthorized users cannot perform administrative actions.

### Publishing
- Only approved assignments are published.
- Announcements follow a consistent format.
- Original attachments are preserved.
- Duplicate announcements are prevented.

### Scheduling
- Deadline reminders are sent at the configured time.
- Sunday digests are generated automatically.
- Deadline modifications update scheduled reminders.
- Cancelled assignments do not receive reminders.
- Notifications survive application restarts.

### Reliability
- WhatsApp disconnections are detected.
- The system attempts to reconnect.
- Pending notifications are recoverable.
- Errors are logged.
- Duplicate processing and delivery are controlled.

---

## 14. Future Enhancements

These are intentionally excluded from the initial release.

Possible future improvements include:

1. A lightweight administrator dashboard.
2. Student commands for checking upcoming assignments.
3. Searchable assignment history.
4. Multiple class groups.
5. Multiple academic departments.
6. Configurable reminder intervals.
7. Course-specific assignment summaries.
8. Better contextual understanding of assignment discussions.
9. Optional student-submitted assignment completion status.
10. A private assignment explanation assistant.

These features should only be considered after the core system has demonstrated reliability.

---

## 15. Development Strategy

Development should follow this order:

| Phase | Deliverable |
|---|---|
| 1 | Working WhatsApp gateway |
| 2 | Incoming message and media processing |
| 3 | Assignment detection |
| 4 | AI extraction |
| 5 | Administrator review workflow |
| 6 | Assignment publishing |
| 7 | Deadline scheduler |
| 8 | Sunday digest |
| 9 | Reliability testing |
| 10 | Class deployment |

Each phase must have working functionality and tests before proceeding.

Do not build the entire application as one large implementation.

Do not introduce a frontend dashboard before the WhatsApp workflows are functional.

---

## 16. Product Principles

The following principles should guide all implementation decisions:

1. **Assignment-focused:** Do not turn the bot into a general-purpose chatbot.
2. **Human-controlled publishing:** AI must not independently publish new assignments.
3. **Reliable scheduling:** Reminders must work without administrator intervention.
4. **Original preservation:** Never discard the source assignment document or image.
5. **Accuracy over assumptions:** Missing or uncertain information must be identified.
6. **Minimal friction:** Students should not need accounts or additional applications.
7. **Simple architecture:** Prefer straightforward, maintainable implementation.
8. **Useful over sophisticated:** Build what solves the actual classroom problem.

---

## 17. Final Product Vision

Class Assignment Bot should become the class's dependable assignment record and reminder system.

A student should be able to open the class WhatsApp group and quickly discover:

- What assignments are available?
- Which course does each assignment belong to?
- What exactly are the instructions?
- When is each assignment due?
- Which assignments are approaching their deadlines?

The administrator should not need to manually track every assignment or remember when reminders should be sent.

The system should take care of that.

**The ultimate objective is simple: No student should miss an assignment simply because they forgot it was announced.**

---

**End of PRD — Version 1.0**
