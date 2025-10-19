"""Test script për list analyzer"""
import json
from core.list_analyzer import generate_report
from pprint import pprint

print("🔬 Testing List Analyzer...")
print("="*80)

# Generate full report
report = generate_report("vicidial_analysis_data.json")

# Display key findings
print("\n📊 PRESS 1 FUNNEL ANALYSIS:")
print("-"*80)
funnel = report["press1_funnel"]["funnel"]
print(f"Total Dials (7 days): {int(funnel['total_dials_per_week']):,}")
print(f"Pick Up (PU): {int(funnel['pu_pick_up']):,} ({funnel['conversion_rates']['dials_to_pu']}%)")
print(f"Listened Full (SVYCLM): {int(funnel['svyclm_listened_full']):,} ({funnel['conversion_rates']['pu_to_svyclm']}%)")
print(f"Press 1: {int(funnel['press1_actual'])} ({funnel['conversion_rates']['svyclm_to_press1']}%)")

print("\n🎯 TARGET GAP:")
print("-"*80)
daily = report["press1_funnel"]["daily_metrics"]
print(f"Current: {daily['current_press1_per_day']}/day")
print(f"Target: {daily['target_press1_per_day']}/day")
print(f"Gap: {daily['gap']} ({daily['improvement_needed_percent']}% improvement needed)")

print("\n📱 MOBILE VS FIX:")
print("-"*80)
mvf = report["mobile_vs_fix"]
print(f"Mobile: {int(mvf['mobile']['total_calls']):,} calls ({mvf['mobile']['percentage']}%) - Cost: €{mvf['mobile']['cost']:.2f}")
print(f"Fix: {int(mvf['fix']['total_calls']):,} calls ({mvf['fix']['percentage']}%) - Cost: €{mvf['fix']['cost']:.2f}")
print(f"Cost premium for mobile: {mvf['comparison']['mobile_cost_premium']}x")
print(f"Potential savings (10% shift): €{mvf['comparison']['potential_savings_if_10pct_shift']:.2f}/week")

print("\n🏆 TOP 10 LISTS BY QUALITY:")
print("-"*80)
print(f"{'Rank':<5} {'List Name':<40} {'Score':<6} {'Available':<12} {'Type':<8} {'Recommendation'}")
print("-"*80)
for i, lst in enumerate(report["ranked_lists"][:10], 1):
    print(f"{i:<5} {lst['list_name'][:38]:<40} {lst['quality_score']:<6.1f} {lst['available_leads']:>10,}  {lst['phone_type']:<8} {lst['recommendation']}")

print("\n🔧 VICIDIAL RECOMMENDATIONS:")
print("-"*80)
for cfg in report["vicidial_recommendations"]["configurations"][:3]:
    print(f"\n{cfg['priority']}. {cfg['title']}")
    print(f"   Impact: {cfg['impact']}")
    print(f"   {cfg['description']}")

print("\n✅ Report generated successfully!")
print(f"Full report saved to: list_analysis_report.json")

# Save full report
with open("list_analysis_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
















