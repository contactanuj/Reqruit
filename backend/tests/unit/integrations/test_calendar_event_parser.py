"""Tests for CalendarEventParser interview detection."""

from datetime import UTC, datetime, timedelta

from src.integrations.calendar_event_parser import CalendarEventParser
from src.integrations.google_calendar_client import CalendarEvent


def _event(
    summary="",
    organizer_email=None,
    attendees=None,
    start_time=None,
):
    return CalendarEvent(
        event_id="evt1",
        summary=summary,
        start_time=start_time or datetime.now(UTC),
        end_time=None,
        organizer_email=organizer_email,
        attendees=attendees or [],
        status="confirmed",
    )


class TestIsInterviewEvent:
    def setup_method(self):
        self.parser = CalendarEventParser()
        self.tracked = ["Google", "Meta", "Stripe"]

    def test_title_and_organizer_match(self):
        event = _event(
            summary="Technical Interview with Google Engineering",
            organizer_email="hr@google.com",
        )
        result = self.parser.is_interview_event(event, self.tracked)
        assert result is not None
        assert result.confidence == 0.95
        assert result.company_name == "Google"
        assert result.match_source == "organizer"

    def test_title_and_attendee_match(self):
        event = _event(
            summary="Hiring Manager Discussion",
            attendees=["recruiter@meta.com"],
        )
        result = self.parser.is_interview_event(event, self.tracked)
        assert result is not None
        assert result.confidence == 0.95
        assert result.company_name == "Meta"

    def test_title_keyword_only(self):
        event = _event(
            summary="Phone Screen - Software Engineer",
            organizer_email="interviewer@unknown.com",
        )
        result = self.parser.is_interview_event(event, self.tracked)
        assert result is not None
        assert result.confidence == 0.7
        assert result.match_source == "title"

    def test_final_round_title(self):
        result = self.parser.is_interview_event(
            _event(summary="Final Round Onsite"), self.tracked
        )
        assert result is not None
        assert result.confidence == 0.7

    def test_coding_round_title(self):
        result = self.parser.is_interview_event(
            _event(summary="Coding Round with Team"), self.tracked
        )
        assert result is not None
        assert result.matched_pattern == "calendar_interview"

    def test_recruiter_call_title(self):
        result = self.parser.is_interview_event(
            _event(summary="Recruiter Call - Initial Screen"), self.tracked
        )
        assert result is not None

    def test_company_domain_in_attendees_only(self):
        event = _event(
            summary="Meeting with Team",
            attendees=["pm@stripe.com", "eng@stripe.com"],
        )
        result = self.parser.is_interview_event(event, self.tracked)
        assert result is not None
        assert result.confidence == 0.6
        assert result.company_name == "Stripe"

    def test_team_lunch_returns_none(self):
        result = self.parser.is_interview_event(
            _event(summary="Team Lunch"), self.tracked
        )
        assert result is None

    def test_doctor_appointment_returns_none(self):
        result = self.parser.is_interview_event(
            _event(summary="Doctor Appointment"), self.tracked
        )
        assert result is None

    def test_one_on_one_returns_none(self):
        result = self.parser.is_interview_event(
            _event(summary="1:1 with Manager"), self.tracked
        )
        assert result is None

    def test_no_match_no_tracked_company(self):
        result = self.parser.is_interview_event(
            _event(summary="Grocery shopping"), []
        )
        assert result is None

    def test_event_date_preserved(self):
        dt = datetime(2026, 3, 25, 14, 0, tzinfo=UTC)
        event = _event(summary="Technical Screen", start_time=dt)
        result = self.parser.is_interview_event(event, self.tracked)
        assert result is not None
        assert result.event_date == dt


class TestNudgeEligible:
    def test_event_5_days_out_is_eligible(self):
        future = datetime.now(UTC) + timedelta(days=5)
        assert CalendarEventParser.is_nudge_eligible(future) is True

    def test_event_tomorrow_not_eligible(self):
        tomorrow = datetime.now(UTC) + timedelta(days=1)
        assert CalendarEventParser.is_nudge_eligible(tomorrow) is False

    def test_event_exactly_3_days_out_not_eligible(self):
        # Must be MORE than 3 days
        three_days = datetime.now(UTC) + timedelta(days=3, seconds=1)
        assert CalendarEventParser.is_nudge_eligible(three_days) is True

    def test_past_event_not_eligible(self):
        past = datetime.now(UTC) - timedelta(days=1)
        assert CalendarEventParser.is_nudge_eligible(past) is False


class TestMatchCompany:
    def test_matches_by_domain_name(self):
        result = CalendarEventParser._match_company("google.com", ["Google"])
        assert result == "Google"

    def test_matches_partial_domain(self):
        result = CalendarEventParser._match_company("careers.stripe.com", ["Stripe"])
        assert result == "Stripe"

    def test_no_match_returns_none(self):
        result = CalendarEventParser._match_company("random.org", ["Google", "Meta"])
        assert result is None
