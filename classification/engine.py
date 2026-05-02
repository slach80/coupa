"""
Classification Engine - Core classification logic
Implements the 8-stage classification pipeline
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
from rapidfuzz import fuzz
from classification.database import Database, SupplierActivityMapping, ActivityCode
from classification.matchers.commodity_matcher import CommodityMatcher
from classification.matchers.keyword_matcher import KeywordMatcher
from classification.matchers.pattern_matcher import PatternMatcher
from classification.matchers.llm_matcher import LLMMatcher


@dataclass
class ClassificationResult:
    """Result of classification attempt"""
    activity_code: Optional[str]
    confidence: float
    method: str
    suggestions: List[dict]  # Top 3 alternatives
    needs_review: bool
    admin_alert: bool = False
    alert_reason: Optional[str] = None


class ClassificationEngine:
    """
    8-Stage Classification Pipeline
    Phase 1: Stages 1-2 (exact, fuzzy)
    Phase 2: Stages 4-5 (commodity, keyword)
    Phase 3: Stage 6 (historical patterns)
    Stages 7-8 (non-IT detection, no match)
    """

    def __init__(self, db_path='classification.db', results_file=None, enable_llm=False, llm_fallback_opus=False):
        self.db = Database(db_path)
        self.session = self.db.get_session()

        # Load supplier mappings into memory for fast lookup
        self._load_mappings()

        # Initialize Phase 2 matchers
        self.commodity_matcher = CommodityMatcher()
        self.keyword_matcher = KeywordMatcher()

        # Initialize Phase 3 pattern matcher
        self.pattern_matcher = PatternMatcher()
        if results_file:
            self.pattern_matcher.load_multi_product_patterns(results_file)

        # Initialize Phase 4 LLM matcher (optional)
        self.llm_matcher = None
        if enable_llm:
            codes = self.session.query(ActivityCode).all()
            activity_codes_map = {c.activity_code: c.activity_description for c in codes}
            self.llm_matcher = LLMMatcher(
                activity_codes_map,
                provider='ollama',
                model='qwen2.5-coder:7b-32k',
                ollama_host='http://192.168.1.70:11434',
                fallback_to_opus=llm_fallback_opus
            )

        # Non-IT keywords for Stage 7
        self.non_it_keywords = [
            'CLEANING', 'JANITORIAL', 'CASINO', 'BENEFITS', 'INSURANCE',
            'LEGAL', 'LAW FIRM', 'ATTORNEY', 'WELLNESS', 'GYM', 'FITNESS',
            'CATERING', 'FOOD', 'RESTAURANT', 'HOTEL', 'TRAVEL'
        ]

    def _load_mappings(self):
        """Load supplier mappings into memory"""
        mappings = self.session.query(SupplierActivityMapping).all()
        self.supplier_map = {m.supplier_name: m.activity_code for m in mappings}
        self.fuzzy_suppliers = list(self.supplier_map.keys())

    def classify(self, supplier: str, commodity: str = '', description: str = '') -> ClassificationResult:
        """
        Classify an invoice line through the 8-stage pipeline
        Phase 1: Stages 1-2 (exact + fuzzy supplier matching)
        Phase 2: Stages 4-5 (commodity + keyword matching)
        Phase 3: Stage 6 (historical pattern matching)
        Stage 7: Non-IT detection
        Stage 8: No match
        """
        # Normalize whitespace: strip and collapse multiple spaces
        import re
        supplier_upper = re.sub(r'\s+', ' ', supplier.upper().strip())

        # Stage 1: Exact Match (from manual mappings)
        result = self._stage1_exact_match(supplier_upper)
        if result:
            return result

        # Stage 2: Fuzzy Supplier Match
        result = self._stage2_fuzzy_match(supplier_upper)
        if result:
            return result

        # Stage 6: Historical Pattern Match (Phase 3 - runs early for high confidence)
        result = self._stage6_pattern_match(supplier_upper, commodity, description)
        if result:
            return result

        # Stage 4: Commodity Match (Phase 2)
        result = self._stage4_commodity_match(commodity)
        if result:
            return result

        # Stage 5: Keyword Match (Phase 2)
        result = self._stage5_keyword_match(supplier_upper, commodity, description)
        if result:
            return result

        # Stage 7: Non-IT Vendor Detection (runs before LLM)
        result = self._stage7_non_it_detection(supplier_upper)
        if result:
            return result

        # Stage 9: LLM Classification (Phase 4 - for remaining ambiguous cases)
        if self.llm_matcher:
            result = self._stage9_llm_match(supplier_upper, commodity, description)
            if result:
                return result

        # Stage 8: No Match Found
        return self._stage8_no_match()

    def _stage1_exact_match(self, supplier: str) -> Optional[ClassificationResult]:
        """Stage 1: Exact supplier match from historical data"""
        if supplier in self.supplier_map:
            code = self.supplier_map[supplier]
            return ClassificationResult(
                activity_code=code,
                confidence=95.0,
                method='exact_match',
                suggestions=[
                    {'code': code, 'confidence': 95.0, 'rationale': f'Exact historical match: {supplier} → {code}'}
                ],
                needs_review=False
            )
        return None

    def _stage2_fuzzy_match(self, supplier: str) -> Optional[ClassificationResult]:
        """Stage 2: Fuzzy supplier match (threshold 80%)"""
        best_match = None
        best_score = 0
        best_code = None

        for known_supplier in self.fuzzy_suppliers:
            score = fuzz.ratio(supplier, known_supplier)
            if score > best_score:
                best_score = score
                best_match = known_supplier
                best_code = self.supplier_map[known_supplier]

        if best_score >= 80:
            # Scale confidence: 80-100 score → 60-90 confidence
            confidence = 60 + (best_score - 80) * 1.5

            return ClassificationResult(
                activity_code=best_code,
                confidence=confidence,
                method='fuzzy_match',
                suggestions=[
                    {
                        'code': best_code,
                        'confidence': confidence,
                        'rationale': f'Fuzzy match ({best_score}% similarity): "{supplier}" → "{best_match}" → {best_code}'
                    }
                ],
                needs_review=confidence < 70
            )
        return None

    def _stage4_commodity_match(self, commodity: str) -> Optional[ClassificationResult]:
        """Stage 4: Commodity-based classification"""
        if not commodity:
            return None

        match = self.commodity_matcher.match(commodity)
        if match:
            code, confidence = match
            rationale = self.commodity_matcher.get_rationale(commodity, code, confidence)
            return ClassificationResult(
                activity_code=code,
                confidence=confidence,
                method='commodity_match',
                suggestions=[
                    {'code': code, 'confidence': confidence, 'rationale': rationale}
                ],
                needs_review=confidence < 70
            )
        return None

    def _stage5_keyword_match(self, supplier: str, commodity: str, description: str) -> Optional[ClassificationResult]:
        """Stage 5: Keyword-based classification"""
        match = self.keyword_matcher.match(supplier, commodity, description)
        if match:
            code, confidence, rationale = match
            return ClassificationResult(
                activity_code=code,
                confidence=confidence,
                method='keyword_match',
                suggestions=[
                    {'code': code, 'confidence': confidence, 'rationale': rationale}
                ],
                needs_review=confidence < 70
            )
        return None

    def _stage6_pattern_match(self, supplier: str, commodity: str, description: str) -> Optional[ClassificationResult]:
        """Stage 6: Historical pattern matching"""
        match = self.pattern_matcher.match(supplier, commodity, description)
        if match:
            code, confidence, rationale = match
            return ClassificationResult(
                activity_code=code,
                confidence=confidence,
                method='pattern_match',
                suggestions=[
                    {'code': code, 'confidence': confidence, 'rationale': rationale}
                ],
                needs_review=confidence < 70
            )
        return None

    def _stage7_non_it_detection(self, supplier: str) -> Optional[ClassificationResult]:
        """Stage 7: Detect non-IT vendors"""
        for keyword in self.non_it_keywords:
            if keyword in supplier:
                return ClassificationResult(
                    activity_code=None,
                    confidence=0,
                    method='non_it_detected',
                    suggestions=[],
                    needs_review=True,
                    admin_alert=True,
                    alert_reason=f'Non-IT vendor detected (keyword: {keyword})'
                )
        return None

    def _stage9_llm_match(self, supplier: str, commodity: str, description: str) -> Optional[ClassificationResult]:
        """Stage 9: LLM-based classification for ambiguous cases"""
        match = self.llm_matcher.match(supplier, commodity, description)
        if match:
            code, confidence, rationale, alternatives = match

            # Handle NON_IT classification
            if code == 'NON_IT':
                return ClassificationResult(
                    activity_code=None,
                    confidence=0,
                    method='llm_non_it',
                    suggestions=[],
                    needs_review=False,  # LLM confirmed it's not IT
                    admin_alert=True,
                    alert_reason=f'LLM determined non-IT: {rationale}'
                )

            # IT classification
            return ClassificationResult(
                activity_code=code,
                confidence=confidence,
                method='llm_match',
                suggestions=[
                    {'code': code, 'confidence': confidence, 'rationale': rationale}
                ] + [
                    {'code': alt['code'], 'confidence': alt['confidence'], 'rationale': alt['rationale']}
                    for alt in alternatives[:2]
                ],
                needs_review=confidence < 70
            )
        return None

    def _stage8_no_match(self) -> ClassificationResult:
        """Stage 8: No match found"""
        return ClassificationResult(
            activity_code=None,
            confidence=0,
            method='no_match',
            suggestions=[],
            needs_review=True
        )

    def close(self):
        """Close database session"""
        self.session.close()


if __name__ == '__main__':
    # Test the engine
    engine = ClassificationEngine()

    # Test cases
    test_cases = [
        ('SALESFORCE', 'CRM Software', ''),
        ('MICROSOFT AZURE', 'Cloud Services', ''),
        ('JAN-PRO CLEANING', 'Janitorial', ''),
        ('UNKNOWN VENDOR INC', 'Unknown', '')
    ]

    print("=" * 80)
    print("CLASSIFICATION ENGINE TEST")
    print("=" * 80)

    for supplier, commodity, description in test_cases:
        result = engine.classify(supplier, commodity, description)
        print(f"\nSupplier: {supplier}")
        print(f"  Code:       {result.activity_code or 'None'}")
        print(f"  Confidence: {result.confidence:.1f}%")
        print(f"  Method:     {result.method}")
        print(f"  Review:     {'Yes' if result.needs_review else 'No'}")
        if result.admin_alert:
            print(f"  ⚠️  Alert:    {result.alert_reason}")

    engine.close()
    print("\n" + "=" * 80)
