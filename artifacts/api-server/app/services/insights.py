from typing import List
from sqlalchemy.orm import Session
from app.repositories.checkin import CheckInRepository
from app.repositories.journal import JournalRepository
from app.repositories.insight import InsightRepository
from app.models.checkin import CheckIn


def _pearson_correlation(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    den_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def generate_insights(db: Session, user_id: int) -> List[dict]:
    checkins = CheckInRepository.get_recent_for_user(db, user_id, limit=60)

    if len(checkins) < 3:
        result = [{
            "insight_type": "insufficient_data",
            "title": "More Check-Ins Needed",
            "description": "Keep logging daily check-ins — you need at least 3 to start seeing behavioral patterns.",
            "confidence": None,
            "suggestion": "Try logging your mood, sleep, and stress each evening for a few days.",
        }]
        InsightRepository.create_bulk(db, user_id, result)
        return result

    insights = []

    sleep_vals = [c.sleep_hours for c in checkins]
    mood_vals = [float(c.mood_rating) for c in checkins]
    stress_vals = [float(c.stress_level) for c in checkins]

    sleep_mood_r = _pearson_correlation(sleep_vals, mood_vals)
    if abs(sleep_mood_r) >= 0.2:
        direction = "more" if sleep_mood_r > 0 else "less"
        insights.append({
            "insight_type": "sleep_mood",
            "title": "Sleep Affects Your Mood",
            "description": f"When you sleep {'more' if sleep_mood_r > 0 else 'less'}, your mood tends to be {'higher' if sleep_mood_r > 0 else 'lower'}. There is a {abs(sleep_mood_r):.0%} correlation between your sleep and mood.",
            "confidence": round(abs(sleep_mood_r), 2),
            "suggestion": f"Try to prioritize getting {direction} sleep to support better moods.",
        })

    exercise_mood_vals = [(float(c.exercised), float(c.mood_rating)) for c in checkins]
    exercised = [p[1] for p in exercise_mood_vals if p[0] > 0.5]
    not_exercised = [p[1] for p in exercise_mood_vals if p[0] <= 0.5]
    if exercised and not_exercised:
        avg_ex = sum(exercised) / len(exercised)
        avg_no = sum(not_exercised) / len(not_exercised)
        diff = avg_ex - avg_no
        if abs(diff) >= 0.3:
            insights.append({
                "insight_type": "exercise_mood",
                "title": "Exercise Boosts Your Mood",
                "description": f"On days you exercise, your average mood is {avg_ex:.1f} vs {avg_no:.1f} on rest days — a {abs(diff):.1f} point {'boost' if diff > 0 else 'dip'}.",
                "confidence": round(min(abs(diff) / 2, 0.95), 2),
                "suggestion": "Even a short walk or workout can make a meaningful difference to how you feel.",
            })

    workload_checkins = [c for c in checkins if c.workload_level is not None]
    if len(workload_checkins) >= 3:
        workload_vals = [float(c.workload_level) for c in workload_checkins]
        stress_wl_vals = [float(c.stress_level) for c in workload_checkins]
        workload_stress_r = _pearson_correlation(workload_vals, stress_wl_vals)
        if abs(workload_stress_r) >= 0.25:
            insights.append({
                "insight_type": "workload_stress",
                "title": "Workload Drives Your Stress",
                "description": f"Your stress levels are closely tied to your workload — a {abs(workload_stress_r):.0%} correlation. Heavy work days tend to spike your stress.",
                "confidence": round(abs(workload_stress_r), 2),
                "suggestion": "Consider scheduling breaks or buffer time on high-workload days to manage stress.",
            })

    journals = JournalRepository.get_recent_for_user(db, user_id, limit=20)
    all_keywords: List[str] = []
    for j in journals:
        if j.keywords:
            all_keywords.extend([k.strip() for k in j.keywords.split(",") if k.strip()])
    if all_keywords:
        from collections import Counter
        freq = Counter(all_keywords)
        top = freq.most_common(3)
        if top:
            kw_list = ", ".join(f'"{k}" ({c}x)' for k, c in top)
            insights.append({
                "insight_type": "journal_keywords",
                "title": "Recurring Themes in Your Journal",
                "description": f"These themes appear most often in your journal entries: {kw_list}.",
                "confidence": None,
                "suggestion": "Noticing recurring themes can help you understand what's on your mind most.",
            })

    if not insights:
        insights.append({
            "insight_type": "general",
            "title": "Keep Logging",
            "description": "You're building great habits! Keep logging check-ins and journal entries to unlock more personalized pattern insights.",
            "confidence": None,
            "suggestion": "Patterns become clearer with more data — aim for consistent daily check-ins.",
        })

    InsightRepository.create_bulk(db, user_id, insights)
    return insights
