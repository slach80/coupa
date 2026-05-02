"""
Stage 4: Commodity-based classification
Maps Coupa commodity codes to IT Activity Codes based on business rules
"""

from typing import Optional, Tuple


class CommodityMatcher:
    """
    Maps commodities to activity codes based on IT-relevant patterns

    Strategy:
    - IT-specific commodities (73000-73999) → map to specific codes
    - Consulting (72505, 73050) → Development/Project codes
    - General supplies/services → exclude (non-IT)
    """

    def __init__(self):
        # Direct commodity → activity code mappings
        # IT Commodities
        self.commodity_map = {
            # IT General (73000-73099)
            'IT - General - Operating (73000)': 'IN100',        # Infrastructure Default
            'IT - Corporate Services Operating (73027)': 'IN100', # Infrastructure Default
            'IT Consulting - General (73050)': 'DL100',          # Development Default

            # Internet & Telecom (73500-73510)
            'Internet (73505)': 'IN300',                         # Network
            'Telephone - Operating (73500)': 'IN300',            # Network
            # NOTE: Utilities (73510) removed - catches electric/water, not IT

            # Software related (73100-73199)
            'Software (73100)': 'WP100',                         # Client Computing Default
            'Software Licenses (73105)': 'WP100',                # Client Computing Default
            'Software Maintenance (73110)': 'WP100',             # Client Computing Default

            # Hardware (73200-73299)
            'Computer Hardware (73200)': 'WP100',                # Client Computing Default
            'Computer Equipment (73205)': 'WP100',               # Client Computing Default

            # Cloud Services (73300-73399)
            'Cloud Services (73300)': 'IN100',                   # Infrastructure Default
            'Hosting Services (73305)': 'IN100',                 # Infrastructure Default

            # Security (73400-73499)
            'Security Software (73400)': 'DL320',                # Cyber Security
            'Security Services (73405)': 'DL320',                # Cyber Security

            # NOTE: Consulting (72505) removed - too generic, needs supplier context

            # === NON-IT COMMODITIES → SC (Shared & Corporate) CODES ===

            # Legal & Compliance
            'Legal (72005)': 'SC400',                                # Legal Default
            'State Corp/License Fees (78020)': 'SC400',             # Legal Default

            # Facilities
            'Facilities Base Rent & Leases (77000)': 'SC500',       # Property & Facility
            'Repairs & Maintenance (77500)': 'SC500',               # Property & Facility
            'Property Taxes (78040)': 'SC500',                      # Property & Facility
            'Utilities (73510)': 'SC500',                           # Property & Facility (electric/water)

            # Office Supplies & Admin
            'Supplies (75000)': 'SC700',                            # Vendor & Procurement
            'Office - Operating (75005)': 'SC700',                  # Vendor & Procurement
            'Printing - Operating (75500)': 'SC700',                # Vendor & Procurement
            'Printing - Sales (65500)': 'SC700',                    # Vendor & Procurement
            'Postage - Operating (76000)': 'SC700',                 # Vendor & Procurement
            'Shipping - Operating (76010)': 'SC700',                # Vendor & Procurement
            'Dues & Subscriptions - Operating (75010)': 'SC700',    # Vendor & Procurement

            # HR & Staffing
            'Temporary Labor (72500)': 'SC800',                     # Workforce

            # Marketing & Sales
            'Advertising & Marketing (62000)': 'BS320',             # Other Sales & Marketing Exp
            'Leads - External (63000)': 'BS320',                    # Other Sales & Marketing Exp
            'Television/Radio Advertising (63014)': 'BS320',        # Other Sales & Marketing Exp
            'Newspaper Advertising (63022)': 'BS320',               # Other Sales & Marketing Exp
            'Agent Marketing Reimburements (63052)': 'BS320',       # Other Sales & Marketing Exp

            # Events & Travel
            'Prepaid Trips/Events/Conferences (14041)': 'SC800',    # Workforce
            'Seminars - Sales (62500)': 'BS320',                    # Other Sales & Marketing Exp
            'Seminars, Mtgs & Co Functions - Operating (78515)': 'SC800',  # Workforce
            'Meals & Entertainment - Sales (68505)': 'BS320',       # Other Sales & Marketing Exp

            # Finance
            'Commissions (51000)': 'BS320',                         # Other Sales & Marketing Exp
            'Incentive Commission Expense (59020)': 'BS320',        # Other Sales & Marketing Exp
            'Bonus Commission Expense (59030)': 'SC800',            # Workforce

            # Consulting & Services (context-dependent, map to procurement)
            'Contract Services (72510)': 'SC700',                   # Vendor & Procurement
            'Administrative Fees (72010)': 'SC700',                 # Vendor & Procurement
            'Consulting (72505)': 'SC700',                          # Vendor & Procurement (generic)

            # Equipment & Vehicles
            'Equipment Rent & Leases (76500)': 'SC700',             # Vendor & Procurement
            'Auto - Sales (68510)': 'SC700',                        # Vendor & Procurement
            'Auto - Operating (68500)': 'SC700',                    # Vendor & Procurement
            'Uniforms (75015)': 'SC700',                            # Vendor & Procurement

            # Additional Workforce/Training
            'Training - Sales (67010)': 'SC800',                    # Workforce
            'Recruiting Advertising (65000)': 'SC800',              # Workforce

            # Additional Events
            'Seminars, Mtgs & Co Functions - Sales (68515)': 'BS320',  # Sales & Marketing
            'Meals & Entertainment - Operating (78505)': 'SC800',   # Workforce
            'Travel/Airfare - Sales (68500)': 'BS320',              # Sales & Marketing

            # Additional Finance
            'Final Expense (51005)': 'BS320',                       # Sales & Marketing
            'Licensing - Sales (67000)': 'BS320',                   # Sales & Marketing
            'Dues & Subscriptions - Annual Subscriptions (14045)': 'SC700',  # Procurement

            # Other
            'Other Fees - Operating (78025)': 'SC700',              # Vendor & Procurement
            'Chargeback Other FY Actual (46170)': 'SC230',          # Finance - General Accounting
            'Chargeback Life F4 Actual (46110)': 'SC230',           # Finance - General Accounting
        }

        # Keyword patterns in commodity names
        self.keyword_patterns = [
            ('SOFTWARE', 'WP100'),
            ('HARDWARE', 'WP100'),
            ('COMPUTER', 'WP100'),
            ('CLOUD', 'IN100'),
            ('HOSTING', 'IN100'),
            ('SERVER', 'IN100'),
            ('NETWORK', 'IN300'),
            ('INTERNET', 'IN300'),
            ('TELECOM', 'IN300'),
            ('SECURITY', 'DL320'),
            ('CYBERSECURITY', 'DL320'),
            ('FIREWALL', 'DL320'),
            ('DATABASE', 'IN100'),
            ('STORAGE', 'IN100'),
        ]

    def match(self, commodity: str) -> Optional[Tuple[str, float]]:
        """
        Match commodity to activity code

        Returns:
            Tuple of (activity_code, confidence) or None if no match
        """
        if not commodity or not isinstance(commodity, str):
            return None

        commodity_clean = commodity.strip()
        commodity_upper = commodity_clean.upper()

        # Try exact match first
        if commodity_clean in self.commodity_map:
            # Boost confidence for direct commodity mappings to 75%
            # (these are explicit Coupa commodity codes, highly reliable)
            return (self.commodity_map[commodity_clean], 75.0)

        # Try keyword matching
        for keyword, code in self.keyword_patterns:
            if keyword in commodity_upper:
                return (code, 60.0)

        return None

    def get_rationale(self, commodity: str, code: str, confidence: float) -> str:
        """Generate human-readable rationale for the match"""
        commodity_clean = commodity.strip()

        # Check if exact match
        if commodity_clean in self.commodity_map:
            return f'Commodity match: "{commodity}" → {code}'

        # Find which keyword triggered
        commodity_upper = commodity_clean.upper()
        for keyword, pattern_code in self.keyword_patterns:
            if keyword in commodity_upper and pattern_code == code:
                return f'Commodity keyword match: "{commodity}" contains "{keyword}" → {code}'

        return f'Commodity match: "{commodity}" → {code}'


if __name__ == '__main__':
    # Test the matcher
    matcher = CommodityMatcher()

    test_cases = [
        'IT - General - Operating (73000)',
        'Software (73100)',
        'Internet (73505)',
        'Cloud Services (73300)',
        'Security Software (73400)',
        'Consulting (72505)',
        'Office - Operating (75005)',  # Should not match
        'Advertising & Marketing (62000)',  # Should not match
    ]

    print("=" * 80)
    print("COMMODITY MATCHER TEST")
    print("=" * 80)

    for commodity in test_cases:
        result = matcher.match(commodity)
        if result:
            code, confidence = result
            rationale = matcher.get_rationale(commodity, code, confidence)
            print(f"\n✓ {commodity}")
            print(f"  → {code} ({confidence:.1f}%)")
            print(f"  {rationale}")
        else:
            print(f"\n✗ {commodity}")
            print(f"  → No match")

    print("\n" + "=" * 80)
