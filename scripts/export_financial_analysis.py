#!/usr/bin/env python3
"""
Export classification data to Excel for financial analysis review
Creates multi-tab spreadsheet with:
- Activity codes with vendor relationships
- Classification methods breakdown
- Full classified results
- Unclassified invoices
- Top suppliers analysis
- Activity code summary
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from classification.database import Database, ActivityCode, SupplierActivityMapping


def export_financial_analysis(db_path='classification.db', results_file=None):
    """
    Export comprehensive financial analysis spreadsheet

    Args:
        db_path: Path to SQLite database
        results_file: Path to latest classification results Excel file
    """

    print("=" * 80)
    print("EXPORTING FINANCIAL ANALYSIS DATA")
    print("=" * 80)

    # Initialize database
    db = Database(db_path)
    session = db.get_session()

    # Determine output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'financial_analysis_{timestamp}.xlsx'

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:

        # ===== TAB 1: Activity Codes with Vendor Relationships =====
        print("\n📊 Tab 1: Activity Codes & Vendor Mappings...")
        activity_codes = session.query(ActivityCode).order_by(ActivityCode.activity_code).all()
        supplier_mappings = session.query(SupplierActivityMapping).all()

        # Build vendor list per activity code
        code_vendors = {}
        for mapping in supplier_mappings:
            code = mapping.activity_code
            if code not in code_vendors:
                code_vendors[code] = []
            code_vendors[code].append(mapping.supplier_name)

        # Create activity codes dataframe
        codes_data = []
        for code in activity_codes:
            vendors = code_vendors.get(code.activity_code, [])
            codes_data.append({
                'Activity Code': code.activity_code,
                'Description': code.activity_description,
                'Category': code.level1_type,
                'Vendor Count': len(vendors),
                'Vendors': ', '.join(sorted(vendors)[:10]) + ('...' if len(vendors) > 10 else '')
            })

        df_codes = pd.DataFrame(codes_data)
        df_codes.to_excel(writer, sheet_name='Activity Codes', index=False)
        print(f"   ✓ Exported {len(df_codes)} activity codes")

        # ===== TAB 2: Vendor-to-Code Mappings (Detail) =====
        print("\n📊 Tab 2: Vendor Mappings Detail...")
        mappings_data = []
        for mapping in supplier_mappings:
            # Find activity code details
            code_obj = session.query(ActivityCode).filter_by(activity_code=mapping.activity_code).first()

            mappings_data.append({
                'Supplier': mapping.supplier_name,
                'Activity Code': mapping.activity_code,
                'Code Description': code_obj.activity_description if code_obj else '',
                'Category': code_obj.level1_type if code_obj else '',
                'Source': mapping.source or 'Manual',
                'Confidence': mapping.confidence_score if hasattr(mapping, 'confidence_score') else 100
            })

        df_mappings = pd.DataFrame(mappings_data)
        df_mappings = df_mappings.sort_values(['Activity Code', 'Supplier'])
        df_mappings.to_excel(writer, sheet_name='Vendor Mappings', index=False)
        print(f"   ✓ Exported {len(df_mappings)} vendor mappings")

        # ===== TAB 3-7: Classification Results (if results file provided) =====
        if results_file and Path(results_file).exists():
            print(f"\n📊 Tab 3-7: Classification Results from {results_file}...")

            # Read all sheets from results file
            results_excel = pd.ExcelFile(results_file)

            # Tab 3: Full classified results
            if 'All Classifications' in results_excel.sheet_names:
                df_all = pd.read_excel(results_file, sheet_name='All Classifications')
                df_all.to_excel(writer, sheet_name='All Classifications', index=False)
                print(f"   ✓ Exported {len(df_all)} total classifications")

                # Tab 4: Classification Methods Breakdown
                print("\n📊 Tab 4: Classification Methods...")
                methods_summary = df_all['Method'].value_counts().reset_index()
                methods_summary.columns = ['Classification Method', 'Invoice Count']
                methods_summary['Percentage'] = (methods_summary['Invoice Count'] / len(df_all) * 100).round(2)

                # Add confidence stats per method
                method_details = []
                for method in methods_summary['Classification Method']:
                    method_invoices = df_all[df_all['Method'] == method]
                    method_details.append({
                        'Classification Method': method,
                        'Invoice Count': len(method_invoices),
                        'Percentage': round(len(method_invoices) / len(df_all) * 100, 2),
                        'Avg Confidence': round(method_invoices['Confidence'].mean(), 1),
                        'Min Confidence': method_invoices['Confidence'].min(),
                        'Max Confidence': method_invoices['Confidence'].max()
                    })

                df_methods = pd.DataFrame(method_details)
                df_methods = df_methods.sort_values('Invoice Count', ascending=False)
                df_methods.to_excel(writer, sheet_name='Classification Methods', index=False)
                print(f"   ✓ Exported {len(df_methods)} classification methods")

                # Tab 5: Activity Code Summary (from classified results)
                print("\n📊 Tab 5: Activity Code Summary...")
                # Filter classified invoices only
                df_classified = df_all[df_all['Activity Code'].notna()].copy()

                code_summary = df_classified.groupby('Activity Code').agg({
                    'Supplier': 'count',
                    'Confidence': 'mean'
                }).reset_index()
                code_summary.columns = ['Activity Code', 'Invoice Count', 'Avg Confidence']
                code_summary['Percentage'] = (code_summary['Invoice Count'] / len(df_classified) * 100).round(2)

                # Add code descriptions
                code_desc_map = {row['Activity Code']: row['Description'] for row in codes_data}
                code_summary['Description'] = code_summary['Activity Code'].map(code_desc_map)

                # Add unique supplier count per code
                suppliers_per_code = df_classified.groupby('Activity Code')['Supplier'].nunique().to_dict()
                code_summary['Unique Suppliers'] = code_summary['Activity Code'].map(suppliers_per_code)

                # Reorder columns
                code_summary = code_summary[['Activity Code', 'Description', 'Invoice Count', 'Percentage',
                                             'Unique Suppliers', 'Avg Confidence']]
                code_summary = code_summary.sort_values('Invoice Count', ascending=False)
                code_summary.to_excel(writer, sheet_name='Activity Code Summary', index=False)
                print(f"   ✓ Exported summary for {len(code_summary)} activity codes")

                # Tab 6: Top Suppliers Analysis
                print("\n📊 Tab 6: Top Suppliers...")
                supplier_summary = df_all.groupby('Supplier').agg({
                    'Activity Code': lambda x: x.notna().sum(),  # Count classified
                    'Confidence': 'mean',
                    'Method': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'N/A'
                }).reset_index()
                supplier_summary.columns = ['Supplier', 'Classified Count', 'Avg Confidence', 'Primary Method']

                # Add total invoice count
                total_counts = df_all['Supplier'].value_counts().to_dict()
                supplier_summary['Total Invoices'] = supplier_summary['Supplier'].map(total_counts)
                supplier_summary['Classification Rate %'] = (supplier_summary['Classified Count'] /
                                                              supplier_summary['Total Invoices'] * 100).round(1)

                # Add primary activity code
                def get_primary_code(supplier):
                    codes = df_all[df_all['Supplier'] == supplier]['Activity Code'].dropna()
                    if len(codes) > 0:
                        return codes.mode()[0] if len(codes.mode()) > 0 else codes.iloc[0]
                    return None

                supplier_summary['Primary Activity Code'] = supplier_summary['Supplier'].apply(get_primary_code)

                # Reorder and sort
                supplier_summary = supplier_summary[['Supplier', 'Total Invoices', 'Classified Count',
                                                     'Classification Rate %', 'Primary Activity Code',
                                                     'Primary Method', 'Avg Confidence']]
                supplier_summary = supplier_summary.sort_values('Total Invoices', ascending=False).head(100)
                supplier_summary.to_excel(writer, sheet_name='Top 100 Suppliers', index=False)
                print(f"   ✓ Exported top 100 suppliers")

                # Tab 7: Unclassified Invoices
                print("\n📊 Tab 7: Unclassified Invoices...")
                df_unclassified = df_all[df_all['Activity Code'].isna()].copy()

                # Add frequency column
                supplier_freq = df_unclassified['Supplier'].value_counts().to_dict()
                df_unclassified['Supplier Frequency'] = df_unclassified['Supplier'].map(supplier_freq)

                df_unclassified = df_unclassified.sort_values('Supplier Frequency', ascending=False)
                df_unclassified.to_excel(writer, sheet_name='Unclassified', index=False)
                print(f"   ✓ Exported {len(df_unclassified)} unclassified invoices")

                # Tab 8: Executive Summary
                print("\n📊 Tab 8: Executive Summary...")
                summary_stats = [
                    {'Metric': 'Total Invoices', 'Value': len(df_all), 'Notes': ''},
                    {'Metric': 'Classified Invoices', 'Value': len(df_classified),
                     'Notes': f'{len(df_classified)/len(df_all)*100:.1f}% of total'},
                    {'Metric': 'Unclassified Invoices', 'Value': len(df_unclassified),
                     'Notes': f'{len(df_unclassified)/len(df_all)*100:.1f}% of total'},
                    {'Metric': 'Unique Suppliers', 'Value': df_all['Supplier'].nunique(), 'Notes': ''},
                    {'Metric': 'Unique Activity Codes', 'Value': df_classified['Activity Code'].nunique(), 'Notes': ''},
                    {'Metric': 'Average Confidence', 'Value': f"{df_classified['Confidence'].mean():.1f}%", 'Notes': ''},
                    {'Metric': '', 'Value': '', 'Notes': ''},
                    {'Metric': 'Classification Methods:', 'Value': '', 'Notes': ''},
                ]

                for _, row in df_methods.iterrows():
                    summary_stats.append({
                        'Metric': f"  • {row['Classification Method']}",
                        'Value': row['Invoice Count'],
                        'Notes': f"{row['Percentage']}% (avg conf: {row['Avg Confidence']:.1f}%)"
                    })

                df_summary = pd.DataFrame(summary_stats)
                df_summary.to_excel(writer, sheet_name='Executive Summary', index=False)
                print(f"   ✓ Created executive summary")

        else:
            print(f"\n⚠️  No results file provided or file not found: {results_file}")
            print("   Skipping classification results tabs")

    session.close()

    print("\n" + "=" * 80)
    print(f"✅ EXPORT COMPLETE: {output_file}")
    print("=" * 80)
    print("\nTabs created:")
    print("  1. Activity Codes - All codes with vendor counts")
    print("  2. Vendor Mappings - Detailed supplier-to-code mappings")
    if results_file and Path(results_file).exists():
        print("  3. All Classifications - Complete invoice classification results")
        print("  4. Classification Methods - Breakdown by matching engine")
        print("  5. Activity Code Summary - Invoices per code with stats")
        print("  6. Top 100 Suppliers - Supplier analysis with classification rates")
        print("  7. Unclassified - Invoices needing review")
        print("  8. Executive Summary - Key metrics and method breakdown")

    return output_file


if __name__ == '__main__':
    import glob

    # Find the most recent classification results file
    results_files = glob.glob('classification_results_*.xlsx')
    if results_files:
        # Get most recent by filename timestamp
        latest_results = sorted(results_files)[-1]
        print(f"Using latest results file: {latest_results}\n")
    else:
        latest_results = None
        print("No classification results file found\n")

    output_file = export_financial_analysis(
        db_path='classification.db',
        results_file=latest_results
    )

    print(f"\n📁 File ready for financial analysis review: {output_file}")
