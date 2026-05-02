"""
Stage 6: Historical Pattern Matcher
Mines human-classified data for supplier → activity code patterns
"""

import pandas as pd
from typing import Optional, Tuple, Dict
from collections import Counter


class PatternMatcher:
    """
    Matches invoices based on historical classification patterns

    Strategy:
    - Extract patterns from 2,993 human classifications
    - Single-code suppliers: Direct mapping
    - Multi-code suppliers: Use commodity/description context
    - Confidence based on frequency (10+ = 85%, 5-9 = 75%, 3-4 = 65%)
    """

    def __init__(self, patterns_file='historical_patterns.csv'):
        """Initialize with historical patterns"""
        self.patterns = {}
        self.multi_product_suppliers = {}
        self._load_patterns(patterns_file)

    def _load_patterns(self, patterns_file: str):
        """Load patterns from CSV file"""
        try:
            df = pd.read_csv(patterns_file)

            for _, row in df.iterrows():
                supplier = row['supplier'].upper().strip()
                code = row['activity_code']
                freq = row['frequency']

                # Assign confidence based on frequency
                if freq >= 10:
                    confidence = 85.0
                elif freq >= 5:
                    confidence = 75.0
                elif freq >= 3:
                    confidence = 65.0
                else:
                    continue  # Skip insufficient data

                self.patterns[supplier] = {
                    'code': code,
                    'confidence': confidence,
                    'frequency': freq
                }

            print(f"✓ Loaded {len(self.patterns)} historical patterns")

        except FileNotFoundError:
            print(f"⚠  Pattern file not found: {patterns_file}")
            print("   Run historical data analysis first")

    def load_multi_product_patterns(self, excel_file: str):
        """
        Load multi-product supplier patterns from historical data
        These suppliers need commodity/description context
        """
        try:
            # Load all sheets
            all_data = []
            for sheet in ['Auto-Assigned', 'Needs Review', 'Admin Alerts', 'No Match']:
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet)
                    all_data.append(df)
                except:
                    pass

            if not all_data:
                return

            df_all = pd.concat(all_data, ignore_index=True)
            human_classified = df_all[df_all['human_code'].notna()].copy()

            # Find multi-code suppliers
            supplier_codes = human_classified.groupby('supplier')['human_code'].apply(list).to_dict()

            for supplier, codes in supplier_codes.items():
                code_counts = Counter(codes)
                if len(code_counts) > 1:  # Multi-code supplier
                    supplier_upper = supplier.upper().strip()
                    self.multi_product_suppliers[supplier_upper] = {
                        'codes': dict(code_counts),
                        'most_common': code_counts.most_common(1)[0][0]
                    }

            if self.multi_product_suppliers:
                print(f"✓ Loaded {len(self.multi_product_suppliers)} multi-product supplier patterns")

        except Exception as e:
            print(f"⚠  Could not load multi-product patterns: {e}")

    def match(self, supplier: str, commodity: str = '', description: str = '') -> Optional[Tuple[str, float, str]]:
        """
        Match based on historical patterns

        Returns:
            Tuple of (activity_code, confidence, rationale) or None if no match
        """
        if not supplier:
            return None

        supplier_upper = supplier.upper().strip()

        # Check single-code patterns first
        if supplier_upper in self.patterns:
            pattern = self.patterns[supplier_upper]
            rationale = (f"Historical pattern: {supplier} → {pattern['code']} "
                        f"(based on {pattern['frequency']} past classifications)")
            return (pattern['code'], pattern['confidence'], rationale)

        # Check multi-product suppliers
        if supplier_upper in self.multi_product_suppliers:
            multi = self.multi_product_suppliers[supplier_upper]
            # Use most common code with reduced confidence
            code = multi['most_common']
            confidence = 60.0  # Lower confidence due to ambiguity
            rationale = (f"Multi-product supplier: {supplier} → {code} "
                        f"(most common, but context-dependent)")
            return (code, confidence, rationale)

        return None

    def get_supplier_history(self, supplier: str) -> Dict:
        """Get detailed history for a supplier"""
        supplier_upper = supplier.upper().strip()

        if supplier_upper in self.patterns:
            return {
                'type': 'single_code',
                'pattern': self.patterns[supplier_upper]
            }

        if supplier_upper in self.multi_product_suppliers:
            return {
                'type': 'multi_code',
                'pattern': self.multi_product_suppliers[supplier_upper]
            }

        return {'type': 'no_history'}


if __name__ == '__main__':
    # Test the matcher
    matcher = PatternMatcher()

    # Load multi-product patterns
    matcher.load_multi_product_patterns('classification_results_20260502_102240.xlsx')

    test_cases = [
        ('CDW DIRECT LLC', 'Computer Equipment', ''),
        ('SALESFORCE COM INC', 'Software', 'CRM licenses'),
        ('COMCAST', 'Internet (73505)', 'Business internet'),
        ('UNKNOWN SUPPLIER INC', 'Consulting', ''),
    ]

    print("\n" + "=" * 80)
    print("PATTERN MATCHER TEST")
    print("=" * 80)

    for supplier, commodity, description in test_cases:
        result = matcher.match(supplier, commodity, description)

        print(f"\nSupplier: {supplier}")
        print(f"Commodity: {commodity}")

        if result:
            code, confidence, rationale = result
            print(f"  → {code} ({confidence:.1f}%)")
            print(f"  {rationale}")
        else:
            print(f"  → No historical pattern")

        # Show history
        history = matcher.get_supplier_history(supplier)
        if history['type'] != 'no_history':
            print(f"  History: {history}")

    print("\n" + "=" * 80)
