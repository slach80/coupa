"""
Batch Processor - Process Excel files and generate classification reports
"""

import sys
sys.path.insert(0, '/home/slach/Projects/coupa')

import pandas as pd
from datetime import datetime
from classification.engine import ClassificationEngine
from classification.database import Database, ClassificationHistory, AdminAlert
import json


class BatchProcessor:
    """Process invoice data in batch and store results"""

    def __init__(self, db_path='classification.db', results_file=None):
        self.engine = ClassificationEngine(db_path, results_file=results_file)
        self.db = Database(db_path)
        self.session = self.db.get_session()

    def process_excel(self, file_path: str, months: list) -> pd.DataFrame:
        """
        Process invoice data from Excel file
        Returns DataFrame with classification results
        """
        print("=" * 80)
        print("BATCH CLASSIFICATION PROCESSOR")
        print("=" * 80)

        all_results = []

        for month in months:
            print(f"\n📄 Processing sheet: {month}...")

            df = pd.read_excel(file_path, sheet_name=month)
            month_results = []

            for idx, row in df.iterrows():
                supplier = row.get('Supplier', '')
                commodity = row.get('Commodity', '')
                description = row.get('Description', '')
                invoice_id = row.get('Invoice #', f'{month}_{idx}')
                line_number = row.get('Line #', idx + 1)
                amount = row.get('Total', 0.0)
                human_code = row.get('IT Activity Code', None)

                # Classify
                result = self.engine.classify(supplier, commodity, description)

                # Store in database
                classification = ClassificationHistory(
                    invoice_id=str(invoice_id),
                    line_number=int(line_number) if pd.notna(line_number) else None,
                    supplier=supplier,
                    commodity=commodity if pd.notna(commodity) else '',
                    description=description if pd.notna(description) else '',
                    amount=float(amount) if pd.notna(amount) else 0.0,
                    assigned_code=result.activity_code,
                    confidence=result.confidence,
                    method=result.method,
                    needs_review=result.needs_review,
                    top_suggestions=json.dumps(result.suggestions)
                )
                self.session.add(classification)
                self.session.flush()  # Get ID

                # Create admin alert if needed
                if result.admin_alert:
                    alert = AdminAlert(
                        classification_id=classification.id,
                        alert_type='non_it_vendor',
                        alert_message=result.alert_reason,
                        suggested_code=result.activity_code
                    )
                    self.session.add(alert)

                # Build result row
                month_results.append({
                    'invoice_id': invoice_id,
                    'month': month,
                    'line_number': line_number,
                    'supplier': supplier,
                    'commodity': commodity,
                    'amount': amount,
                    'human_code': human_code if pd.notna(human_code) else None,
                    'ai_code': result.activity_code,
                    'confidence': result.confidence,
                    'method': result.method,
                    'needs_review': result.needs_review,
                    'admin_alert': result.admin_alert,
                    'match': (result.activity_code == human_code) if pd.notna(human_code) and result.activity_code else None
                })

            self.session.commit()
            print(f"   ✓ Processed {len(month_results)} invoices")
            all_results.extend(month_results)

        return pd.DataFrame(all_results)

    def generate_report(self, results_df: pd.DataFrame) -> dict:
        """Generate summary report"""
        print("\n" + "=" * 80)
        print("CLASSIFICATION REPORT")
        print("=" * 80)

        total = len(results_df)
        auto_assigned = len(results_df[results_df['confidence'] >= 70])
        needs_review = len(results_df[(results_df['confidence'] > 0) & (results_df['confidence'] < 70)])
        no_match = len(results_df[results_df['confidence'] == 0])
        admin_alerts = len(results_df[results_df['admin_alert'] == True])

        # Accuracy (where human code exists)
        has_human = results_df[results_df['human_code'].notna()]
        if len(has_human) > 0:
            matches = has_human[has_human['match'] == True]
            accuracy = len(matches) / len(has_human) * 100
        else:
            accuracy = 0

        report = {
            'total_invoices': total,
            'auto_assigned': auto_assigned,
            'auto_assign_rate': (auto_assigned / total * 100) if total > 0 else 0,
            'needs_review': needs_review,
            'no_match': no_match,
            'admin_alerts': admin_alerts,
            'accuracy_vs_human': accuracy,
            'human_baseline_count': len(has_human)
        }

        print(f"\n   Total Invoices:        {total:,}")
        print(f"   Auto-Assigned (≥70%):  {auto_assigned:,} ({report['auto_assign_rate']:.1f}%)")
        print(f"   Needs Review:          {needs_review:,}")
        print(f"   No Match:              {no_match:,}")
        print(f"   Admin Alerts:          {admin_alerts:,}")
        print(f"\n   Human Baseline:        {len(has_human):,} invoices")
        print(f"   Accuracy vs Human:     {accuracy:.1f}%")
        print("\n" + "=" * 80)

        return report

    def export_to_excel(self, results_df: pd.DataFrame, output_path: str):
        """Export results to Excel with multiple sheets"""
        print(f"\n📊 Exporting results to {output_path}...")

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: Auto-assigned
            auto_df = results_df[results_df['confidence'] >= 70].copy()
            auto_df.to_excel(writer, sheet_name='Auto-Assigned', index=False)

            # Sheet 2: Needs Review
            review_df = results_df[
                (results_df['confidence'] > 0) &
                (results_df['confidence'] < 70)
            ].copy()
            review_df.to_excel(writer, sheet_name='Needs Review', index=False)

            # Sheet 3: Admin Alerts
            alert_df = results_df[results_df['admin_alert'] == True].copy()
            alert_df.to_excel(writer, sheet_name='Admin Alerts', index=False)

            # Sheet 4: No Match
            no_match_df = results_df[results_df['confidence'] == 0].copy()
            no_match_df.to_excel(writer, sheet_name='No Match', index=False)

            # Sheet 5: Summary
            summary_data = {
                'Category': ['Auto-Assigned', 'Needs Review', 'Admin Alerts', 'No Match', 'Total'],
                'Count': [len(auto_df), len(review_df), len(alert_df), len(no_match_df), len(results_df)],
                'Percentage': [
                    len(auto_df) / len(results_df) * 100,
                    len(review_df) / len(results_df) * 100,
                    len(alert_df) / len(results_df) * 100,
                    len(no_match_df) / len(results_df) * 100,
                    100.0
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

        print(f"   ✓ Exported {len(results_df)} results to 5 sheets")

    def close(self):
        """Close connections"""
        self.engine.close()
        self.session.close()


if __name__ == '__main__':
    processor = BatchProcessor()

    try:
        # Process all 4 months
        results_df = processor.process_excel(
            '/home/slach/Downloads/SAMPLE.xlsx',
            ['Nov2025_Inv', 'Dec2025_Inv', 'Jan2026_Inv', 'Feb2026_Inv']
        )

        # Generate report
        report = processor.generate_report(results_df)

        # Export to Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'classification_results_{timestamp}.xlsx'
        processor.export_to_excel(results_df, output_file)

        print(f"\n✅ Batch processing complete!")
        print(f"   Results: {output_file}")
        print(f"   Database: classification.db")

    finally:
        processor.close()
