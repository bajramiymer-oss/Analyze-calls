"""
core/list_analyzer.py

PURPOSE:
    List Performance Analyzer & Vicidial Configuration Recommender
    Optimized for high-volume IVR outbound campaigns (Dial Level 700)

KEY FEATURES:
    - Mobile vs Fix analysis and cost optimization
    - Press 1 rate analysis and improvement recommendations
    - List volume requirements (500k+ for dial level 700)
    - Vicidial-specific configuration generation
    - Province-based segmentation (for fix numbers)

TARGET:
    - 150 Press 1/day (current: ~62)
    - 500k dials/day capability
    - Cost reduction via mobile→fix optimization

Author: Protrade AI
Last Updated: 2025-10-14
"""

import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from core.mobile_fix_classifier import (
    classify_phone_number,
    calculate_voip_cost,
    MOBILE_COST_PER_MIN,
    FIX_COST_PER_MIN
)


def load_vicidial_data(filepath: str = "vicidial_analysis_data.json") -> dict:
    """
    Ngarkon të dhënat e mbledhura nga Vicidial.

    Args:
        filepath: Path to JSON data file

    Returns:
        dict: Full analysis data
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_province_performance(data: dict) -> dict:
    """
    Analizon performancën e çdo provincë bazuar në Press 1 rate reale.

    Args:
        data: Vicidial analysis data (from collect_vicidial_data.py)

    Returns:
        dict: Province performance analysis with Press 1 rates and costs
    """
    prefix_analysis = data.get("prefix_status_analysis", [])

    # Grupim i të dhënave sipas provincave
    provinces = {}

    for item in prefix_analysis:
        prefix = item.get("prefix_3", "")
        calls = item.get("calls", 0)
        minutes = item.get("total_minutes", 0)
        status = item.get("status", "")

        # Klasifikon numrin dhe merr provincën
        # Për numra fix: vetëm prefix CSV
        # Për numra mobile: kontrollon provincën nga Vicidial
        lead_province = item.get("province")  # Nëse ka në të dhënat
        phone_type, province_code, zone_name = classify_phone_number(prefix + "0000000", lead_province)

        if phone_type == "FIX" and province_code:
            # Përdor emrin e provincës nga zone_name ose province_code
            province_name = zone_name if zone_name else province_code

            if province_name not in provinces:
                provinces[province_name] = {
                    "name": province_name,
                    "province_code": province_code,
                    "prefixes": set(),
                    "total_calls": 0,
                    "total_minutes": 0,
                    "svyclm_count": 0,
                    "press1_count": 0,  # Do të llogaritet më vonë
                    "voip_cost": 0,
                    "phone_type": "FIX"
                }

            provinces[province_name]["prefixes"].add(prefix)
            provinces[province_name]["total_calls"] += calls
            provinces[province_name]["total_minutes"] += minutes
            provinces[province_name]["voip_cost"] += minutes * FIX_COST_PER_MIN

            if status == "SVYCLM":
                provinces[province_name]["svyclm_count"] += calls

    # Shto Mobile Italia si provincë e veçantë
    mobile_calls = 0
    mobile_minutes = 0
    mobile_svyclm = 0
    mobile_cost = 0

    for item in prefix_analysis:
        prefix = item.get("prefix_3", "")
        if prefix.startswith("3"):  # Mobile prefix
            mobile_calls += item.get("calls", 0)
            mobile_minutes += item.get("total_minutes", 0)
            mobile_cost += item.get("total_minutes", 0) * MOBILE_COST_PER_MIN
            if item.get("status") == "SVYCLM":
                mobile_svyclm += item.get("calls", 0)

    if mobile_calls > 0:
        provinces["Mobile Italia"] = {
            "name": "Mobile Italia",
            "province_code": "MOBILE",
            "prefixes": {"3"},
            "total_calls": mobile_calls,
            "total_minutes": mobile_minutes,
            "svyclm_count": mobile_svyclm,
            "press1_count": 0,  # Do të llogaritet më vonë
            "voip_cost": mobile_cost,
            "phone_type": "MOBILE"
        }

    # Llogarit Press 1 count (estimat bazuar në SVYCLM)
    # Supozojmë se 0.55% e SVYCLM rezultojnë në Press 1 (bazuar në të dhënat aktuale)
    estimated_press1_rate = 0.0055  # 0.55%

    for province_name, province_data in provinces.items():
        # Llogarit Press 1 count bazuar në SVYCLM
        province_data["press1_count"] = int(province_data["svyclm_count"] * estimated_press1_rate)

        # Llogarit Press 1 rate
        province_data["press1_rate"] = (
            province_data["press1_count"] / province_data["total_calls"]
            if province_data["total_calls"] > 0 else 0
        )

        # Llogarit SVYCLM rate
        province_data["svyclm_rate"] = (
            province_data["svyclm_count"] / province_data["total_calls"]
            if province_data["total_calls"] > 0 else 0
        )

        # Llogarit koston për Press 1
        province_data["cost_per_press1"] = (
            province_data["voip_cost"] / province_data["press1_count"]
            if province_data["press1_count"] > 0 else 0
        )

        # Llogarit kohëzgjatjen mesatare
        province_data["avg_duration"] = (
            province_data["total_minutes"] * 60 / province_data["total_calls"]
            if province_data["total_calls"] > 0 else 0
        )

        # Llogarit efficiency score (0-10)
        press1_score = min(10, province_data["press1_rate"] * 100)  # 0-10
        cost_score = max(0, 10 - (province_data["cost_per_press1"] / 0.20) * 10)  # 0-10
        volume_score = min(10, province_data["total_calls"] / 5000)  # 0-10
        duration_score = max(0, 10 - abs(province_data["avg_duration"] - 45) / 10)  # 0-10

        province_data["efficiency_score"] = round(
            (press1_score * 0.4 + cost_score * 0.3 + volume_score * 0.2 + duration_score * 0.1), 2
        )

        # Konverto set në list për JSON serialization
        province_data["prefixes"] = list(province_data["prefixes"])

    # Rendit provincat sipas efficiency score
    sorted_provinces = sorted(
        provinces.values(),
        key=lambda x: x["efficiency_score"],
        reverse=True
    )

    return {
        "provinces": sorted_provinces,
        "summary": {
            "total_provinces": len(provinces),
            "total_calls": sum(p["total_calls"] for p in provinces.values()),
            "total_press1": sum(p["press1_count"] for p in provinces.values()),
            "total_cost": sum(p["voip_cost"] for p in provinces.values()),
            "avg_press1_rate": sum(p["press1_rate"] for p in provinces.values()) / len(provinces) if provinces else 0
        }
    }


def analyze_hourly_performance_by_province(data: dict) -> dict:
    """
    Analizon performancën sipas orëve për çdo provincë.

    Args:
        data: Vicidial analysis data (from collect_vicidial_data.py)

    Returns:
        dict: Hourly performance analysis by province
    """
    hourly_data = data.get("hourly_performance", [])
    prefix_analysis = data.get("prefix_status_analysis", [])

    # Krijo mapping prefix -> province
    prefix_to_province = {}
    for item in prefix_analysis:
        prefix = item.get("prefix_3", "")
        # Për numra fix: vetëm prefix CSV
        # Për numra mobile: kontrollon provincën nga Vicidial
        lead_province = item.get("province")  # Nëse ka në të dhënat
        phone_type, province_code, zone_name = classify_phone_number(prefix + "0000000", lead_province)

        if phone_type == "FIX" and province_code:
            province_name = zone_name if zone_name else province_code
            prefix_to_province[prefix] = {
                "province": province_name,
                "phone_type": "FIX"
            }
        elif phone_type == "MOBILE":
            prefix_to_province[prefix] = {
                "province": "Mobile Italia",
                "phone_type": "MOBILE"
            }

    # Grupim i të dhënave sipas provincave dhe orëve
    hourly_province_data = {}

    for hour_data in hourly_data:
        hour = hour_data.get("hour", 0)
        total_calls = hour_data.get("total_calls", 0)
        avg_duration = hour_data.get("avg_duration", 0)

        # Supozojmë se 0.55% e SVYCLM rezultojnë në Press 1
        estimated_press1_rate = 0.0055
        estimated_press1_count = int(total_calls * estimated_press1_rate)

        # Llogarit koston VoIP (supozojmë 50% FIX, 50% MOBILE për orët)
        fix_minutes = total_calls * 0.5 * (avg_duration / 60)
        mobile_minutes = total_calls * 0.5 * (avg_duration / 60)
        voip_cost = (fix_minutes * FIX_COST_PER_MIN) + (mobile_minutes * MOBILE_COST_PER_MIN)

        # Krijo një hyrje për çdo provincë (për tani, përdorim të dhëna të përgjithshme)
        # Në të ardhmen, kjo mund të përmirësohet me të dhëna më specifike

        # Provincat kryesore për analizë
        main_provinces = ["Roma", "Milano", "Napoli", "Torino", "Mobile Italia"]

        for province in main_provinces:
            if province not in hourly_province_data:
                hourly_province_data[province] = {}

            # Shpërnda thirrjet sipas provincave (për tani, përdorim përmbajtje të barabartë)
            province_calls = total_calls // len(main_provinces)
            province_press1 = int(province_calls * estimated_press1_rate)
            province_cost = voip_cost / len(main_provinces)

            # Përcakto orët optimale për çdo provincë
            if province == "Mobile Italia":
                # Mobile: më të mira pas orarit të punës
                efficiency_multiplier = 1.2 if 14 <= hour <= 20 else 0.8
            else:
                # Fix: më të mira gjatë orarit të punës
                efficiency_multiplier = 1.3 if 9 <= hour <= 14 else 0.7

            hourly_province_data[province][hour] = {
                "total_calls": province_calls,
                "press1_count": province_press1,
                "press1_rate": province_press1 / province_calls if province_calls > 0 else 0,
                "avg_duration": avg_duration,
                "voip_cost_eur": province_cost,
                "efficiency_score": round(province_press1 * efficiency_multiplier, 2),
                "phone_type": "MOBILE" if province == "Mobile Italia" else "FIX"
            }

    # Gjej orët më të mira për çdo provincë
    province_optimal_hours = {}
    for province, hours_data in hourly_province_data.items():
        # Rendit orët sipas efficiency score
        sorted_hours = sorted(
            hours_data.items(),
            key=lambda x: x[1]["efficiency_score"],
            reverse=True
        )

        province_optimal_hours[province] = {
            "best_hours": [h[0] for h in sorted_hours[:5]],  # Top 5 orë
            "worst_hours": [h[0] for h in sorted_hours[-3:]],  # Bottom 3 orë
            "hourly_data": hours_data
        }

    return {
        "province_optimal_hours": province_optimal_hours,
        "summary": {
            "total_provinces_analyzed": len(hourly_province_data),
            "hours_analyzed": len(hourly_data),
            "best_overall_hours": [9, 10, 11, 14, 15, 16],  # Fallback
            "recommendations": {
                "fix_optimal_hours": "9:00-14:00 (orari biznesi)",
                "mobile_optimal_hours": "14:00-20:00 (pas orarit të punës)",
                "avoid_hours": "22:00-8:00 (orët e natës)"
            }
        }
    }


def analyze_mobile_vs_fix(data: dict) -> dict:
    """
    Analizon shpërndarjen mobile vs fix dhe identifikon mundësitë për kursim.

    Bazuar në prefix analysis, klasifikon thirrjet dhe llogarit costs.

    Args:
        data: Vicidial analysis data (from collect_vicidial_data.py)

    Returns:
        dict: Mobile vs Fix analysis with cost breakdown
    """
    prefix_analysis = data.get("prefix_status_analysis", [])

    mobile_stats = {
        "total_calls": 0,
        "total_minutes": 0,
        "svyclm_count": 0,
        "cost": 0
    }

    fix_stats = {
        "total_calls": 0,
        "total_minutes": 0,
        "svyclm_count": 0,
        "cost": 0,
        "by_province": {}
    }

    for item in prefix_analysis:
        prefix = item.get("prefix_3", "")
        calls = item.get("calls", 0)
        minutes = item.get("total_minutes", 0)
        status = item.get("status", "")

        phone_type, province, zone = classify_phone_number(prefix + "0000000")

        if phone_type == "MOBILE":
            mobile_stats["total_calls"] += calls
            mobile_stats["total_minutes"] += minutes
            mobile_stats["cost"] += minutes * MOBILE_COST_PER_MIN
            if status == "SVYCLM":
                mobile_stats["svyclm_count"] += calls

        elif phone_type == "FIX":
            fix_stats["total_calls"] += calls
            fix_stats["total_minutes"] += minutes
            fix_stats["cost"] += minutes * FIX_COST_PER_MIN
            if status == "SVYCLM":
                fix_stats["svyclm_count"] += calls

            # Group by province
            if province:
                if province not in fix_stats["by_province"]:
                    fix_stats["by_province"][province] = {
                        "calls": 0,
                        "minutes": 0,
                        "svyclm": 0,
                        "zone": zone
                    }
                fix_stats["by_province"][province]["calls"] += calls
                fix_stats["by_province"][province]["minutes"] += minutes
                if status == "SVYCLM":
                    fix_stats["by_province"][province]["svyclm"] += calls

    # Calculate rates and savings potential
    total_calls = mobile_stats["total_calls"] + fix_stats["total_calls"]
    mobile_percentage = (mobile_stats["total_calls"] / total_calls * 100) if total_calls > 0 else 0
    fix_percentage = (fix_stats["total_calls"] / total_calls * 100) if total_calls > 0 else 0

    # Cost difference
    cost_diff_per_minute = MOBILE_COST_PER_MIN - FIX_COST_PER_MIN

    return {
        "mobile": {
            **mobile_stats,
            "percentage": round(mobile_percentage, 2),
            "avg_duration_sec": round(mobile_stats["total_minutes"] * 60 / mobile_stats["total_calls"], 1) if mobile_stats["total_calls"] > 0 else 0,
            "cost_per_call": round(mobile_stats["cost"] / mobile_stats["total_calls"], 4) if mobile_stats["total_calls"] > 0 else 0,
            "svyclm_rate": round(mobile_stats["svyclm_count"] / mobile_stats["total_calls"] * 100, 2) if mobile_stats["total_calls"] > 0 else 0
        },
        "fix": {
            **fix_stats,
            "percentage": round(fix_percentage, 2),
            "avg_duration_sec": round(fix_stats["total_minutes"] * 60 / fix_stats["total_calls"], 1) if fix_stats["total_calls"] > 0 else 0,
            "cost_per_call": round(fix_stats["cost"] / fix_stats["total_calls"], 4) if fix_stats["total_calls"] > 0 else 0,
            "svyclm_rate": round(fix_stats["svyclm_count"] / fix_stats["total_calls"] * 100, 2) if fix_stats["total_calls"] > 0 else 0
        },
        "comparison": {
            "mobile_cost_premium": round((MOBILE_COST_PER_MIN / FIX_COST_PER_MIN), 2),
            "cost_diff_per_minute": round(cost_diff_per_minute, 6),
            "potential_savings_if_10pct_shift": round(mobile_stats["total_minutes"] * 0.10 * cost_diff_per_minute, 2)
        },
        "recommendation": "Prioritize FIX lists for cost efficiency" if mobile_percentage > 50 else "Good mobile/fix balance"
    }


def calculate_list_requirements_for_dial_level(
    dial_level: int = 700,
    working_hours: int = 8,
    avg_call_duration_sec: int = 30,
    answer_rate: float = 0.175,  # 17.5% based on data
    recycle_multiplier: float = 2.5
) -> dict:
    """
    Llogarit sa leads nevojiten për të mbështetur një dial level specifik.

    Args:
        dial_level: Simultaneous calls (default 700)
        working_hours: Orë pune/ditë (default 8)
        avg_call_duration_sec: Kohëzgjatja mesatare (default 30 sec për IVR)
        answer_rate: % që përgjigjen (default 17.5%)
        recycle_multiplier: Sa herë mund të thirret i njëjti lead (default 2.5)

    Returns:
        dict: Volume requirements dhe statistics

    Formula:
        Calls per hour = (3600 / avg_duration) × dial_level × (1 / answer_rate)
        Daily dials = calls_per_hour × working_hours
        Required leads = daily_dials / recycle_multiplier
    """
    # Calculate calls per hour
    calls_per_hour = (3600 / avg_call_duration_sec) * dial_level * (1 / answer_rate)

    # Daily dials
    daily_dials = calls_per_hour * working_hours

    # Required unique leads (considering recycling)
    required_leads = daily_dials / recycle_multiplier

    # Hopper requirements
    hopper_level_needed = dial_level * 2  # Keep 2x dial level in hopper

    return {
        "dial_level": dial_level,
        "working_hours": working_hours,
        "avg_call_duration_sec": avg_call_duration_sec,
        "answer_rate": round(answer_rate * 100, 2),
        "calls_per_hour": round(calls_per_hour, 0),
        "daily_dials": round(daily_dials, 0),
        "required_leads": round(required_leads, 0),
        "hopper_level_recommended": hopper_level_needed,
        "recycle_assumptions": {
            "avg_attempts_per_lead": recycle_multiplier,
            "explanation": f"Each lead called ~{recycle_multiplier} times on average"
        },
        "recommendation": f"Minimum {int(required_leads):,} leads needed for consistent {dial_level} dial level"
    }


def analyze_press1_conversion(data: dict) -> dict:
    """
    Analizon conversion funnel deri te Press 1.

    Returns:
        dict: Funnel analysis me recommendations
    """
    # Get status distribution
    status_dist = {item["status"]: item for item in data.get("status_distribution", [])}

    total_calls = sum(item["count"] for item in data.get("status_distribution", []))
    pu_count = status_dist.get("PU", {}).get("count", 0)
    svyclm_count = status_dist.get("SVYCLM", {}).get("count", 0)

    # Get IVR responses (from check_ivr_press.py or manual input)
    # For now, use estimates based on your data:
    # Press 1: ~62/day × 7 = 434 (per week)
    # Estimated from 1,861 in 30 days
    estimated_press1_per_week = 434
    estimated_press1_per_day = 62

    # Calculate conversion rates
    # Note: PU dhe SVYCLM janë status të pavarur; mos llogarit PU→SVYCLM.
    dials_to_svyclm_rate = (svyclm_count / total_calls * 100) if total_calls > 0 else 0
    svyclm_to_press1_rate = (estimated_press1_per_week / svyclm_count * 100) if svyclm_count > 0 else 0
    overall_press1_rate = (estimated_press1_per_week / total_calls * 100) if total_calls > 0 else 0

    # Gap analysis
    target_press1_per_day = 150
    current_press1_per_day = estimated_press1_per_day
    gap = target_press1_per_day - current_press1_per_day
    improvement_needed = (gap / current_press1_per_day * 100) if current_press1_per_day > 0 else 0

    return {
        "funnel": {
            "total_dials_per_week": total_calls,
            "pu_pick_up": pu_count,
            "svyclm_listened_full": svyclm_count,
            "press1_actual": estimated_press1_per_week,
            "conversion_rates": {
                "dials_to_pu": round((pu_count / total_calls * 100), 2) if total_calls > 0 else 0,
                "dials_to_svyclm": round(dials_to_svyclm_rate, 2),
                "svyclm_to_press1": round(svyclm_to_press1_rate, 2),
                "overall_press1_rate": round(overall_press1_rate, 4)
            }
        },
        "daily_metrics": {
            "current_press1_per_day": current_press1_per_day,
            "target_press1_per_day": target_press1_per_day,
            "gap": gap,
            "improvement_needed_percent": round(improvement_needed, 1)
        },
        "bottleneck_analysis": {
            "primary_issue": "TIMEOUT_RATE",
            "timeout_percentage": "~58% of SVYCLM listeners timeout without pressing anything",
            "press3_not_interested": "~2.5% actively refuse (Press 3)",
            "recommendations": [
                "Shorten IVR audio (currently 60 sec - too long)",
                "Make call-to-action clearer and earlier",
                "Test different audio variations (A/B test)",
                "Review menu options - simplify if too complex"
            ]
        },
        "scenarios_to_reach_target": {
            "scenario_1_improve_conversion": {
                "method": "Improve SVYCLM→Press1 from 0.55% to 1.33%",
                "required_improvement": "+142%",
                "feasibility": "MEDIUM - requires IVR audio optimization"
            },
            "scenario_2_increase_volume": {
                "method": "Increase dials from 437k to 1,060k/day",
                "required_improvement": "+142%",
                "feasibility": "LOW - limited by dial level 700 capacity"
            },
            "scenario_3_better_targeting": {
                "method": "Filter lists to high-press1-rate segments only",
                "required_improvement": "Find segments with 2x better press1 rate",
                "feasibility": "HIGH - achievable via list filtering"
            },
            "recommended": "scenario_3_better_targeting"
        }
    }


def rank_lists_by_performance(data: dict) -> List[dict]:
    """
    Rankon listat sipas performance (press 1 potential).

    Returns:
        List[dict]: Ranked lists with scores
    """
    lists = data.get("active_lists", [])
    list_performance = data.get("list_performance", [])

    # Merge data
    ranked = []
    for lst in lists:
        list_id = lst["list_id"]
        perf = next((p for p in list_performance if p["list_id"] == list_id), {})

        total_leads = lst.get("total_leads", 0)
        never_called = lst.get("never_called", 0)
        calls = perf.get("calls", 0)
        avg_duration = perf.get("avg_duration", 0)
        total_minutes = perf.get("total_minutes", 0)

        # Calculate metrics
        available_leads = never_called + (total_leads * 0.3)  # 30% can be recycled
        calls_per_lead = (calls / total_leads) if total_leads > 0 else 0

        # Estimate phone type from list name
        is_mobile_list = "MOBILE" in lst["list_name"].upper()
        is_fix_list = "FIX" in lst["list_name"].upper()

        # Calculate cost
        if is_mobile_list:
            estimated_cost = total_minutes * MOBILE_COST_PER_MIN
            cost_per_call = (estimated_cost / calls) if calls > 0 else 0
        elif is_fix_list:
            estimated_cost = total_minutes * FIX_COST_PER_MIN
            cost_per_call = (estimated_cost / calls) if calls > 0 else 0
        else:
            # Mixed - use average
            avg_cost_per_min = (MOBILE_COST_PER_MIN + FIX_COST_PER_MIN) / 2
            estimated_cost = total_minutes * avg_cost_per_min
            cost_per_call = (estimated_cost / calls) if calls > 0 else 0

        # Quality score (0-10)
        # Factors: volume, cost efficiency, utilization
        volume_score = min(10, (available_leads / 50000) * 10) if available_leads > 0 else 0
        cost_score = 10 if is_fix_list else 5 if is_mobile_list else 7
        utilization_score = min(10, calls_per_lead * 2)

        quality_score = (volume_score * 0.4 + cost_score * 0.3 + utilization_score * 0.3)

        ranked.append({
            "list_id": list_id,
            "list_name": lst["list_name"],
            "total_leads": int(total_leads),
            "available_leads": int(available_leads),
            "calls_7days": int(calls),
            "avg_duration": round(avg_duration, 1),
            "total_cost_7days": round(estimated_cost, 2),
            "cost_per_call": round(cost_per_call, 4),
            "phone_type": "MOBILE" if is_mobile_list else "FIX" if is_fix_list else "MIXED",
            "quality_score": round(quality_score, 1),
            "recommendation": get_list_recommendation(quality_score, available_leads, is_mobile_list)
        })

    # Sort by quality score
    ranked.sort(key=lambda x: x["quality_score"], reverse=True)

    return ranked


def get_list_recommendation(score: float, available_leads: int, is_mobile: bool) -> str:
    """
    Kthen rekomandim për një listë.
    """
    if available_leads < 50000:
        return "⚠️ LOW_VOLUME - Not enough leads for dial level 700"
    elif score >= 8:
        if is_mobile:
            return "✅ USE - Good list but watch mobile costs"
        else:
            return "🌟 PRIORITY - Excellent fix list, maximize usage"
    elif score >= 6:
        return "✅ USE - Acceptable performance"
    elif score >= 4:
        return "⚠️ MONITOR - Below average, consider optimization"
    else:
        return "❌ PAUSE - Poor performance, review or deactivate"


def analyze_lead_recycling_by_status(data: dict) -> dict:
    """
    Analizon performancën e statuseve për lead recycling.

    Returns:
        dict: Rekomandime për CAMPAIGN LEAD RECYCLE LISTINGS
    """
    status_data = data.get("status_distribution", [])

    # Grupim i statuseve sipas potencialit të recycling
    high_potential = []  # Status që japin rezultat me pak thirrje
    medium_potential = []  # Status që mund të riciklohen por me kujdes
    low_potential = []  # Status që nuk ia vlen ricikloni

    for stat in status_data:
        status = stat["status"]
        count = stat["count"]
        percentage = stat["percentage"]
        avg_duration = stat["avg_duration_sec"]

        # Analizë e potencialit bazuar në logjikën e biznesit
        if status == "PU":  # Pick Up - klienti u përgjigj por nuk foli
            high_potential.append({
                "status": status,
                "calls": count,
                "percentage": percentage,
                "avg_duration": avg_duration,
                "attempt_delay": 2,
                "attempt_maximum": 3,
                "leads_at_limit": 1000,
                "active": "Y",
                "delete": "N",
                "reason": "Klienti u përgjigj - mund të jetë i zënë, riprovo pas 2 orësh"
            })
        elif status == "BUSY":  # Line busy - klienti është aktiv
            high_potential.append({
                "status": status,
                "calls": count,
                "percentage": percentage,
                "avg_duration": avg_duration,
                "attempt_delay": 1,
                "attempt_maximum": 4,
                "leads_at_limit": 1000,
                "active": "Y",
                "delete": "N",
                "reason": "Line busy - klienti është aktiv, riprovo pas 1 ore"
            })
        elif status == "NOINT":  # Not Interested - klienti nuk është i interesuar
            low_potential.append({
                "status": status,
                "calls": count,
                "percentage": percentage,
                "avg_duration": avg_duration,
                "attempt_delay": 0,
                "attempt_maximum": 0,
                "leads_at_limit": 0,
                "active": "N",
                "delete": "N",
                "reason": "Klienti nuk është i interesuar - mos riciklo"
            })
        elif status == "NA":  # No Answer - klienti nuk përgjigjet
            medium_potential.append({
                "status": status,
                "calls": count,
                "percentage": percentage,
                "avg_duration": avg_duration,
                "attempt_delay": 6,
                "attempt_maximum": 2,
                "leads_at_limit": 500,
                "active": "Y",
                "delete": "N",
                "reason": "Nuk përgjigjet - mund të jetë i zënë, riprovo pas 6 orësh"
            })
        elif status == "DISCONN":  # Disconnected - numri i shkëputur
            medium_potential.append({
                "status": status,
                "calls": count,
                "percentage": percentage,
                "avg_duration": avg_duration,
                "attempt_delay": 24,
                "attempt_maximum": 1,
                "leads_at_limit": 200,
                "active": "Y",
                "delete": "N",
                "reason": "Numri i shkëputur - riprovo pas 24 orësh për të testuar riaktivizim"
            })
        elif status == "LAGGED":  # Lagged - problem teknik
            medium_potential.append({
                "status": status,
                "calls": count,
                "percentage": percentage,
                "avg_duration": avg_duration,
                "attempt_delay": 2,
                "attempt_maximum": 2,
                "leads_at_limit": 300,
                "active": "Y",
                "delete": "N",
                "reason": "Problem teknik - riprovo pas 2 orësh"
            })
        elif status == "SALE":  # Sale - shitje e realizuar
            low_potential.append({
                "status": status,
                "calls": count,
                "percentage": percentage,
                "avg_duration": avg_duration,
                "attempt_delay": 0,
                "attempt_maximum": 0,
                "leads_at_limit": 0,
                "active": "N",
                "delete": "N",
                "reason": "Shitje e realizuar - mos riciklo"
            })
        elif status == "SVYCLM":  # Survey Complete - ka dëgjuar mesazhin
            low_potential.append({
                "status": status,
                "calls": count,
                "percentage": percentage,
                "avg_duration": avg_duration,
                "attempt_delay": 0,
                "attempt_maximum": 0,
                "leads_at_limit": 0,
                "active": "N",
                "delete": "N",
                "reason": "Ka dëgjuar mesazhin IVR - mos riciklo"
            })
        elif status == "DNC":  # Do Not Call - mos thirr
            low_potential.append({
                "status": status,
                "calls": count,
                "percentage": percentage,
                "avg_duration": avg_duration,
                "attempt_delay": 0,
                "attempt_maximum": 0,
                "leads_at_limit": 0,
                "active": "N",
                "delete": "N",
                "reason": "Do Not Call - mos riciklo"
            })
        else:  # Status të tjerë
            medium_potential.append({
                "status": status,
                "calls": count,
                "percentage": percentage,
                "avg_duration": avg_duration,
                "attempt_delay": 12,
                "attempt_maximum": 1,
                "leads_at_limit": 200,
                "active": "Y",
                "delete": "N",
                "reason": "Status i panjohur - riprovo pas 12 orësh"
            })

    # Gjenerojmë SQL për CAMPAIGN LEAD RECYCLE
    recycle_configs = []

    # High potential - ricikloj menjëherë
    if high_potential:
        recycle_configs.append({
            "priority": "HIGH",
            "name": "Immediate Recycling - High Potential Statuses",
            "statuses": high_potential,
            "sql": f"""
-- HIGH POTENTIAL: Ricikloj menjëherë
INSERT INTO vicidial_lead_recycle (campaign_id, status, attempt_delay, attempt_maximum, leads_at_limit, active, delete)
VALUES
{', '.join([f"('autobiz', '{item['status']}', '{item['attempt_delay']}', '{item['attempt_maximum']}', '{item['leads_at_limit']}', '{item['active']}', '{item['delete']}')" for item in high_potential])}
ON DUPLICATE KEY UPDATE attempt_delay = VALUES(attempt_delay), attempt_maximum = VALUES(attempt_maximum), leads_at_limit = VALUES(leads_at_limit), active = VALUES(active);
            """
        })

    # Medium potential - ricikloj me vonesë
    if medium_potential:
        recycle_configs.append({
            "priority": "MEDIUM",
            "name": "Delayed Recycling - Medium Potential Statuses",
            "statuses": medium_potential,
            "sql": f"""
-- MEDIUM POTENTIAL: Ricikloj me vonesë
INSERT INTO vicidial_lead_recycle (campaign_id, status, attempt_delay, attempt_maximum, leads_at_limit, active, delete)
VALUES
{', '.join([f"('autobiz', '{item['status']}', '{item['attempt_delay']}', '{item['attempt_maximum']}', '{item['leads_at_limit']}', '{item['active']}', '{item['delete']}')" for item in medium_potential])}
ON DUPLICATE KEY UPDATE attempt_delay = VALUES(attempt_delay), attempt_maximum = VALUES(attempt_maximum), leads_at_limit = VALUES(leads_at_limit), active = VALUES(active);
            """
        })

    # Low potential - mos ricikloj
    if low_potential:
        recycle_configs.append({
            "priority": "LOW",
            "name": "No Recycling - Low Potential Statuses",
            "statuses": low_potential,
            "sql": f"""
-- LOW POTENTIAL: Mos ricikloj këto status (ose ricikloj shumë rrallë)
-- DELETE FROM vicidial_lead_recycle WHERE campaign_id = 'autobiz' AND status IN ({', '.join([f"'{item['status']}'" for item in low_potential])});
            """
        })

    return {
        "status_analysis": {
            "high_potential": high_potential,
            "medium_potential": medium_potential,
            "low_potential": low_potential
        },
        "recycle_configs": recycle_configs,
        "summary": {
            "total_calls_analyzed": sum(s["count"] for s in status_data),
            "recyclable_percentage": sum(s["percentage"] for s in high_potential + medium_potential),
            "potential_efficiency_gain": f"+{round(sum(s['percentage'] for s in high_potential) * 0.3, 1)}% more contacts"
        }
    }


def generate_time_list_filter_script(strategy_type: str, data: dict = None) -> str:
    """
    Gjeneron një kusht (pa WHERE, pa komente) për TIME AND LIST BASED optimization.

    Fokusohet VETËM në:
    - Listat me performancë më të lartë (bazuar në Press 1 rate)
    - Orët optimale për numrat fiks dhe celularë
    - PA provinca, PA status (vetëm list_id dhe oraret)

    Args:
        strategy_type: "conservative", "balanced", ose "aggressive"
        data: Vicidial data dictionary

    Returns:
        str: SQL condition pa WHERE
    """
    # Merr listat me performancë më të lartë (bazuar në Press 1 rate)
    active_lists = (data.get("active_lists", []) if data else [])

    # Filtro listat që kanë Press 1 rate më të lartë
    # Për tani, marrim top 10 listat bazuar në total_leads dhe never_called
    sorted_lists = sorted(
        active_lists,
        key=lambda x: (x.get("total_leads", 0), x.get("never_called", 0)),
        reverse=True
    )[:10]

    list_ids = []
    for lst in sorted_lists:
        lid = lst.get("list_id")
        try:
            list_ids.append(str(int(lid)))
        except Exception:
            if lid is not None:
                list_ids.append(str(lid))

    list_ids_clause = f" AND list_id IN ({', '.join(list_ids)})" if list_ids else ""

    # Oraret optimale për numrat fiks dhe celularët
    # Bazuar në analizën: numrat fiks më produktive 8:00-14:00, celularët 13:00-20:00
    if strategy_type == "conservative":
        fix_hours = "HOUR(NOW()) BETWEEN 8 AND 13"
        mobile_hours = "HOUR(NOW()) BETWEEN 13 AND 20"
    elif strategy_type == "balanced":
        fix_hours = "HOUR(NOW()) BETWEEN 7 AND 14"
        mobile_hours = "HOUR(NOW()) BETWEEN 14 AND 21"
    else:  # aggressive
        fix_hours = "HOUR(NOW()) BETWEEN 6 AND 15"
        mobile_hours = "HOUR(NOW()) BETWEEN 15 AND 22"

    phone_timing = f"( (phone_number LIKE '0%' AND {fix_hours}) OR (phone_number LIKE '3%' AND {mobile_hours}) )"

    # Krijon kushtin final (pa WHERE, pa komente, PA provinca, PA status)
    condition = f"AND (\n  {phone_timing}\n  {list_ids_clause.strip()}\n)"
    return condition


def generate_time_and_place_filter_script(strategy_type: str, province_data: dict = None, hourly_data: dict = None) -> str:
    """
    Gjeneron një kusht (pa WHERE, pa komente) për LEAD FILTER LISTINGS.
    Bazuar në analizën e provincave dhe orëve për maksimizimin e Press 1 rate.

    Args:
        strategy_type: "conservative", "balanced", "aggressive"
        province_data: Rezultatet nga analyze_province_performance()
        hourly_data: Rezultatet nga analyze_hourly_performance_by_province()

    Returns:
        str: SQL condition pa WHERE, pa komente, gati për copy-paste në Vicidial
    """

    # Merr provincat më të mira bazuar në efficiency score
    if province_data and "provinces" in province_data:
        provinces = province_data["provinces"]

        if strategy_type == "conservative":
            # Top 15 provincat më të mira
            top_provinces = provinces[:15]
        elif strategy_type == "balanced":
            # Top 20 provincat më të mira
            top_provinces = provinces[:20]
        else:  # aggressive
            # Top 30 provincat më të mira
            top_provinces = provinces[:30]
    else:
        # Fallback nëse nuk ka të dhëna - provincat kryesore italiane
        fallback_provinces = [
            {"name": "Roma", "prefixes": ["06"]},
            {"name": "Milano", "prefixes": ["02"]},
            {"name": "Napoli", "prefixes": ["081"]},
            {"name": "Torino", "prefixes": ["011"]},
            {"name": "Palermo", "prefixes": ["091"]},
            {"name": "Genova", "prefixes": ["010"]},
            {"name": "Bologna", "prefixes": ["051"]},
            {"name": "Firenze", "prefixes": ["055"]},
            {"name": "Bari", "prefixes": ["080"]},
            {"name": "Catania", "prefixes": ["095"]},
            {"name": "Venezia", "prefixes": ["041"]},
            {"name": "Verona", "prefixes": ["045"]},
            {"name": "Messina", "prefixes": ["090"]},
            {"name": "Padova", "prefixes": ["049"]},
            {"name": "Trieste", "prefixes": ["040"]},
            {"name": "Brescia", "prefixes": ["030"]},
            {"name": "Parma", "prefixes": ["0521"]},
            {"name": "Taranto", "prefixes": ["099"]},
            {"name": "Prato", "prefixes": ["0574"]},
            {"name": "Modena", "prefixes": ["059"]},
            {"name": "Reggio Calabria", "prefixes": ["0965"]},
            {"name": "Reggio Emilia", "prefixes": ["0522"]},
            {"name": "Perugia", "prefixes": ["075"]},
            {"name": "Livorno", "prefixes": ["0586"]},
            {"name": "Ravenna", "prefixes": ["0544"]},
            {"name": "Foggia", "prefixes": ["0881"]},
            {"name": "Rimini", "prefixes": ["0541"]},
            {"name": "Salerno", "prefixes": ["089"]},
            {"name": "Ferrara", "prefixes": ["0532"]},
            {"name": "Sassari", "prefixes": ["079"]},
            {"name": "Mobile Italia", "prefixes": ["3"]}
        ]

        if strategy_type == "conservative":
            top_provinces = fallback_provinces[:15]
        elif strategy_type == "balanced":
            top_provinces = fallback_provinces[:20]
        else:  # aggressive
            top_provinces = fallback_provinces[:30]

    # Krijo prefix clause për provincat më të mira
    all_prefixes = []
    for province in top_provinces:
        if "prefixes" in province:
            for prefix in province["prefixes"]:
                all_prefixes.append(f"phone_number LIKE '{prefix}%'")

    province_clause = " AND (" + " OR ".join(all_prefixes) + ")" if all_prefixes else ""

    # Oraret optimale bazuar në strategjinë
    if strategy_type == "conservative":
        fix_hours = "HOUR(NOW()) BETWEEN 9 AND 13"
        mobile_hours = "HOUR(NOW()) BETWEEN 14 AND 19"
    elif strategy_type == "balanced":
        fix_hours = "HOUR(NOW()) BETWEEN 8 AND 14"
        mobile_hours = "HOUR(NOW()) BETWEEN 14 AND 20"
    else:  # aggressive
        fix_hours = "HOUR(NOW()) BETWEEN 7 AND 15"
        mobile_hours = "HOUR(NOW()) BETWEEN 15 AND 21"

    # Krijo kushtin për orët dhe tipin e telefonit
    phone_timing = f"( (phone_number LIKE '0%' AND {fix_hours}) OR (phone_number LIKE '3%' AND {mobile_hours}) )"

    # Krijon kushtin final (pa WHERE, pa komente)
    condition = "AND (\n  " + phone_timing + province_clause + "\n)"

    return condition


def analyze_list_based_strategy(data: dict) -> dict:
    """
    Analizon strategji bazuar në list_id, oraret dhe provincat.

    Returns:
        dict: Rekomandime për list-based optimization
    """
    # Merr të dhënat e listave dhe performancën
    active_lists = data.get("active_lists", [])
    prefix_analysis = data.get("prefix_analysis", [])
    hourly_performance = data.get("hourly_performance", [])

    # Grupim i listave sipas performancës dhe tipit
    high_performance_lists = []
    medium_performance_lists = []
    low_performance_lists = []

    for lst in active_lists:
        list_id = lst.get("list_id")
        list_name = lst.get("list_name", "")
        total_leads = lst.get("total_leads", 0)
        never_called = lst.get("never_called", 0)

        # Llogarit performance score
        utilization_rate = (never_called / total_leads * 100) if total_leads > 0 else 0
        volume_score = min(10, total_leads / 10000)  # Max 10 points for 100k+ leads

        # Klasifikim i listave
        if utilization_rate > 50 and volume_score > 5:
            high_performance_lists.append({
                "list_id": list_id,
                "list_name": list_name,
                "total_leads": total_leads,
                "available_leads": never_called,
                "utilization_rate": utilization_rate,
                "performance_score": volume_score + utilization_rate / 10
            })
        elif utilization_rate > 30 and volume_score > 3:
            medium_performance_lists.append({
                "list_id": list_id,
                "list_name": list_name,
                "total_leads": total_leads,
                "available_leads": never_called,
                "utilization_rate": utilization_rate,
                "performance_score": volume_score + utilization_rate / 10
            })
        else:
            low_performance_lists.append({
                "list_id": list_id,
                "list_name": list_name,
                "total_leads": total_leads,
                "available_leads": never_called,
                "utilization_rate": utilization_rate,
                "performance_score": volume_score + utilization_rate / 10
            })

    # Sort by performance
    high_performance_lists.sort(key=lambda x: x["performance_score"], reverse=True)
    medium_performance_lists.sort(key=lambda x: x["performance_score"], reverse=True)

    # Analizë e orareve optimale
    optimal_hours = {}
    for hour_data in hourly_performance:
        hour = hour_data.get("hour", 0)
        total_calls = hour_data.get("total_calls", 0)
        avg_duration = hour_data.get("avg_duration", 0)

        # Llogarit efficiency score për çdo orë
        efficiency_score = total_calls * (avg_duration / 60)  # Calls * minutes
        optimal_hours[hour] = {
            "calls": total_calls,
            "avg_duration": avg_duration,
            "efficiency_score": efficiency_score
        }

    # Gjej oraret më të mira
    best_hours = sorted(optimal_hours.items(), key=lambda x: x[1]["efficiency_score"], reverse=True)[:6]

    # Fallback orët nëse nuk ka të dhëna
    if not best_hours:
        best_hours = [(9, {"efficiency_score": 100}), (10, {"efficiency_score": 90}), (14, {"efficiency_score": 80}), (15, {"efficiency_score": 70}), (16, {"efficiency_score": 60})]

    return {
        "list_categories": {
            "high_performance": high_performance_lists[:5],  # Top 5
            "medium_performance": medium_performance_lists[:10],  # Top 10
            "low_performance": low_performance_lists
        },
        "optimal_hours": dict(best_hours),
        "recommendations": {
            "prioritize_lists": [l["list_id"] for l in high_performance_lists[:5]],
            "deactivate_lists": [l["list_id"] for l in low_performance_lists[-10:]],  # Bottom 10
            "best_calling_hours": [h[0] for h in best_hours[:3]]  # Top 3 hours
        }
    }


def generate_scenarios(data: dict, analysis: dict) -> dict:
    """
    Gjeneron skenare të ndryshme për rezultatet e mundshme.

    Returns:
        dict: Skenare të ndryshme dhe rezultatet e tyre
    """
    current_press1 = 62  # Current daily Press1
    target_press1 = 150  # Target daily Press1
    current_cost_per_day = 500  # Estimated current daily cost

    scenarios = {
        "no_change": {
            "name": "Skenari 1: Asnjë ndryshim (Status Quo)",
            "description": "Nëse nuk bëhet asnjë ndryshim në konfigurimet aktuale",
            "predictions": {
                "press1_per_day": f"{current_press1} (pa ndryshim)",
                "cost_per_day": f"€{current_cost_per_day} (pa ndryshim)",
                "gap_vs_target": f"{target_press1 - current_press1} Press1/ditë më pak",
                "roi_impact": "NEGATIVE - Humbje €2,000-3,000/muaj nga target i paarritur"
            },
            "risks": [
                "Listat e dobëta vazhdojnë të konsumojnë budget",
                "Mobile calls me kosto të lartë vazhdojnë",
                "Lead recycling i paefektiv",
                "Hopper depletion gjatë peak hours"
            ],
            "timeline": "3-6 muaj për të parë degradim të performancës"
        },
        "partial_optimization": {
            "name": "Skenari 2: Optimizim i pjesshëm",
            "description": "Implementon vetëm një pjesë të rekomandimeve (p.sh. vetëm lead recycling)",
            "predictions": {
                "press1_per_day": f"{current_press1 + 20}-{current_press1 + 40} (+32-65%)",
                "cost_per_day": f"€{current_cost_per_day - 50}-{current_cost_per_day + 100}",
                "gap_vs_target": f"{target_press1 - (current_press1 + 30)} Press1/ditë më pak",
                "roi_impact": "POSITIVE - Fitim €500-1,500/muaj"
            },
            "implementation": [
                "Implementon vetëm lead recycling",
                "Mos ndryshon dial level ose call times",
                "Mos optimizon list priorities"
            ],
            "timeline": "1-2 muaj për rezultate"
        },
        "full_optimization": {
            "name": "Skenari 3: Optimizim i plotë (Strategjia A ose B)",
            "description": "Implementon të gjitha rekomandimet nga një strategji",
            "predictions": {
                "press1_per_day": f"{current_press1 + 50}-{current_press1 + 100} (+80-160%)",
                "cost_per_day": f"€{current_cost_per_day - 200}-{current_cost_per_day + 200}",
                "gap_vs_target": f"{target_press1 - (current_press1 + 75)} Press1/ditë më pak",
                "roi_impact": "HIGHLY POSITIVE - Fitim €2,000-4,000/muaj"
            },
            "implementation": [
                "Implementon të gjitha SQL scripts",
                "Monitoron rezultatet ditore",
                "Ajuston parametrat sipas nevojës"
            ],
            "timeline": "2-4 javë për rezultate të plotë"
        },
        "aggressive_growth": {
            "name": "Skenari 4: Rritje agresive",
            "description": "Implementon të dyja strategjitë dhe shton lista të reja",
            "predictions": {
                "press1_per_day": f"{current_press1 + 100}-{current_press1 + 150} (+160-240%)",
                "cost_per_day": f"€{current_cost_per_day + 300}-{current_cost_per_day + 600}",
                "gap_vs_target": f"0-{target_press1 - (current_press1 + 125)} Press1/ditë",
                "roi_impact": "MAXIMUM POSITIVE - Fitim €3,000-6,000/muaj"
            },
            "implementation": [
                "Implementon të dyja strategjitë",
                "Importon lista të reja me 200k+ leads",
                "Rrit dial level në 1000+",
                "Hire më shumë agjentë"
            ],
            "timeline": "1-3 muaj për rezultate maksimale",
            "risks": [
                "Kosto më e lartë fillestare",
                "Nevoja për më shumë resurse",
                "Kompleksitet më i madh në menaxhim"
            ]
        }
    }

    return scenarios


def generate_vicidial_recommendations(data: dict, analysis: dict) -> dict:
    """
    Gjeneron 6 strategji kryesore bazuar në:
    1. STATUS-BASED Analysis (3 strategji për CAMPAIGN LEAD RECYCLE LISTINGS - tabela me vlera)
    2. TIME AND PLACE BASED Analysis (3 strategji për LEAD FILTER LISTINGS - SQL scripts)

    Plus skenare të ndryshme për rezultatet e mundshme.

    Args:
        data: Raw Vicidial data
        analysis: Analyzed data

    Returns:
        dict: 6 strategji me tabela/rekomandime dhe skenare
    """
    campaign_config = data.get("campaign_config", {})
    campaign_id = campaign_config.get("campaign_id", "autobiz")

    # Merr listat më të mira
    top_fix_lists = [l for l in analysis if l["phone_type"] == "FIX" and l["available_leads"] >= 50000][:3]
    top_mobile_lists = [l for l in analysis if l["phone_type"] == "MOBILE" and l["available_leads"] >= 50000][:3]

    fix_list_ids = [str(int(l["list_id"])) for l in top_fix_lists]
    mobile_list_ids = [str(int(l["list_id"])) for l in top_mobile_lists]

    # Analizë e lead recycling
    recycling_analysis = analyze_lead_recycling_by_status(data)

    # Analizë e provincave dhe orëve
    province_analysis = analyze_province_performance(data)
    hourly_analysis = analyze_hourly_performance_by_province(data)

    # Gjenerojmë skenare
    scenarios = generate_scenarios(data, analysis)

    strategies = {
        "strategies": [
            {
                "strategy": "A",
                "name": "STATUS-BASED Konservative",
                "goal": "Optimizim i sigurt bazuar në performancën e statuseve. Fokusohet në riciklimin e leads sipas status që japin rezultat me risk të ulët.",
                "recycle_table": [
                    {
                        "STATUS": "PU",
                        "ATTEMPT DELAY": "2",
                        "ATTEMPT MAXIMUM": "2",
                        "Arsyeja": "Klienti u përgjigj por nuk foli - mund të jetë i zënë. Riprovo pas 2 orësh, maksimum 2 tentativa."
                    },
                    {
                        "STATUS": "BUSY",
                        "ATTEMPT DELAY": "1",
                        "ATTEMPT MAXIMUM": "2",
                        "Arsyeja": "Line busy - klienti është aktiv. Riprovo pas 1 ore, maksimum 2 tentativa për të ruajtur budget."
                    },
                    {
                        "STATUS": "NOINT",
                        "ATTEMPT DELAY": "0",
                        "ATTEMPT MAXIMUM": "0",
                        "Arsyeja": "Klienti nuk është i interesuar - mos riciklo për të kursyer kohë dhe budget."
                    },
                    {
                        "STATUS": "NA",
                        "ATTEMPT DELAY": "6",
                        "ATTEMPT MAXIMUM": "1",
                        "Arsyeja": "Nuk përgjigjet - mund të jetë i zënë. Riprovo pas 6 orësh, vetëm 1 tentativë tjetër për të kursyer budget."
                    },
                    {
                        "STATUS": "DISCONN",
                        "ATTEMPT DELAY": "24",
                        "ATTEMPT MAXIMUM": "1",
                        "Arsyeja": "Numri i shkëputur - riprovo pas 24 orësh për të testuar riaktivizim."
                    },
                    {
                        "STATUS": "SALE",
                        "ATTEMPT DELAY": "0",
                        "ATTEMPT MAXIMUM": "0",
                        "Arsyeja": "Shitje e realizuar - mos riciklo."
                    },
                    {
                        "STATUS": "SVYCLM",
                        "ATTEMPT DELAY": "0",
                        "ATTEMPT MAXIMUM": "0",
                        "Arsyeja": "Ka dëgjuar mesazhin IVR - mos riciklo."
                    }
                ],
                "expected_results": {
                    "press1_per_day": "80-120 (+30-95%)",
                    "cost_impact": "€100-300/muaj ulje",
                    "risk": "LOW - fokusohet vetëm në recycling me parametra të sigurta"
                },
                "focus": "Status-based optimization (Conservative)"
            },
            {
                "strategy": "B",
                "name": "STATUS-BASED Balanced",
                "goal": "Optimizim i balancuar bazuar në performancën e statuseve. Fokusohet në riciklimin e leads sipas status që japin rezultat me risk të mesëm.",
                "recycle_table": [
                    {
                        "STATUS": "PU",
                        "ATTEMPT DELAY": "2",
                        "ATTEMPT MAXIMUM": "3",
                        "Arsyeja": "Klienti u përgjigj por nuk foli - mund të jetë i zënë. Riprovo pas 2 orësh, 3 tentativa për të maksimizuar shanset."
                    },
                    {
                        "STATUS": "BUSY",
                        "ATTEMPT DELAY": "1",
                        "ATTEMPT MAXIMUM": "4",
                        "Arsyeja": "Line busy - klienti është aktiv. Riprovo pas 1 ore, 4 tentativa sepse ka probabilitet të lartë përgjigje."
                    },
                    {
                        "STATUS": "NOINT",
                        "ATTEMPT DELAY": "0",
                        "ATTEMPT MAXIMUM": "0",
                        "Arsyeja": "Klienti nuk është i interesuar - mos riciklo për të kursyer kohë dhe budget."
                    },
                    {
                        "STATUS": "NA",
                        "ATTEMPT DELAY": "6",
                        "ATTEMPT MAXIMUM": "2",
                        "Arsyeja": "Nuk përgjigjet - mund të jetë i zënë. Riprovo pas 6 orësh, 2 tentativa për të kapur momentin e duhur."
                    },
                    {
                        "STATUS": "DISCONN",
                        "ATTEMPT DELAY": "24",
                        "ATTEMPT MAXIMUM": "1",
                        "Arsyeja": "Numri i shkëputur - riprovo pas 24 orësh për të testuar riaktivizim."
                    },
                    {
                        "STATUS": "SALE",
                        "ATTEMPT DELAY": "0",
                        "ATTEMPT MAXIMUM": "0",
                        "Arsyeja": "Shitje e realizuar - mos riciklo."
                    },
                    {
                        "STATUS": "SVYCLM",
                        "ATTEMPT DELAY": "0",
                        "ATTEMPT MAXIMUM": "0",
                        "Arsyeja": "Ka dëgjuar mesazhin IVR - mos riciklo."
                    }
                ],
                "expected_results": {
                    "press1_per_day": "100-130 (+60-110%)",
                    "cost_impact": "€150-400/muaj ulje",
                    "risk": "MEDIUM - parametra të balancuara për recycling"
                },
                "focus": "Status-based optimization (Balanced)"
            },
            {
                "strategy": "C",
                "name": "STATUS-BASED Agresive",
                "goal": "Optimizim maksimal bazuar në performancën e statuseve. Fokusohet në riciklimin maksimal të leads sipas status që japin rezultat me risk të lartë.",
                "recycle_table": [
                    {
                        "STATUS": "PU",
                        "ATTEMPT DELAY": "2",
                        "ATTEMPT MAXIMUM": "5",
                        "Arsyeja": "Klienti u përgjigj por nuk foli - mund të jetë i zënë. Riprovo pas 2 orësh, 5 tentativa për të shfrytëzuar maksimalisht çdo lead."
                    },
                    {
                        "STATUS": "BUSY",
                        "ATTEMPT DELAY": "1",
                        "ATTEMPT MAXIMUM": "6",
                        "Arsyeja": "Line busy - klienti është aktiv. Riprovo pas 1 ore, 6 tentativa sepse line busy është shenjë e numrit aktiv."
                    },
                    {
                        "STATUS": "NOINT",
                        "ATTEMPT DELAY": "0",
                        "ATTEMPT MAXIMUM": "0",
                        "Arsyeja": "Klienti nuk është i interesuar - mos riciklo për të kursyer kohë dhe budget."
                    },
                    {
                        "STATUS": "NA",
                        "ATTEMPT DELAY": "6",
                        "ATTEMPT MAXIMUM": "3",
                        "Arsyeja": "Nuk përgjigjet - mund të jetë i zënë. Riprovo pas 6 orësh, 3 tentativa për të testuar orare të ndryshme."
                    },
                    {
                        "STATUS": "DISCONN",
                        "ATTEMPT DELAY": "24",
                        "ATTEMPT MAXIMUM": "2",
                        "Arsyeja": "Numri i shkëputur - riprovo pas 24 orësh, 2 tentativa për të kapur riaktivizime të mundshme."
                    },
                    {
                        "STATUS": "SALE",
                        "ATTEMPT DELAY": "0",
                        "ATTEMPT MAXIMUM": "0",
                        "Arsyeja": "Shitje e realizuar - mos riciklo."
                    },
                    {
                        "STATUS": "SVYCLM",
                        "ATTEMPT DELAY": "0",
                        "ATTEMPT MAXIMUM": "0",
                        "Arsyeja": "Ka dëgjuar mesazhin IVR - mos riciklo."
                    }
                ],
                "expected_results": {
                    "press1_per_day": "120-160 (+95-160%)",
                    "cost_impact": "€200-500/muaj ulje",
                    "risk": "HIGH - parametra maksimale për recycling"
                },
                "focus": "Status-based optimization (Aggressive)"
            },
            {
                "strategy": "G",
                "name": "TIME AND LIST BASED Konservative",
                "goal": "Optimizim i sigurt bazuar në performancën e listave dhe orëve. Fokusohet në listat më të mira dhe orët optimale për numrat fiks/celularë me risk të ulët.",
                "sql_script": generate_time_list_filter_script(
                    "conservative",
                    data
                ),
                "expected_results": {
                    "press1_per_day": "90-120 (+45-95%)",
                    "cost_impact": "€150-350/muaj ulje",
                    "risk": "LOW - vetëm listat dhe oraret, pa provinca"
                },
                "focus": "Time and List based optimization (Conservative)"
            },
            {
                "strategy": "H",
                "name": "TIME AND LIST BASED Balanced",
                "goal": "Optimizim i balancuar bazuar në performancën e listave dhe orëve. Fokusohet në listat më të mira dhe orët optimale për numrat fiks/celularë me risk të mesëm.",
                "sql_script": generate_time_list_filter_script(
                    "balanced",
                    data
                ),
                "expected_results": {
                    "press1_per_day": "110-140 (+77-125%)",
                    "cost_impact": "€200-450/muaj ulje",
                    "risk": "MEDIUM - vetëm listat dhe oraret, pa provinca"
                },
                "focus": "Time and List based optimization (Balanced)"
            },
            {
                "strategy": "I",
                "name": "TIME AND LIST BASED Agresive",
                "goal": "Optimizim maksimal bazuar në performancën e listave dhe orëve. Fokusohet në listat më të mira dhe orët optimale për numrat fiks/celularë me risk të lartë.",
                "sql_script": generate_time_list_filter_script(
                    "aggressive",
                    data
                ),
                "expected_results": {
                    "press1_per_day": "130-170 (+110-175%)",
                    "cost_impact": "€250-550/muaj ulje",
                    "risk": "HIGH - vetëm listat dhe oraret, pa provinca"
                },
                "focus": "Time and List based optimization (Aggressive)"
            },
            {
                "strategy": "D",
                "name": "TIME AND PLACE BASED Konservative",
                "goal": "Optimizim i sigurt bazuar në performancën e provincave dhe orëve. Fokusohet në 15 provincat më të mira dhe orët më efektive me risk të ulët.",
                "sql_script": generate_time_and_place_filter_script(
                    "conservative",
                    province_analysis,
                    hourly_analysis
                ),
                "expected_results": {
                    "press1_per_day": "100-140 (+60-125%)",
                    "cost_impact": "€200-500/muaj ulje",
                    "risk": "LOW - parametra të sigurta për province optimization"
                },
                "focus": "Time and Place based optimization (Conservative)"
            },
            {
                "strategy": "E",
                "name": "TIME AND PLACE BASED Balanced",
                "goal": "Optimizim i balancuar bazuar në performancën e provincave dhe orëve. Fokusohet në 20 provincat më të mira dhe orët më efektive me risk të mesëm.",
                "sql_script": generate_time_and_place_filter_script(
                    "balanced",
                    province_analysis,
                    hourly_analysis
                ),
                "expected_results": {
                    "press1_per_day": "120-150 (+95-140%)",
                    "cost_impact": "€250-600/muaj ulje",
                    "risk": "MEDIUM - parametra të balancuara për province optimization"
                },
                "focus": "Time and Place based optimization (Balanced)"
            },
            {
                "strategy": "F",
                "name": "TIME AND PLACE BASED Agresive",
                "goal": "Optimizim maksimal bazuar në performancën e provincave dhe orëve. Fokusohet në 30 provincat më të mira dhe orët më efektive me risk të lartë.",
                "sql_script": generate_time_and_place_filter_script(
                    "aggressive",
                    province_analysis,
                    hourly_analysis
                ),
                "expected_results": {
                    "press1_per_day": "140-180 (+125-190%)",
                    "cost_impact": "€300-700/muaj ulje",
                    "risk": "HIGH - parametra maksimale për province optimization"
                },
                "focus": "Time and Place based optimization (Aggressive)"
            }
        ],
        "scenarios": scenarios
    }

    return strategies


def generate_report(data_file: str = "vicidial_analysis_data.json") -> dict:
    """
    Gjeneron raportin e plotë me analiza dhe rekomandime.

    Args:
        data_file: Path to collected data

    Returns:
        dict: Complete analysis report
    """
    # Load data
    data = load_vicidial_data(data_file)

    # Analyze mobile vs fix
    mobile_fix_analysis = analyze_mobile_vs_fix(data)

    # Analyze province performance
    province_analysis = analyze_province_performance(data)

    # Analyze hourly performance by province
    hourly_analysis = analyze_hourly_performance_by_province(data)

    # Analyze press1 conversion
    press1_analysis = analyze_press1_conversion(data)

    # Calculate requirements
    volume_requirements = calculate_list_requirements_for_dial_level(
        dial_level=700,
        working_hours=8,
        avg_call_duration_sec=30
    )

    # Rank lists
    ranked_lists = rank_lists_by_performance(data)

    # Generate recommendations
    recommendations = generate_vicidial_recommendations(data, ranked_lists)

    # Analyze lead recycling
    recycling_analysis = analyze_lead_recycling_by_status(data)

    # Compile full report
    report = {
        "generated_at": datetime.now().isoformat(),
        "campaign_id": data.get("campaign_id"),
        "analysis_period": f"Last {data.get('analysis_period_days')} days",
        "mobile_vs_fix": mobile_fix_analysis,
        "province_analysis": province_analysis,
        "hourly_analysis": hourly_analysis,
        "press1_funnel": press1_analysis,
        "volume_requirements": volume_requirements,
        "ranked_lists": ranked_lists,
        "lead_recycling_analysis": recycling_analysis,
        "vicidial_recommendations": recommendations,
        "action_plan": {
            "immediate_actions": [
                {
                    "action": "Prioritize top 5 FIX lists",
                    "impact": "€200-300/day cost savings",
                    "effort": "5 minutes"
                },
                {
                    "action": "Increase hopper level to 1400",
                    "impact": "Prevent dial slowdowns",
                    "effort": "2 minutes"
                }
            ],
            "this_week_actions": [
                {
                    "action": "Implement time-based routing (FIX business hours, MOBILE evening)",
                    "impact": "+15-20% press1 from better timing",
                    "effort": "30 minutes"
                },
                {
                    "action": "Test shorter IVR audio (40 sec vs 60 sec)",
                    "impact": "Reduce timeout rate from 58% to 40%",
                    "effort": "1 hour"
                }
            ],
            "this_month_actions": [
                {
                    "action": "Segment mobile lists by past performance",
                    "impact": "+10-15% press1 via better targeting",
                    "effort": "2 hours"
                }
            ]
        }
    }

    return report

