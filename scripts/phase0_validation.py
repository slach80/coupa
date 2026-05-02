#!/usr/bin/env python3
"""
Phase 0 Validation Script
Validates classification system assumptions against real data from SAMPLE.xlsx

This addresses Critical Review Item #2: "Accuracy Target (95%) Has No Baseline"
By comparing AI classifications against existing human classifications.
"""

import pandas as pd
from rapidfuzz import fuzz
from collections import Counter
import json

# Configuration
SAMPLE_FILE = "/home/slach/Downloads/SAMPLE.xlsx"
CONFIDENCE_THRESHOLD = 70  # Auto-assign threshold

def load_data():
    """Load all invoice data and activity codes"""
    print("=" * 80)
    print("PHASE 0 VALIDATION - Activity Code Classification System")
    print("=" * 80)
    print("\n📥 Loading data from SAMPLE.xlsx...")

    # Load activity codes with supplier mappings
    codes_df = pd.read_excel(SAMPLE_FILE, sheet_name='Activity Codes_Active')

    # Load all 4 months of invoices
    months = ['Nov2025_Inv', 'Dec2025_Inv', 'Jan2026_Inv', 'Feb2026_Inv']
    all_invoices = []

    for month in months:
        df = pd.read_excel(SAMPLE_FILE, sheet_name=month)
        df['month'] = month
        all_invoices.append(df)

    invoices_df = pd.concat(all_invoices, ignore_index=True)

    print(f"   ✓ Loaded {len(codes_df)} activity codes")
    print(f"   ✓ Loaded {len(invoices_df):,} invoice lines from 4 months")

    return codes_df, invoices_df

def build_supplier_mappings(codes_df):
    """Extract supplier-to-code mappings from Activity Codes_Active"""
    mappings = {}

    for _, row in codes_df.iterrows():
        code = row['Activity Code']

        # Check if Supplier Names column exists and has data (note: no underscore)
        if 'Supplier Names' in row and pd.notna(row['Supplier Names']):
            suppliers = str(row['Supplier Names']).split('|')
            for supplier in suppliers:
                supplier = supplier.strip().upper()
                if supplier:
                    mappings[supplier] = code

    print(f"   ✓ Built {len(mappings)} supplier-to-code mappings")
    return mappings

def classify_invoice(supplier, commodity, description, mappings):
    """
    Simple 2-stage classifier for validation:
    Stage 1: Exact match against supplier mappings
    Stage 2: Fuzzy match (threshold 80%)

    Returns: (predicted_code, confidence, method)
    """
    supplier_upper = str(supplier).upper().strip()

    # Stage 1: Exact match
    if supplier_upper in mappings:
        return (mappings[supplier_upper], 95, 'exact_match')

    # Stage 2: Fuzzy match
    best_match = None
    best_score = 0

    for known_supplier, code in mappings.items():
        score = fuzz.ratio(supplier_upper, known_supplier)
        if score > best_score:
            best_score = score
            best_match = code

    if best_score >= 80:
        # Scale confidence: 80-100 score -> 60-90 confidence
        confidence = 60 + (best_score - 80) * 1.5
        return (best_match, int(confidence), 'fuzzy_match')

    # No match
    return (None, 0, 'no_match')

def analyze_data_quality(invoices_df):
    """Analyze data quality metrics"""
    print("\n📊 Data Quality Analysis")
    print("-" * 80)

    total = len(invoices_df)

    # Missing fields
    missing_supplier = invoices_df['Supplier'].isna().sum()
    missing_commodity = invoices_df['Commodity'].isna().sum()
    missing_code = invoices_df['IT Activity Code'].isna().sum()

    print(f"   Missing Supplier:     {missing_supplier:,} ({missing_supplier/total*100:.1f}%)")
    print(f"   Missing Commodity:    {missing_commodity:,} ({missing_commodity/total*100:.1f}%)")
    print(f"   Missing Activity Code: {missing_code:,} ({missing_code/total*100:.1f}%)")

    # Unique suppliers
    unique_suppliers = invoices_df['Supplier'].nunique()
    print(f"\n   Unique Suppliers: {unique_suppliers:,}")

    # Supplier variations (same supplier, different spellings)
    supplier_freq = invoices_df['Supplier'].value_counts()
    print(f"   Top 5 suppliers:")
    for supplier, count in supplier_freq.head(5).items():
        print(f"      - {supplier}: {count} invoices")

    # Existing classifications
    classified = invoices_df['IT Activity Code'].notna().sum()
    unclassified = missing_code

    print(f"\n   Human Classified:   {classified:,} ({classified/total*100:.1f}%)")
    print(f"   Unclassified:       {unclassified:,} ({unclassified/total*100:.1f}%)")

    return classified, unclassified

def validate_accuracy(invoices_df, mappings):
    """
    Validate AI accuracy against human baseline
    Compare AI predictions to existing human classifications
    """
    print("\n🎯 Accuracy Validation (AI vs Human Baseline)")
    print("-" * 80)

    # Filter to only invoices that humans already classified
    classified_df = invoices_df[invoices_df['IT Activity Code'].notna()].copy()

    if len(classified_df) == 0:
        print("   ⚠️  No human classifications found to validate against")
        return None

    print(f"   Testing on {len(classified_df):,} human-classified invoices...")

    # Run AI classifier on these invoices
    results = []
    for _, inv in classified_df.iterrows():
        pred_code, confidence, method = classify_invoice(
            inv['Supplier'],
            inv.get('Commodity', ''),
            inv.get('Description', ''),
            mappings
        )

        human_code = inv['IT Activity Code']
        match = (pred_code == human_code) if pred_code else False

        results.append({
            'human_code': human_code,
            'predicted_code': pred_code,
            'confidence': confidence,
            'method': method,
            'match': match
        })

    results_df = pd.DataFrame(results)

    # Calculate accuracy
    total_predictions = len(results_df[results_df['predicted_code'].notna()])
    matches = results_df['match'].sum()

    if total_predictions > 0:
        accuracy = (matches / total_predictions) * 100
    else:
        accuracy = 0

    print(f"\n   AI Predictions:  {total_predictions:,} / {len(classified_df):,}")
    print(f"   Matches:         {matches:,}")
    print(f"   Accuracy:        {accuracy:.1f}%")

    # Breakdown by confidence level
    high_conf = results_df[results_df['confidence'] >= 70]
    if len(high_conf) > 0:
        high_acc = (high_conf['match'].sum() / len(high_conf)) * 100
        print(f"\n   High Confidence (≥70%): {len(high_conf):,} predictions, {high_acc:.1f}% accurate")

    # Method breakdown
    print(f"\n   By Method:")
    for method in results_df['method'].unique():
        method_df = results_df[results_df['method'] == method]
        method_matches = method_df['match'].sum()
        method_acc = (method_matches / len(method_df)) * 100 if len(method_df) > 0 else 0
        print(f"      {method:15s}: {len(method_df):4d} attempts, {method_matches:4d} matches ({method_acc:.1f}%)")

    return accuracy, results_df

def measure_auto_assign_rate(invoices_df, mappings):
    """
    Measure auto-assign rate on ALL invoices (classified + unclassified)
    This validates the 60% auto-assign target
    """
    print("\n📈 Auto-Assignment Rate Validation")
    print("-" * 80)

    print(f"   Running classifier on all {len(invoices_df):,} invoices...")

    auto_assigned = 0
    needs_review = 0
    no_match = 0

    for _, inv in invoices_df.iterrows():
        pred_code, confidence, method = classify_invoice(
            inv['Supplier'],
            inv.get('Commodity', ''),
            inv.get('Description', ''),
            mappings
        )

        if confidence >= CONFIDENCE_THRESHOLD:
            auto_assigned += 1
        elif confidence > 0:
            needs_review += 1
        else:
            no_match += 1

    total = len(invoices_df)
    auto_pct = (auto_assigned / total) * 100
    review_pct = (needs_review / total) * 100
    no_match_pct = (no_match / total) * 100

    print(f"\n   Auto-Assigned (≥{CONFIDENCE_THRESHOLD}%):  {auto_assigned:,} ({auto_pct:.1f}%)")
    print(f"   Needs Review (1-{CONFIDENCE_THRESHOLD-1}%): {needs_review:,} ({review_pct:.1f}%)")
    print(f"   No Match (0%):          {no_match:,} ({no_match_pct:.1f}%)")

    return auto_pct

def generate_report(accuracy, auto_assign_rate, classified_count, unclassified_count):
    """Generate final validation report"""
    print("\n" + "=" * 80)
    print("📋 VALIDATION REPORT - Summary")
    print("=" * 80)

    total = classified_count + unclassified_count

    print(f"\n🎯 ACCURACY VALIDATION:")
    print(f"   Human Baseline:      {classified_count:,} classified ({classified_count/total*100:.1f}%)")
    print(f"   AI Accuracy:         {accuracy:.1f}%")

    target_met = "✅ YES" if accuracy >= 95 else "⚠️  NO"
    print(f"   Meets 95% Target:    {target_met}")

    print(f"\n📈 AUTO-ASSIGN RATE:")
    print(f"   Current (manual):    19% ({classified_count:,} / {total:,})")
    print(f"   AI Auto-Assign:      {auto_assign_rate:.1f}%")
    print(f"   Improvement:         +{auto_assign_rate - 19:.1f} percentage points")

    target_met = "✅ YES" if auto_assign_rate >= 60 else "⚠️  NO"
    print(f"   Meets 60% Target:    {target_met}")

    print(f"\n💰 ROI IMPLICATIONS:")
    print(f"   Current manual effort: {total:,} invoices → ~{total/100:.0f} hours @ 1 invoice/6min")
    manual_hours = total / 100  # Rough estimate: 6 min per invoice
    ai_review_hours = (total - (total * auto_assign_rate / 100)) / 100
    saved_hours = manual_hours - ai_review_hours
    saved_dollars = saved_hours * 75  # $75/hr labor cost

    print(f"   AI review effort:      ~{ai_review_hours:.0f} hours (only reviewing {100-auto_assign_rate:.1f}%)")
    print(f"   Time savings:          ~{saved_hours:.0f} hours/quarter ({saved_hours/manual_hours*100:.0f}%)")
    print(f"   Cost savings:          ~${saved_dollars:,.0f}/quarter @ $75/hr")
    print(f"   Annual savings:        ~${saved_dollars*4:,.0f}/year")

    print("\n" + "=" * 80)
    print("✅ Validation Complete!")
    print("\nNext Steps:")
    print("   1. Review accuracy breakdown by method above")
    print("   2. Update business-case.html with actual numbers")
    print("   3. Present validated ROI to stakeholders")
    print("=" * 80 + "\n")

def main():
    # Load data
    codes_df, invoices_df = load_data()

    # Build supplier mappings
    mappings = build_supplier_mappings(codes_df)

    # Data quality analysis
    classified_count, unclassified_count = analyze_data_quality(invoices_df)

    # Validate accuracy against human baseline
    accuracy, results_df = validate_accuracy(invoices_df, mappings)

    # Measure auto-assign rate
    auto_assign_rate = measure_auto_assign_rate(invoices_df, mappings)

    # Generate report
    if accuracy is not None:
        generate_report(accuracy, auto_assign_rate, classified_count, unclassified_count)

    print("\n📄 Detailed results saved to: validation_results.json")

    # Save detailed results
    report = {
        "validation_date": pd.Timestamp.now().isoformat(),
        "data_summary": {
            "total_invoices": len(invoices_df),
            "classified": int(classified_count),
            "unclassified": int(unclassified_count),
            "unique_suppliers": int(invoices_df['Supplier'].nunique())
        },
        "accuracy": {
            "ai_accuracy_pct": float(accuracy) if accuracy else 0,
            "target_pct": 95,
            "meets_target": bool(accuracy >= 95 if accuracy else False)
        },
        "auto_assign_rate": {
            "ai_rate_pct": float(auto_assign_rate),
            "target_pct": 60,
            "meets_target": bool(auto_assign_rate >= 60),
            "improvement_vs_manual": float(auto_assign_rate - 19)
        },
        "roi": {
            "estimated_annual_savings_usd": int(((len(invoices_df) / 100) * 0.75 * 75 * 4)),
            "confidence_threshold": CONFIDENCE_THRESHOLD
        }
    }

    with open('validation_results.json', 'w') as f:
        json.dump(report, f, indent=2)

if __name__ == '__main__':
    main()
