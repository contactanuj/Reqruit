"""Tests for EmailParser pattern-based signal detection."""

from datetime import datetime

from src.integrations.email_parser import EmailParser, SignalPattern


class TestParseEmail:
    def setup_method(self):
        self.parser = EmailParser()

    def test_interview_invitation_subject(self):
        result = self.parser.parse_email(
            subject="Interview Scheduled for Software Engineer",
            sender_domain="careers.google.com",
        )
        assert result is not None
        assert result.matched_pattern == "interview_invitation"
        assert result.confidence == 0.9
        assert result.status_transition == "interviewing"

    def test_rejection_subject(self):
        result = self.parser.parse_email(
            subject="Unfortunately we will not be moving forward",
            sender_domain="hr.acme.com",
        )
        assert result is not None
        assert result.matched_pattern == "rejection"
        assert result.confidence == 0.9
        assert result.status_transition == "rejected"

    def test_offer_subject(self):
        result = self.parser.parse_email(
            subject="Your Offer Letter from TechCorp",
            sender_domain="techcorp.com",
        )
        assert result is not None
        assert result.matched_pattern == "offer"
        assert result.confidence == 0.9
        assert result.status_transition == "offer_received"

    def test_application_confirmation_subject(self):
        result = self.parser.parse_email(
            subject="Thank you for applying to the Data Scientist role",
            sender_domain="jobs.company.com",
        )
        assert result is not None
        assert result.matched_pattern == "application_confirmation"
        assert result.confidence == 0.9
        assert result.status_transition == "applied"

    def test_assessment_request_subject(self):
        result = self.parser.parse_email(
            subject="Your Coding Assessment - Complete by Friday",
            sender_domain="hackerrank.com",
        )
        assert result is not None
        assert result.matched_pattern == "assessment_request"
        assert result.confidence == 0.9
        assert result.status_transition == "interviewing"

    def test_no_match_returns_none(self):
        result = self.parser.parse_email(
            subject="Weekly newsletter - Top tech stories",
            sender_domain="news.techblog.com",
        )
        assert result is None

    def test_non_job_domain_excluded(self):
        result = self.parser.parse_email(
            subject="Your order has been confirmed",
            sender_domain="amazon.com",
        )
        assert result is None

    def test_phone_screen_pattern(self):
        result = self.parser.parse_email(
            subject="Phone screen with hiring manager",
            sender_domain="talent.startup.io",
        )
        assert result is not None
        assert result.matched_pattern == "interview_invitation"

    def test_position_filled_rejection(self):
        result = self.parser.parse_email(
            subject="Update: Position has been filled",
            sender_domain="noreply.bigcorp.com",
        )
        assert result is not None
        assert result.matched_pattern == "rejection"

    def test_take_home_assessment(self):
        result = self.parser.parse_email(
            subject="Please complete the take-home challenge",
            sender_domain="recruiting.startup.com",
        )
        assert result is not None
        assert result.matched_pattern == "assessment_request"

    def test_highest_confidence_wins(self):
        """When multiple patterns could match, highest confidence is returned."""
        result = self.parser.parse_email(
            subject="Congratulations! Interview Scheduled",
            sender_domain="hr.company.com",
        )
        assert result is not None
        # "interview_invitation" matches first with 0.9
        assert result.confidence == 0.9

    def test_case_insensitive_matching(self):
        result = self.parser.parse_email(
            subject="INTERVIEW INVITATION for Backend Developer",
            sender_domain="hr.company.com",
        )
        assert result is not None
        assert result.matched_pattern == "interview_invitation"


class TestExtractCompanyName:
    def test_simple_domain(self):
        assert EmailParser.extract_company_name("google.com") == "Google"

    def test_careers_subdomain(self):
        assert EmailParser.extract_company_name("careers.google.com") == "Google"

    def test_noreply_subdomain(self):
        assert EmailParser.extract_company_name("noreply.stripe.com") == "Stripe"

    def test_hr_subdomain(self):
        assert EmailParser.extract_company_name("hr.acme.com") == "Acme"

    def test_jobs_tld(self):
        assert EmailParser.extract_company_name("amazon.jobs") == "Amazon"

    def test_recruiting_subdomain(self):
        assert EmailParser.extract_company_name("recruiting.meta.com") == "Meta"

    def test_talent_subdomain(self):
        assert EmailParser.extract_company_name("talent.startup.io") == "Startup"


class TestExtractEventDate:
    def test_month_day_year(self):
        result = EmailParser.extract_event_date("Interview on March 15, 2026")
        assert result == datetime(2026, 3, 15)

    def test_slash_format(self):
        result = EmailParser.extract_event_date("Meeting on 3/15/2026")
        assert result == datetime(2026, 3, 15)

    def test_month_day_no_year(self):
        result = EmailParser.extract_event_date("Interview on March 15")
        assert result is not None
        assert result.month == 3
        assert result.day == 15

    def test_no_date_returns_none(self):
        result = EmailParser.extract_event_date("Thank you for applying")
        assert result is None

    def test_invalid_date_returns_none(self):
        result = EmailParser.extract_event_date("Meeting on 13/45/2026")
        assert result is None


class TestCustomPatterns:
    def test_custom_pattern_used(self):
        import re

        custom = [
            SignalPattern(
                name="custom_signal",
                subject_patterns=[re.compile(r"custom\s+pattern", re.I)],
                status_transition="custom_status",
            )
        ]
        parser = EmailParser(patterns=custom)
        result = parser.parse_email(
            subject="This is a custom pattern test",
            sender_domain="example.com",
        )
        assert result is not None
        assert result.matched_pattern == "custom_signal"
        assert result.status_transition == "custom_status"
