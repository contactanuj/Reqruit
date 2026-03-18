"""Morale service — burnout detection, morale dashboard, and proactive intervention.

All calculations are DETERMINISTIC (no LLM). The system uses pattern matching
and threshold checks on activity data to detect fatigue and compute morale indicators.
"""

from datetime import UTC, datetime, timedelta

import structlog
from beanie import PydanticObjectId
from pydantic import BaseModel

from src.repositories.user_activity_repository import UserActivityRepository

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HIGH_XP_ACTIONS = {"mock_interview_completed", "star_story_created"}
LOW_XP_ACTIONS = {"job_saved"}

QUALITY_RATIO_DECLINE_THRESHOLD = 0.50  # 50% drop in high/low ratio
LATE_NIGHT_ACTION_THRESHOLD = 3  # actions between 23:00-05:00
SESSION_DURATION_DECLINE_THRESHOLD = 0.40  # 40% drop over 7 days
BURST_APPLICATION_THRESHOLD = 10  # applications in 2-hour window
BURST_WINDOW_HOURS = 2

MORALE_TREND_THRESHOLD = 0.10  # 10% change for improving/declining
GHOSTING_DAYS = 14  # no response after 14 days
INTERVENTION_NEGATIVE_INDICATORS = 2  # 2+ indicators negative
INTERVENTION_CONSECUTIVE_DAYS = 7  # for 7+ days


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class BurnoutSignal(BaseModel):
    signal_type: str
    description: str
    recommendation: str
    severity: str  # low, medium, high


class BurnoutResult(BaseModel):
    signals: list[BurnoutSignal]
    has_warning: bool
    overall_severity: str  # low, medium, high
    recommendation: str


class MoraleDashboard(BaseModel):
    response_rate_trend: str  # improving, stable, declining
    ghosting_frequency: int
    ghosting_percentage: float
    interview_conversion_rate: float
    time_since_last_positive_signal: int  # days


class InterventionResult(BaseModel):
    triggered_indicators: list[str]
    consecutive_negative_days: int
    recommendations: list[str]
    rest_suggestion: str | None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class MoraleService:
    """Deterministic burnout detection, morale dashboard, and intervention logic."""

    def __init__(self, user_activity_repo: UserActivityRepository) -> None:
        self._repo = user_activity_repo

    # --- Fatigue Signal 1: Declining action quality ---

    def detect_declining_quality(
        self, current_week_actions: list, previous_week_actions: list
    ) -> BurnoutSignal | None:
        """Track ratio of high-XP to low-XP actions. Flag if ratio drops >50% WoW."""
        prev_ratio = self._quality_ratio(previous_week_actions)
        curr_ratio = self._quality_ratio(current_week_actions)

        if prev_ratio == 0:
            return None

        decline = (prev_ratio - curr_ratio) / prev_ratio
        if decline > QUALITY_RATIO_DECLINE_THRESHOLD:
            prev_pct = round(prev_ratio * 100, 1)
            curr_pct = round(curr_ratio * 100, 1)
            return BurnoutSignal(
                signal_type="declining_quality",
                description=(
                    f"Quality action ratio dropped from {prev_pct}% to {curr_pct}% "
                    f"({round(decline * 100, 1)}% decline)"
                ),
                recommendation=(
                    f"Your high-value action ratio dropped from {prev_pct}% to {curr_pct}%. "
                    "Consider doing 1 mock interview or creating a STAR story before "
                    "your next batch of applications."
                ),
                severity="medium",
            )
        return None

    @staticmethod
    def _quality_ratio(actions: list) -> float:
        """Ratio of high-XP actions to total actions."""
        if not actions:
            return 0.0
        high_count = sum(1 for a in actions if a.action_type in HIGH_XP_ACTIONS)
        total = len(actions)
        return high_count / total if total > 0 else 0.0

    # --- Fatigue Signal 2: Late-night activity spikes ---

    def detect_late_night_activity(
        self, day_actions: list
    ) -> BurnoutSignal | None:
        """Detect >3 actions between 23:00-05:00 in a single day."""
        late_count = 0
        for action in day_actions:
            hour = action.timestamp.hour
            if hour >= 23 or hour < 5:
                late_count += 1

        if late_count >= LATE_NIGHT_ACTION_THRESHOLD:
            return BurnoutSignal(
                signal_type="late_night_activity",
                description=(
                    f"{late_count} actions recorded between 23:00-05:00"
                ),
                recommendation=(
                    f"You had {late_count} actions between 23:00-05:00. "
                    "Late-night job searching correlates with lower quality applications. "
                    "Try to do your most important applications before 20:00."
                ),
                severity="medium",
            )
        return None

    # --- Fatigue Signal 3: Decreasing session duration ---

    def detect_decreasing_session_duration(
        self, daily_activities: list,
    ) -> BurnoutSignal | None:
        """Track session duration (first to last action per day) over 7 days.

        Flag if average drops >40%.
        """
        if len(daily_activities) < 4:
            return None

        durations = []
        for activity in daily_activities:
            if len(activity.actions) < 2:
                durations.append(0.0)
                continue
            timestamps = sorted(a.timestamp for a in activity.actions)
            duration_mins = (timestamps[-1] - timestamps[0]).total_seconds() / 60
            durations.append(duration_mins)

        mid = len(durations) // 2
        first_half = durations[:mid]
        second_half = durations[mid:]

        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0

        if avg_first == 0:
            return None

        decline = (avg_first - avg_second) / avg_first
        if decline > SESSION_DURATION_DECLINE_THRESHOLD:
            return BurnoutSignal(
                signal_type="decreasing_session_duration",
                description=(
                    f"Average session duration dropped {round(decline * 100, 1)}% "
                    f"(from {round(avg_first, 0)} to {round(avg_second, 0)} minutes)"
                ),
                recommendation=(
                    f"Your session duration dropped from {round(avg_first, 0)} to "
                    f"{round(avg_second, 0)} minutes. Shorter sessions often mean "
                    "less focused work. Consider scheduling 2-3 dedicated 45-minute "
                    "blocks per week instead of frequent short sessions."
                ),
                severity="low",
            )
        return None

    # --- Fatigue Signal 4: High-volume-low-quality bursts ---

    def detect_burst_applications(
        self, day_actions: list
    ) -> BurnoutSignal | None:
        """Detect >10 application_submitted in a 2-hour window."""
        app_timestamps = sorted(
            a.timestamp for a in day_actions
            if a.action_type == "application_submitted"
        )

        if len(app_timestamps) < BURST_APPLICATION_THRESHOLD:
            return None

        window = timedelta(hours=BURST_WINDOW_HOURS)
        for i in range(len(app_timestamps)):
            count = 1
            for j in range(i + 1, len(app_timestamps)):
                if app_timestamps[j] - app_timestamps[i] <= window:
                    count += 1
                else:
                    break
            if count >= BURST_APPLICATION_THRESHOLD:
                return BurnoutSignal(
                    signal_type="high_volume_burst",
                    description=(
                        f"{count} applications submitted in a {BURST_WINDOW_HOURS}-hour window"
                    ),
                    recommendation=(
                        f"You've submitted {count} applications in the last "
                        f"{BURST_WINDOW_HOURS} hours. Quality drops with volume. "
                        "Consider taking tomorrow off and focusing on 3 targeted "
                        "applications Wednesday."
                    ),
                    severity="high",
                )
        return None

    # --- Burnout detection (combines all 4 signals) ---

    async def detect_burnout(self, user_id: PydanticObjectId) -> BurnoutResult:
        """Run all 4 fatigue detectors and return combined result."""
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)

        current_activities = await self._repo.get_history(user_id, week_ago, now)
        previous_activities = await self._repo.get_history(user_id, two_weeks_ago, week_ago)

        signals: list[BurnoutSignal] = []

        # Signal 1: declining quality
        curr_actions = [a for act in current_activities for a in act.actions]
        prev_actions = [a for act in previous_activities for a in act.actions]
        s1 = self.detect_declining_quality(curr_actions, prev_actions)
        if s1:
            signals.append(s1)

        # Signal 2: late-night activity (check today)
        today_activities = [
            a for act in current_activities
            if (now - act.date).days < 1
            for a in act.actions
        ]
        if today_activities:
            s2 = self.detect_late_night_activity(today_activities)
            if s2:
                signals.append(s2)

        # Signal 3: decreasing session duration
        s3 = self.detect_decreasing_session_duration(current_activities)
        if s3:
            signals.append(s3)

        # Signal 4: burst applications (check today)
        if today_activities:
            s4 = self.detect_burst_applications(today_activities)
            if s4:
                signals.append(s4)

        # Determine overall severity
        if not signals:
            overall = "low"
        elif any(s.severity == "high" for s in signals):
            overall = "high"
        elif len(signals) >= 2:
            overall = "high"
        else:
            overall = "medium"

        # Build recommendation
        if signals:
            recommendation = signals[0].recommendation
        else:
            recommendation = "No burnout signals detected. Keep up your balanced approach!"

        return BurnoutResult(
            signals=signals,
            has_warning=len(signals) > 0,
            overall_severity=overall,
            recommendation=recommendation,
        )

    # --- Morale Dashboard (4 indicators) ---

    async def compute_morale(self, user_id: PydanticObjectId) -> MoraleDashboard:
        """Calculate all 4 morale indicators (deterministic, no LLM)."""
        now = datetime.now(UTC)
        fourteen_days_ago = now - timedelta(days=14)
        twenty_eight_days_ago = now - timedelta(days=28)
        thirty_days_ago = now - timedelta(days=30)

        recent_activities = await self._repo.get_history(user_id, fourteen_days_ago, now)
        older_activities = await self._repo.get_history(user_id, twenty_eight_days_ago, fourteen_days_ago)
        month_activities = await self._repo.get_history(user_id, thirty_days_ago, now)

        # 1. response_rate_trend
        response_rate_trend = self._compute_response_rate_trend(
            recent_activities, older_activities
        )

        # 2. ghosting_frequency
        ghosting_count, ghosting_pct = self._compute_ghosting_frequency(
            month_activities, now
        )

        # 3. interview_conversion_rate
        interview_rate = self._compute_interview_conversion(month_activities)

        # 4. time_since_last_positive_signal
        all_activities = await self._repo.get_history(
            user_id, now - timedelta(days=90), now
        )
        days_since_positive = self._compute_days_since_positive(
            all_activities, now
        )

        return MoraleDashboard(
            response_rate_trend=response_rate_trend,
            ghosting_frequency=ghosting_count,
            ghosting_percentage=ghosting_pct,
            interview_conversion_rate=interview_rate,
            time_since_last_positive_signal=days_since_positive,
        )

    def _compute_response_rate_trend(
        self, recent: list, older: list
    ) -> str:
        """Compare response rate over last 14 days vs previous 14 days."""
        recent_apps, recent_responses = self._count_apps_and_responses(recent)
        older_apps, older_responses = self._count_apps_and_responses(older)

        recent_rate = recent_responses / recent_apps if recent_apps > 0 else 0.0
        older_rate = older_responses / older_apps if older_apps > 0 else 0.0

        if older_rate == 0:
            return "stable" if recent_rate == 0 else "improving"

        change = (recent_rate - older_rate) / older_rate
        if change > MORALE_TREND_THRESHOLD:
            return "improving"
        elif change < -MORALE_TREND_THRESHOLD:
            return "declining"
        return "stable"

    def _compute_ghosting_frequency(
        self, month_activities: list, now: datetime
    ) -> tuple[int, float]:
        """Count applications with no response after 14+ days."""
        total_apps = 0
        ghosted = 0

        for activity in month_activities:
            for action in activity.actions:
                if action.action_type == "application_submitted":
                    total_apps += 1
                    days_since = (now - action.timestamp).days
                    if days_since >= GHOSTING_DAYS:
                        ghosted += 1

        pct = round((ghosted / total_apps) * 100, 1) if total_apps > 0 else 0.0
        return ghosted, pct

    def _compute_interview_conversion(self, month_activities: list) -> float:
        """Interviews / applications over last 30 days."""
        apps = 0
        interviews = 0
        for activity in month_activities:
            for action in activity.actions:
                if action.action_type == "application_submitted":
                    apps += 1
                elif action.action_type == "interview_prepped":
                    interviews += 1
        return round((interviews / apps) * 100, 1) if apps > 0 else 0.0

    def _compute_days_since_positive(
        self, activities: list, now: datetime
    ) -> int:
        """Days since last view, response, or interview invitation."""
        positive_types = {"interview_prepped", "mock_interview_completed"}
        latest = None

        for activity in activities:
            for action in activity.actions:
                if action.action_type in positive_types:
                    if latest is None or action.timestamp > latest:
                        latest = action.timestamp

        if latest is None:
            return 90  # max lookback
        return (now - latest).days

    @staticmethod
    def _count_apps_and_responses(activities: list) -> tuple[int, int]:
        apps = 0
        responses = 0
        for activity in activities:
            for action in activity.actions:
                if action.action_type == "application_submitted":
                    apps += 1
                elif action.action_type == "mock_interview_completed":
                    responses += 1
        return apps, responses

    # --- Proactive Intervention ---

    async def check_intervention_needed(
        self, user_id: PydanticObjectId
    ) -> InterventionResult | None:
        """Check if 2+ morale indicators have been negative for 7+ consecutive days."""
        now = datetime.now(UTC)
        negative_streak = 0
        triggered_indicators: list[str] = []

        # Check the last 7 days, each day computing morale snapshot
        for day_offset in range(INTERVENTION_CONSECUTIVE_DAYS):
            check_date = now - timedelta(days=day_offset)
            day_start = check_date.replace(hour=0, minute=0, second=0, microsecond=0)
            fourteen_before = day_start - timedelta(days=14)
            twenty_eight_before = day_start - timedelta(days=28)

            recent = await self._repo.get_history(user_id, fourteen_before, day_start)
            older = await self._repo.get_history(user_id, twenty_eight_before, fourteen_before)

            # Count negative indicators for this day
            negative_count = 0
            day_negative: list[str] = []

            # 1. response rate declining
            trend = self._compute_response_rate_trend(recent, older)
            if trend == "declining":
                negative_count += 1
                day_negative.append("response_rate_trend")

            # 2. high ghosting (>50%)
            month_activities = await self._repo.get_history(
                user_id, day_start - timedelta(days=30), day_start
            )
            _, ghost_pct = self._compute_ghosting_frequency(month_activities, day_start)
            if ghost_pct > 50:
                negative_count += 1
                day_negative.append("ghosting_frequency")

            # 3. low interview conversion (<10%)
            conv = self._compute_interview_conversion(month_activities)
            if conv < 10:
                negative_count += 1
                day_negative.append("interview_conversion_rate")

            # 4. long time since positive (>14 days)
            all_acts = await self._repo.get_history(
                user_id, day_start - timedelta(days=90), day_start
            )
            days_pos = self._compute_days_since_positive(all_acts, day_start)
            if days_pos > 14:
                negative_count += 1
                day_negative.append("time_since_last_positive_signal")

            if negative_count >= INTERVENTION_NEGATIVE_INDICATORS:
                negative_streak += 1
                triggered_indicators = day_negative
            else:
                break  # streak broken

        if negative_streak < INTERVENTION_CONSECUTIVE_DAYS:
            return None

        # Build actionable recommendations from triggered indicators
        recommendations = []
        for indicator in triggered_indicators:
            if indicator == "response_rate_trend":
                recommendations.append(
                    "Your response rate is declining. Review your resume's "
                    "top 3 bullet points and ensure they have quantified achievements."
                )
            elif indicator == "ghosting_frequency":
                recommendations.append(
                    f"Over 50% of your applications got no response. "
                    "Consider targeting smaller companies (50-200 employees) "
                    "where your application gets more visibility."
                )
            elif indicator == "interview_conversion_rate":
                recommendations.append(
                    "Your interview conversion is below 10%. Consider doing "
                    "2 mock interviews before your next real one to sharpen "
                    "your talking points."
                )
            elif indicator == "time_since_last_positive_signal":
                recommendations.append(
                    "It's been over 2 weeks since your last positive signal. "
                    "Try reaching out to 3 contacts in your target companies "
                    "for informational conversations."
                )

        rest_suggestion = (
            "Consider taking 1-2 days off from active applications. "
            "Use that time to reflect on your strategy and recharge."
        )

        return InterventionResult(
            triggered_indicators=triggered_indicators,
            consecutive_negative_days=negative_streak,
            recommendations=recommendations,
            rest_suggestion=rest_suggestion,
        )
