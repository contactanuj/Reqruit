"""
Interview preparation routes (Stage 4: Prepare).

Endpoints for managing STAR stories, interview schedules,
AI-generated behavioral questions, and mock interview sessions.
"""

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel

from datetime import datetime

from src.api.dependencies import (
    get_application_repository,
    get_current_user,
    get_interview_repository,
    get_job_repository,
    get_mock_session_repository,
    get_star_story_repository,
)
from src.core.exceptions import BusinessValidationError, NotFoundError
from src.db.documents.enums import InterviewType, MockSessionStatus
from src.agents.interview_prep import BehavioralQuestionGenerator
from src.db.documents.interview import GeneratedQuestion, Interview, InterviewNotes
from src.db.documents.mock_session import MockInterviewSession
from src.db.documents.star_story import STARStory
from src.db.documents.user import User
from src.repositories.application_repository import ApplicationRepository
from src.repositories.interview_repository import InterviewRepository
from src.repositories.job_repository import JobRepository
from src.repositories.mock_session_repository import MockSessionRepository
from src.repositories.star_story_repository import STARStoryRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/interviews", tags=["interviews"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class CreateSTARStoryRequest(BaseModel):
    title: str
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    tags: list[str] = []


class UpdateSTARStoryRequest(BaseModel):
    title: str | None = None
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    tags: list[str] | None = None


class STARStoryResponse(BaseModel):
    id: str
    title: str
    situation: str
    task: str
    action: str
    result: str
    tags: list[str]
    created_at: str | None
    updated_at: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _story_to_response(story: STARStory) -> STARStoryResponse:
    return STARStoryResponse(
        id=str(story.id),
        title=story.title,
        situation=story.situation,
        task=story.task,
        action=story.action,
        result=story.result,
        tags=story.tags,
        created_at=story.created_at.isoformat() if story.created_at else None,
        updated_at=story.updated_at.isoformat() if story.updated_at else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/star-stories", status_code=201, response_model=STARStoryResponse)
async def create_star_story(
    body: CreateSTARStoryRequest,
    current_user: User = Depends(get_current_user),
    repo: STARStoryRepository = Depends(get_star_story_repository),
) -> STARStoryResponse:
    """Create a new STAR story for the current user."""
    story = STARStory(
        user_id=current_user.id,
        title=body.title,
        situation=body.situation,
        task=body.task,
        action=body.action,
        result=body.result,
        tags=body.tags,
    )
    story = await repo.create(story)
    logger.info(
        "star_story_created",
        user_id=str(current_user.id),
        story_id=str(story.id),
    )
    return _story_to_response(story)


@router.get("/star-stories", response_model=list[STARStoryResponse])
async def list_star_stories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    repo: STARStoryRepository = Depends(get_star_story_repository),
) -> list[STARStoryResponse]:
    """List all STAR stories for the current user, newest first."""
    stories = await repo.get_all_for_user(current_user.id, skip=skip, limit=limit)
    return [_story_to_response(s) for s in stories]


@router.get("/star-stories/{story_id}", response_model=STARStoryResponse)
async def get_star_story(
    story_id: str,
    current_user: User = Depends(get_current_user),
    repo: STARStoryRepository = Depends(get_star_story_repository),
) -> STARStoryResponse:
    """Get a single STAR story by ID."""
    story = await repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(story_id)
    )
    if not story:
        raise NotFoundError("STARStory", story_id)
    return _story_to_response(story)


@router.patch("/star-stories/{story_id}", response_model=STARStoryResponse)
async def update_star_story(
    story_id: str,
    body: UpdateSTARStoryRequest,
    current_user: User = Depends(get_current_user),
    repo: STARStoryRepository = Depends(get_star_story_repository),
) -> STARStoryResponse:
    """Partially update a STAR story."""
    story = await repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(story_id)
    )
    if not story:
        raise NotFoundError("STARStory", story_id)

    update_data: dict = {}
    if body.title is not None:
        update_data["title"] = body.title
    if body.situation is not None:
        update_data["situation"] = body.situation
    if body.task is not None:
        update_data["task"] = body.task
    if body.action is not None:
        update_data["action"] = body.action
    if body.result is not None:
        update_data["result"] = body.result
    if body.tags is not None:
        update_data["tags"] = body.tags

    if update_data:
        updated = await repo.update(PydanticObjectId(story_id), update_data)
        story = updated or story

    logger.info(
        "star_story_updated",
        user_id=str(current_user.id),
        story_id=story_id,
    )
    return _story_to_response(story)


@router.delete("/star-stories/{story_id}", status_code=204)
async def delete_star_story(
    story_id: str,
    current_user: User = Depends(get_current_user),
    repo: STARStoryRepository = Depends(get_star_story_repository),
) -> Response:
    """Delete a STAR story."""
    story = await repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(story_id)
    )
    if not story:
        raise NotFoundError("STARStory", story_id)

    await repo.delete(PydanticObjectId(story_id))
    logger.info(
        "star_story_deleted",
        user_id=str(current_user.id),
        story_id=story_id,
    )
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Interview request / response schemas
# ---------------------------------------------------------------------------


class CreateInterviewRequest(BaseModel):
    application_id: str
    scheduled_at: datetime | None = None
    interview_type: InterviewType = InterviewType.PHONE_SCREEN
    interviewer_name: str = ""
    notes_key_points: list[str] = []
    notes_follow_up_items: list[str] = []


class UpdateInterviewRequest(BaseModel):
    scheduled_at: datetime | None = None
    interview_type: InterviewType | None = None
    interviewer_name: str | None = None
    notes_key_points: list[str] | None = None
    notes_follow_up_items: list[str] | None = None
    preparation_notes: str | None = None


class InterviewResponse(BaseModel):
    id: str
    application_id: str
    user_id: str
    scheduled_at: str | None
    interview_type: str
    company_name: str
    role_title: str
    interviewer_name: str
    notes: dict
    questions: list[str]
    preparation_notes: str
    created_at: str | None
    updated_at: str | None


# ---------------------------------------------------------------------------
# Interview helpers
# ---------------------------------------------------------------------------


def _interview_to_response(interview: Interview) -> InterviewResponse:
    return InterviewResponse(
        id=str(interview.id),
        application_id=str(interview.application_id),
        user_id=str(interview.user_id),
        scheduled_at=interview.scheduled_at.isoformat() if interview.scheduled_at else None,
        interview_type=interview.interview_type,
        company_name=interview.company_name,
        role_title=interview.role_title,
        interviewer_name=interview.interviewer_name,
        notes=interview.notes.model_dump(),
        questions=interview.questions,
        preparation_notes=interview.preparation_notes,
        created_at=interview.created_at.isoformat() if interview.created_at else None,
        updated_at=interview.updated_at.isoformat() if interview.updated_at else None,
    )


# ---------------------------------------------------------------------------
# Interview endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201, response_model=InterviewResponse)
async def create_interview(
    body: CreateInterviewRequest,
    current_user: User = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    job_repo: JobRepository = Depends(get_job_repository),
) -> InterviewResponse:
    """Create a new interview linked to an application."""
    application = await app_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(body.application_id)
    )
    if not application:
        raise NotFoundError("Application", body.application_id)

    job = await job_repo.get_by_id(application.job_id)
    company_name = job.company_name if job else "Unknown"
    role_title = job.title if job else "Unknown"

    interview = Interview(
        user_id=current_user.id,
        application_id=PydanticObjectId(body.application_id),
        scheduled_at=body.scheduled_at,
        interview_type=body.interview_type,
        company_name=company_name,
        role_title=role_title,
        interviewer_name=body.interviewer_name,
        notes=InterviewNotes(
            key_points=body.notes_key_points,
            follow_up_items=body.notes_follow_up_items,
        ),
    )
    interview = await interview_repo.create(interview)
    logger.info(
        "interview_created",
        user_id=str(current_user.id),
        interview_id=str(interview.id),
        company_name=company_name,
    )
    return _interview_to_response(interview)


@router.get("", response_model=list[InterviewResponse])
async def list_interviews(
    application_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> list[InterviewResponse]:
    """List interviews for the current user, sorted by scheduled_at ascending."""
    app_oid = PydanticObjectId(application_id) if application_id else None
    interviews = await interview_repo.get_for_user(
        current_user.id, application_id=app_oid, skip=skip, limit=limit
    )
    return [_interview_to_response(i) for i in interviews]


@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: str,
    current_user: User = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> InterviewResponse:
    """Get a single interview by ID."""
    interview = await interview_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(interview_id)
    )
    if not interview:
        raise NotFoundError("Interview", interview_id)
    return _interview_to_response(interview)


@router.patch("/{interview_id}", response_model=InterviewResponse)
async def update_interview(
    interview_id: str,
    body: UpdateInterviewRequest,
    current_user: User = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> InterviewResponse:
    """Partial update of an interview."""
    interview = await interview_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(interview_id)
    )
    if not interview:
        raise NotFoundError("Interview", interview_id)

    update_data: dict = {}
    if body.scheduled_at is not None:
        update_data["scheduled_at"] = body.scheduled_at
    if body.interview_type is not None:
        update_data["interview_type"] = body.interview_type
    if body.interviewer_name is not None:
        update_data["interviewer_name"] = body.interviewer_name
    if body.preparation_notes is not None:
        update_data["preparation_notes"] = body.preparation_notes
    if body.notes_key_points is not None or body.notes_follow_up_items is not None:
        notes = interview.notes
        if body.notes_key_points is not None:
            notes.key_points = body.notes_key_points
        if body.notes_follow_up_items is not None:
            notes.follow_up_items = body.notes_follow_up_items
        update_data["notes"] = notes.model_dump()

    if update_data:
        updated = await interview_repo.update(
            PydanticObjectId(interview_id), update_data
        )
        interview = updated or interview

    logger.info(
        "interview_updated",
        user_id=str(current_user.id),
        interview_id=interview_id,
    )
    return _interview_to_response(interview)


@router.delete("/{interview_id}", status_code=204)
async def delete_interview(
    interview_id: str,
    current_user: User = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> Response:
    """Delete an interview."""
    interview = await interview_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(interview_id)
    )
    if not interview:
        raise NotFoundError("Interview", interview_id)

    await interview_repo.delete(PydanticObjectId(interview_id))
    logger.info(
        "interview_deleted",
        user_id=str(current_user.id),
        interview_id=interview_id,
    )
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Question generation schemas
# ---------------------------------------------------------------------------


class GeneratedQuestionResponse(BaseModel):
    question: str
    suggested_angle: str


class QuestionsGeneratedResponse(BaseModel):
    interview_id: str
    questions: list[GeneratedQuestionResponse]


# ---------------------------------------------------------------------------
# Question generation endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{interview_id}/questions/generate",
    status_code=201,
    response_model=QuestionsGeneratedResponse,
)
async def generate_questions(
    interview_id: str,
    current_user: User = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    job_repo: JobRepository = Depends(get_job_repository),
) -> QuestionsGeneratedResponse:
    """Generate behavioral interview questions tailored to the linked job."""
    interview = await interview_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(interview_id)
    )
    if not interview:
        raise NotFoundError("Interview", interview_id)

    application = await app_repo.get_by_user_and_id(
        current_user.id, interview.application_id
    )
    if not application:
        raise NotFoundError("Application", str(interview.application_id))

    job = await job_repo.get_by_id(application.job_id)
    if not job:
        raise NotFoundError("Job", str(application.job_id))

    agent = BehavioralQuestionGenerator()
    config = {"configurable": {"user_id": str(current_user.id)}}
    result = await agent(
        {"role_title": job.title, "job_description": job.description},
        config,
    )

    gen_questions = [
        GeneratedQuestion(question=q["question"], suggested_angle=q["suggested_angle"])
        for q in result["generated_questions"]
    ]

    await interview_repo.update(
        PydanticObjectId(interview_id),
        {"generated_questions": [q.model_dump() for q in gen_questions]},
    )

    logger.info(
        "interview_questions_generated",
        user_id=str(current_user.id),
        interview_id=interview_id,
        question_count=len(gen_questions),
    )
    return QuestionsGeneratedResponse(
        interview_id=interview_id,
        questions=[
            GeneratedQuestionResponse(
                question=q.question, suggested_angle=q.suggested_angle
            )
            for q in gen_questions
        ],
    )


@router.get(
    "/{interview_id}/questions",
    response_model=QuestionsGeneratedResponse,
)
async def get_questions(
    interview_id: str,
    current_user: User = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> QuestionsGeneratedResponse:
    """Retrieve previously generated questions without regenerating."""
    interview = await interview_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(interview_id)
    )
    if not interview:
        raise NotFoundError("Interview", interview_id)

    return QuestionsGeneratedResponse(
        interview_id=interview_id,
        questions=[
            GeneratedQuestionResponse(
                question=q.question, suggested_angle=q.suggested_angle
            )
            for q in interview.generated_questions
        ],
    )


# ---------------------------------------------------------------------------
# Mock interview session schemas
# ---------------------------------------------------------------------------


class QuestionFeedbackResponse(BaseModel):
    question: str
    user_answer: str
    ai_feedback: str
    score: int | None


class MockSessionResponse(BaseModel):
    id: str
    interview_id: str
    status: str
    question_feedbacks: list[QuestionFeedbackResponse]
    current_question_index: int
    current_question: str | None = None
    overall_feedback: str
    overall_score: int | None
    created_at: str | None
    updated_at: str | None


class SubmitAnswerRequest(BaseModel):
    answer: str


class AnswerFeedbackResponse(BaseModel):
    session_id: str
    question: str
    user_answer: str
    ai_feedback: str
    score: int | None
    next_question: str | None
    session_complete: bool


# ---------------------------------------------------------------------------
# Mock session helpers
# ---------------------------------------------------------------------------


def _session_to_response(
    session, questions: list | None = None
) -> MockSessionResponse:
    s: MockInterviewSession = session
    current_question = None
    if questions and s.current_question_index < len(questions):
        current_question = questions[s.current_question_index].question
    return MockSessionResponse(
        id=str(s.id),
        interview_id=str(s.interview_id),
        status=s.status,
        question_feedbacks=[
            QuestionFeedbackResponse(
                question=qf.question,
                user_answer=qf.user_answer,
                ai_feedback=qf.ai_feedback,
                score=qf.score,
            )
            for qf in s.question_feedbacks
        ],
        current_question_index=s.current_question_index,
        current_question=current_question,
        overall_feedback=s.overall_feedback,
        overall_score=s.overall_score,
        created_at=s.created_at.isoformat() if s.created_at else None,
        updated_at=s.updated_at.isoformat() if s.updated_at else None,
    )


# ---------------------------------------------------------------------------
# Mock session endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{interview_id}/mock-sessions",
    status_code=201,
    response_model=MockSessionResponse,
)
async def start_mock_session(
    interview_id: str,
    current_user: User = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    session_repo: MockSessionRepository = Depends(get_mock_session_repository),
) -> MockSessionResponse:
    """Start a new mock interview session using generated questions."""
    interview = await interview_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(interview_id)
    )
    if not interview:
        raise NotFoundError("Interview", interview_id)

    if not interview.generated_questions:
        raise BusinessValidationError(
            "No generated questions available. Generate questions first.",
            error_code="NO_QUESTIONS",
        )

    from src.db.documents.mock_session import MockInterviewSession

    # Idempotent: return existing IN_PROGRESS session if one exists
    existing = await session_repo.find_one(
        {
            "user_id": current_user.id,
            "interview_id": PydanticObjectId(interview_id),
            "status": MockSessionStatus.IN_PROGRESS,
        }
    )
    if existing:
        return _session_to_response(existing, questions=interview.generated_questions)

    session = MockInterviewSession(
        user_id=current_user.id,
        interview_id=PydanticObjectId(interview_id),
        status=MockSessionStatus.IN_PROGRESS,
    )
    session = await session_repo.create(session)
    logger.info(
        "mock_session_started",
        user_id=str(current_user.id),
        interview_id=interview_id,
        session_id=str(session.id),
    )
    return _session_to_response(session, questions=interview.generated_questions)


@router.get(
    "/{interview_id}/mock-sessions",
    response_model=list[MockSessionResponse],
)
async def list_mock_sessions(
    interview_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    session_repo: MockSessionRepository = Depends(get_mock_session_repository),
) -> list[MockSessionResponse]:
    """List mock sessions for an interview."""
    interview = await interview_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(interview_id)
    )
    if not interview:
        raise NotFoundError("Interview", interview_id)

    sessions = await session_repo.get_for_interview(
        current_user.id, PydanticObjectId(interview_id), skip=skip, limit=limit
    )
    return [_session_to_response(s) for s in sessions]


@router.get(
    "/{interview_id}/mock-sessions/{session_id}",
    response_model=MockSessionResponse,
)
async def get_mock_session(
    interview_id: str,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_repo: MockSessionRepository = Depends(get_mock_session_repository),
) -> MockSessionResponse:
    """Get a specific mock session."""
    session = await session_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(session_id)
    )
    if not session or str(session.interview_id) != interview_id:
        raise NotFoundError("MockSession", session_id)
    return _session_to_response(session)


@router.post(
    "/{interview_id}/mock-sessions/{session_id}/answer",
    response_model=AnswerFeedbackResponse,
)
async def submit_answer(
    interview_id: str,
    session_id: str,
    body: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    session_repo: MockSessionRepository = Depends(get_mock_session_repository),
) -> AnswerFeedbackResponse:
    """Submit an answer to the current question and get AI feedback."""
    session = await session_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(session_id)
    )
    if not session or str(session.interview_id) != interview_id:
        raise NotFoundError("MockSession", session_id)

    if session.status != MockSessionStatus.IN_PROGRESS:
        raise BusinessValidationError(
            "Session is not in progress.", error_code="SESSION_NOT_IN_PROGRESS"
        )

    interview = await interview_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(interview_id)
    )
    if not interview:
        raise NotFoundError("Interview", interview_id)

    questions = interview.generated_questions
    if session.current_question_index >= len(questions):
        raise BusinessValidationError(
            "All questions have been answered.", error_code="NO_MORE_QUESTIONS"
        )

    current_q = questions[session.current_question_index]

    from src.agents.interview_prep import MockInterviewer

    agent = MockInterviewer()
    config = {"configurable": {"user_id": str(current_user.id)}}
    result = await agent(
        {"question": current_q.question, "user_answer": body.answer},
        config,
    )

    from src.db.documents.mock_session import QuestionFeedback

    feedback = QuestionFeedback(
        question=current_q.question,
        user_answer=body.answer,
        ai_feedback=result["feedback"],
        score=result.get("score"),
    )

    new_index = session.current_question_index + 1
    updated_feedbacks = [qf.model_dump() for qf in session.question_feedbacks]
    updated_feedbacks.append(feedback.model_dump())

    await session_repo.update(
        PydanticObjectId(session_id),
        {
            "question_feedbacks": updated_feedbacks,
            "current_question_index": new_index,
        },
    )

    next_question = (
        questions[new_index].question if new_index < len(questions) else None
    )
    session_complete = new_index >= len(questions)

    logger.info(
        "mock_session_answer_submitted",
        user_id=str(current_user.id),
        session_id=session_id,
        question_index=session.current_question_index,
    )

    return AnswerFeedbackResponse(
        session_id=session_id,
        question=current_q.question,
        user_answer=body.answer,
        ai_feedback=result["feedback"],
        score=result.get("score"),
        next_question=next_question,
        session_complete=session_complete,
    )


@router.post(
    "/{interview_id}/mock-sessions/{session_id}/complete",
    response_model=MockSessionResponse,
)
async def complete_mock_session(
    interview_id: str,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_repo: MockSessionRepository = Depends(get_mock_session_repository),
) -> MockSessionResponse:
    """Complete a mock session and generate overall feedback."""
    session = await session_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(session_id)
    )
    if not session or str(session.interview_id) != interview_id:
        raise NotFoundError("MockSession", session_id)

    if session.status != MockSessionStatus.IN_PROGRESS:
        raise BusinessValidationError(
            "Session is not in progress.", error_code="SESSION_NOT_IN_PROGRESS"
        )

    if not session.question_feedbacks:
        raise BusinessValidationError(
            "No answers submitted yet.", error_code="NO_ANSWERS",
        )

    # Build transcript for the summarizer
    transcript_parts = []
    for i, qf in enumerate(session.question_feedbacks, 1):
        transcript_parts.append(
            f"Q{i}: {qf.question}\n"
            f"Answer: {qf.user_answer}\n"
            f"Feedback: {qf.ai_feedback}\n"
            f"Score: {qf.score}/10"
        )
    transcript = "\n\n".join(transcript_parts)

    from src.agents.interview_prep import MockInterviewSummarizer

    agent = MockInterviewSummarizer()
    config = {"configurable": {"user_id": str(current_user.id)}}
    result = await agent({"session_transcript": transcript}, config)

    await session_repo.update(
        PydanticObjectId(session_id),
        {
            "status": MockSessionStatus.COMPLETED,
            "overall_feedback": result["overall_feedback"],
            "overall_score": result.get("overall_score"),
        },
    )

    updated = await session_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(session_id)
    )
    logger.info(
        "mock_session_completed",
        user_id=str(current_user.id),
        session_id=session_id,
        overall_score=result.get("overall_score"),
    )
    return _session_to_response(updated)


@router.delete("/{interview_id}/mock-sessions/{session_id}", status_code=204)
async def delete_mock_session(
    interview_id: str,
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_repo: MockSessionRepository = Depends(get_mock_session_repository),
) -> Response:
    """Delete a mock session."""
    session = await session_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(session_id)
    )
    if not session or str(session.interview_id) != interview_id:
        raise NotFoundError("MockSession", session_id)

    await session_repo.delete(PydanticObjectId(session_id))
    logger.info(
        "mock_session_deleted",
        user_id=str(current_user.id),
        session_id=session_id,
    )
    return Response(status_code=204)
