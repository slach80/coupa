"""
Stage 5: Keyword-based classification
Extracts keywords from supplier names and descriptions to classify IT spend
"""

from typing import Optional, Tuple, List


class KeywordMatcher:
    """
    Matches invoices based on keywords in supplier name or description

    Strategy:
    - Domain expertise keywords (AWS, Azure, GitHub, etc.)
    - Technology keywords (cloud, database, API, etc.)
    - Service type keywords (hosting, support, license, etc.)
    """

    def __init__(self):
        # Keyword → (activity_code, confidence, category) mappings
        self.keyword_rules = [
            # Cloud Providers (High confidence)
            ('AWS', 'IN100', 75, 'Cloud Infrastructure'),
            ('AMAZON WEB SERVICES', 'IN100', 75, 'Cloud Infrastructure'),
            ('AZURE', 'IN100', 75, 'Cloud Infrastructure'),
            ('MICROSOFT AZURE', 'IN100', 75, 'Cloud Infrastructure'),
            ('GOOGLE CLOUD', 'IN100', 75, 'Cloud Infrastructure'),
            ('GCP', 'IN100', 75, 'Cloud Infrastructure'),
            ('ORACLE CLOUD', 'IN100', 75, 'Cloud Infrastructure'),
            ('IBM CLOUD', 'IN100', 75, 'Cloud Infrastructure'),

            # Development Tools
            ('GITHUB', 'DL100', 70, 'Development Tools'),
            ('GITLAB', 'DL100', 70, 'Development Tools'),
            ('ATLASSIAN', 'DL100', 70, 'Development Tools'),
            ('JIRA', 'DL100', 70, 'Development Tools'),
            ('CONFLUENCE', 'DL100', 70, 'Development Tools'),

            # Security
            ('CROWDSTRIKE', 'DL320', 70, 'Cyber Security'),
            ('PALO ALTO', 'DL320', 70, 'Cyber Security'),
            ('OKTA', 'DL320', 70, 'Cyber Security'),
            ('QUALYS', 'DL320', 70, 'Cyber Security'),
            ('SYMANTEC', 'DL320', 70, 'Cyber Security'),
            ('MCAFEE', 'DL320', 70, 'Cyber Security'),

            # Networking
            ('CISCO', 'IN300', 70, 'Network Infrastructure'),
            ('JUNIPER', 'IN300', 70, 'Network Infrastructure'),
            ('ARUBA', 'IN300', 70, 'Network Infrastructure'),
            ('FORTINET', 'IN300', 70, 'Network Infrastructure'),

            # Client Computing
            ('DELL', 'WP100', 65, 'Client Computing'),
            ('HP INC', 'WP100', 65, 'Client Computing'),
            ('LENOVO', 'WP100', 65, 'Client Computing'),
            ('APPLE', 'WP100', 65, 'Client Computing'),
            ('CDW', 'WP100', 65, 'Client Computing'),

            # More specific generic keywords (require additional context)
            ('CLOUD SERVICES', 'IN100', 60, 'Cloud Services'),
            ('CLOUD COMPUTING', 'IN100', 60, 'Cloud Services'),
            ('WEB HOSTING', 'IN100', 60, 'Hosting Services'),
            ('MANAGED HOSTING', 'IN100', 60, 'Hosting Services'),
            ('SERVER HOSTING', 'IN100', 60, 'Infrastructure'),
            ('DATABASE HOSTING', 'IN100', 60, 'Infrastructure'),
            ('DATA STORAGE', 'IN100', 60, 'Infrastructure'),
            ('CLOUD STORAGE', 'IN100', 60, 'Infrastructure'),
            ('CLOUD BACKUP', 'IN100', 60, 'Infrastructure'),
            ('NETWORK SERVICES', 'IN300', 60, 'Networking'),
            ('NETWORK EQUIPMENT', 'IN300', 60, 'Networking'),
            ('FIREWALL', 'DL320', 60, 'Security'),
            ('ANTIVIRUS', 'DL320', 60, 'Security'),
            ('SOFTWARE LICENSE', 'WP100', 55, 'Software'),
            ('SOFTWARE SUBSCRIPTION', 'WP100', 55, 'Software'),
        ]

        # Build index for faster lookup
        self._build_index()

    def _build_index(self):
        """Build keyword index for efficient matching"""
        self.keyword_index = []
        for keyword, code, confidence, category in self.keyword_rules:
            self.keyword_index.append({
                'keyword': keyword.upper(),
                'code': code,
                'confidence': confidence,
                'category': category
            })

    def match(self, supplier: str = '', commodity: str = '', description: str = '') -> Optional[Tuple[str, float, str]]:
        """
        Match based on keywords in supplier, commodity, or description

        Returns:
            Tuple of (activity_code, confidence, rationale) or None if no match
        """
        # Handle None/NaN values and combine all text fields
        supplier = str(supplier) if supplier else ''
        commodity = str(commodity) if commodity else ''
        description = str(description) if description else ''

        text = f"{supplier} {commodity} {description}".upper()

        if not text.strip():
            return None

        # Find best matching keyword
        best_match = None
        best_confidence = 0

        for rule in self.keyword_index:
            keyword = rule['keyword']
            if keyword in text:
                confidence = rule['confidence']
                if confidence > best_confidence:
                    best_match = rule
                    best_confidence = confidence

        if best_match:
            rationale = self._build_rationale(best_match, supplier, commodity, description)
            return (best_match['code'], best_match['confidence'], rationale)

        return None

    def _build_rationale(self, match: dict, supplier: str, commodity: str, description: str) -> str:
        """Build human-readable rationale"""
        keyword = match['keyword']
        category = match['category']
        code = match['code']

        # Find where the keyword appeared (handle None/NaN values)
        locations = []
        if supplier and keyword in str(supplier).upper():
            locations.append('supplier')
        if commodity and keyword in str(commodity).upper():
            locations.append('commodity')
        if description and keyword in str(description).upper():
            locations.append('description')

        location_str = ', '.join(locations)
        return f'Keyword match: "{keyword}" ({category}) found in {location_str} → {code}'

    def get_all_matches(self, supplier: str = '', commodity: str = '', description: str = '') -> List[dict]:
        """
        Get all matching keywords (for debugging/suggestions)

        Returns:
            List of match dictionaries with code, confidence, rationale
        """
        # Handle None/NaN values
        supplier = str(supplier) if supplier else ''
        commodity = str(commodity) if commodity else ''
        description = str(description) if description else ''

        text = f"{supplier} {commodity} {description}".upper()
        matches = []

        for rule in self.keyword_index:
            keyword = rule['keyword']
            if keyword in text:
                rationale = self._build_rationale(rule, supplier, commodity, description)
                matches.append({
                    'keyword': keyword,
                    'code': rule['code'],
                    'confidence': rule['confidence'],
                    'category': rule['category'],
                    'rationale': rationale
                })

        # Sort by confidence descending
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        return matches


if __name__ == '__main__':
    # Test the matcher
    matcher = KeywordMatcher()

    test_cases = [
        ('AMAZON WEB SERVICES', 'Cloud Services', 'EC2 compute instances'),
        ('GITHUB INC', 'Software', 'Enterprise subscription'),
        ('CROWDSTRIKE INC', 'Security Software', 'EDR licenses'),
        ('CDW DIRECT LLC', 'Computer Equipment', 'Dell laptops'),
        ('RANDOM SUPPLIER INC', 'Consulting', 'Business consulting'),
    ]

    print("=" * 80)
    print("KEYWORD MATCHER TEST")
    print("=" * 80)

    for supplier, commodity, description in test_cases:
        result = matcher.match(supplier, commodity, description)
        print(f"\nSupplier: {supplier}")
        print(f"Commodity: {commodity}")
        print(f"Description: {description}")

        if result:
            code, confidence, rationale = result
            print(f"  → {code} ({confidence:.1f}%)")
            print(f"  {rationale}")
        else:
            print(f"  → No match")

        # Show all matches
        all_matches = matcher.get_all_matches(supplier, commodity, description)
        if len(all_matches) > 1:
            print(f"  Other matches found: {len(all_matches) - 1}")

    print("\n" + "=" * 80)
