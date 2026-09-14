from typing import List, Dict, Any, Tuple

def calculate_timetable_quality(
    entries: List[Dict[str, Any]],
    soft_weights: Any,
    days: List[str],
    periods: List[int]
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Computes timetable quality score based on soft constraints.
    Quality Score = 100.0 - Total Penalty
    """
    penalties = {
        "faculty_gap": 0.0,
        "student_gap": 0.0,
        "repeat_same_day": 0.0,
        "consecutive_faculty": 0.0,
        "non_preferred_slot": 0.0,
        "bad_lab_slot": 0.0,
        "period_monotony": 0.0
    }

    # Group entries by day, class, faculty
    day_class_entries: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    day_faculty_periods: Dict[Tuple[str, str], List[int]] = {}
    day_class_subjects: Dict[Tuple[str, str], List[str]] = {}

    for entry in entries:
        d = entry["day"]
        c_id = entry["class_section_id"]
        s_id = entry["subject_id"]
        start_p = entry["period"]
        dur = entry["duration"]
        all_p = list(range(start_p, start_p + dur))

        key_c = (d, c_id)
        if key_c not in day_class_entries:
            day_class_entries[key_c] = []
            day_class_subjects[key_c] = []
        day_class_entries[key_c].append(entry)

        # Track theory subject daily repetition
        if dur == 1:
            day_class_subjects[key_c].append(s_id)

        for fac_id in entry.get("faculty_ids", []):
            key_f = (d, fac_id)
            if key_f not in day_faculty_periods:
                day_faculty_periods[key_f] = []
            day_faculty_periods[key_f].extend(all_p)

        # Preferred slot penalty
        pref_days = entry.get("preferred_days", [])
        if pref_days and d not in pref_days:
            penalties["non_preferred_slot"] += getattr(soft_weights, "non_preferred_slot", 1.0)

    # 1. Check repetition of same theory subject in a single day
    for key, sub_list in day_class_subjects.items():
        counts: Dict[str, int] = {}
        for s in sub_list:
            counts[s] = counts.get(s, 0) + 1
        for s, cnt in counts.items():
            if cnt > 1:
                penalties["repeat_same_day"] += (cnt - 1) * getattr(soft_weights, "repeat_same_day", 4.0)

    # 2. Check faculty idle gaps and consecutive teaching fatigue
    for key, p_list in day_faculty_periods.items():
        p_sorted = sorted(p_list)
        if len(p_sorted) > 1:
            # Gaps
            for i in range(len(p_sorted) - 1):
                gap = p_sorted[i+1] - p_sorted[i] - 1
                if 0 < gap <= 2:
                    penalties["faculty_gap"] += gap * getattr(soft_weights, "faculty_gap", 2.0)

            # Consecutive periods (> 3 periods back-to-back causes fatigue)
            consec = 1
            for i in range(len(p_sorted) - 1):
                if p_sorted[i+1] == p_sorted[i] + 1:
                    consec += 1
                    if consec > 3:
                        penalties["consecutive_faculty"] += getattr(soft_weights, "consecutive_faculty", 2.0)
                else:
                    consec = 1

    # 3. Check monotone same-period repetition across days for the same subject
    class_subject_periods: Dict[Tuple[str, str], List[int]] = {}
    for entry in entries:
        if entry.get("duration", 1) == 1:
            k = (entry["class_section_id"], entry["subject_id"])
            if k not in class_subject_periods:
                class_subject_periods[k] = []
            class_subject_periods[k].append(entry["period"])

    for k, p_list in class_subject_periods.items():
        p_counts: Dict[int, int] = {}
        for p in p_list:
            p_counts[p] = p_counts.get(p, 0) + 1
        for p, count in p_counts.items():
            if count > 1:
                penalties["period_monotony"] += (count - 1) * 2.0

    total_penalty = sum(penalties.values())
    quality_score = max(0.0, round(100.0 - total_penalty, 2))
    return quality_score, total_penalty, penalties
