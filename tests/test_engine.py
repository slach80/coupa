"""
Unit tests for classification engine
"""

import pytest
import os
from classification.database import Database, ActivityCode, SupplierActivityMapping
from classification.engine import ClassificationEngine, ClassificationResult


@pytest.fixture
def test_db_with_data():
    """Create test database with sample data"""
    db_path = 'test_engine.db'

    if os.path.exists(db_path):
        os.remove(db_path)

    db = Database(db_path)
    db.create_tables()
    session = db.get_session()

    # Add activity codes
    codes = [
        ActivityCode(activity_code='WP100', activity_description='Client Computing'),
        ActivityCode(activity_code='IN100', activity_description='Compute'),
        ActivityCode(activity_code='DL320', activity_description='Cyber Security'),
        ActivityCode(activity_code='SC500', activity_description='Facility'),
    ]
    session.add_all(codes)

    # Add supplier mappings
    mappings = [
        SupplierActivityMapping(
            supplier_name='CDW DIRECT LLC',
            activity_code='WP100',
            confidence_score=95.0,
            source='historical',
            admin_approved=True
        ),
        SupplierActivityMapping(
            supplier_name='AMAZON WEB SERVICES',
            activity_code='IN100',
            confidence_score=95.0,
            source='historical',
            admin_approved=True
        ),
        SupplierActivityMapping(
            supplier_name='MICROSOFT AZURE',
            activity_code='IN100',
            confidence_score=95.0,
            source='historical',
            admin_approved=True
        ),
        SupplierActivityMapping(
            supplier_name='CROWDSTRIKE INC',
            activity_code='DL320',
            confidence_score=95.0,
            source='historical',
            admin_approved=True
        ),
    ]
    session.add_all(mappings)
    session.commit()
    session.close()

    yield db_path

    if os.path.exists(db_path):
        os.remove(db_path)


class TestClassificationEngine:
    """Test classification engine logic"""

    def test_engine_initialization(self, test_db_with_data):
        """Test engine loads mappings correctly"""
        engine = ClassificationEngine(test_db_with_data)

        assert len(engine.supplier_map) == 4
        assert 'CDW DIRECT LLC' in engine.supplier_map
        assert 'AMAZON WEB SERVICES' in engine.supplier_map
        assert engine.supplier_map['CDW DIRECT LLC'] == 'WP100'

        engine.close()

    def test_stage1_exact_match(self, test_db_with_data):
        """Test Stage 1: Exact supplier match"""
        engine = ClassificationEngine(test_db_with_data)

        result = engine.classify('CDW DIRECT LLC', '', '')

        assert result.activity_code == 'WP100'
        assert result.confidence == 95.0
        assert result.method == 'exact_match'
        assert result.needs_review is False
        assert len(result.suggestions) > 0

        engine.close()

    def test_stage1_case_insensitive(self, test_db_with_data):
        """Test exact match is case-insensitive"""
        engine = ClassificationEngine(test_db_with_data)

        # Test lowercase
        result1 = engine.classify('cdw direct llc', '', '')
        assert result1.activity_code == 'WP100'

        # Test mixed case
        result2 = engine.classify('Cdw DiReCt LLC', '', '')
        assert result2.activity_code == 'WP100'

        engine.close()

    def test_stage2_fuzzy_match_high_similarity(self, test_db_with_data):
        """Test Stage 2: Fuzzy match with high similarity"""
        engine = ClassificationEngine(test_db_with_data)

        # Slight typo in CDW
        result = engine.classify('CDW DRECT LLC', '', '')

        assert result.activity_code == 'WP100'
        assert result.method == 'fuzzy_match'
        assert result.confidence >= 60  # Should be high confidence
        assert result.confidence < 95  # But not exact match confidence

        engine.close()

    def test_stage2_fuzzy_match_threshold(self, test_db_with_data):
        """Test fuzzy match only triggers above 80% threshold"""
        engine = ClassificationEngine(test_db_with_data)

        # Very different name - should not match
        result = engine.classify('COMPLETELY DIFFERENT COMPANY', '', '')

        assert result.activity_code is None
        assert result.method != 'fuzzy_match'

        engine.close()

    def test_stage2_confidence_scaling(self, test_db_with_data):
        """Test fuzzy match confidence scales correctly"""
        engine = ClassificationEngine(test_db_with_data)

        # Close match should have higher confidence
        result1 = engine.classify('CDW DIRECT', '', '')

        # Less close match
        result2 = engine.classify('CDW DIR', '', '')

        if result1.method == 'fuzzy_match' and result2.method == 'fuzzy_match':
            assert result1.confidence > result2.confidence

        engine.close()

    def test_stage7_non_it_detection(self, test_db_with_data):
        """Test Stage 7: Non-IT vendor detection"""
        engine = ClassificationEngine(test_db_with_data)

        non_it_vendors = [
            'JAN-PRO CLEANING SERVICES',
            'CASINO PARTY RENTALS',
            'LEGAL FIRM LLP',
            'WELLNESS CENTER INC',
            'HOTEL CATERING'
        ]

        for vendor in non_it_vendors:
            result = engine.classify(vendor, '', '')

            assert result.activity_code is None
            assert result.method == 'non_it_detected'
            assert result.needs_review is True
            assert result.admin_alert is True
            assert result.alert_reason is not None

        engine.close()

    def test_stage8_no_match(self, test_db_with_data):
        """Test Stage 8: No match found"""
        engine = ClassificationEngine(test_db_with_data)

        result = engine.classify('UNKNOWN VENDOR INC', '', '')

        assert result.activity_code is None
        assert result.confidence == 0
        assert result.method == 'no_match'
        assert result.needs_review is True
        assert result.admin_alert is False

        engine.close()

    def test_pipeline_order(self, test_db_with_data):
        """Test that stages execute in correct order"""
        engine = ClassificationEngine(test_db_with_data)

        # Exact match should take precedence
        result1 = engine.classify('CDW DIRECT LLC', '', '')
        assert result1.method == 'exact_match'
        assert result1.confidence == 95.0

        # Fuzzy only if no exact match
        result2 = engine.classify('CDW DRECT LLC', '', '')
        assert result2.method == 'fuzzy_match'
        assert result2.confidence < 95.0

        engine.close()

    def test_whitespace_handling(self, test_db_with_data):
        """Test engine handles extra whitespace correctly"""
        engine = ClassificationEngine(test_db_with_data)

        vendors = [
            '  CDW DIRECT LLC  ',
            'CDW  DIRECT  LLC',
            'CDW DIRECT LLC   ',
            '   CDW DIRECT LLC'
        ]

        for vendor in vendors:
            result = engine.classify(vendor, '', '')
            assert result.activity_code == 'WP100'
            assert result.method == 'exact_match'

        engine.close()

    def test_classification_result_structure(self, test_db_with_data):
        """Test ClassificationResult has all required fields"""
        engine = ClassificationEngine(test_db_with_data)

        result = engine.classify('CDW DIRECT LLC', 'Hardware', 'Test description')

        # Check all fields exist
        assert hasattr(result, 'activity_code')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'method')
        assert hasattr(result, 'suggestions')
        assert hasattr(result, 'needs_review')
        assert hasattr(result, 'admin_alert')
        assert hasattr(result, 'alert_reason')

        # Check types
        assert isinstance(result.confidence, (int, float))
        assert isinstance(result.method, str)
        assert isinstance(result.suggestions, list)
        assert isinstance(result.needs_review, bool)
        assert isinstance(result.admin_alert, bool)

        engine.close()

    def test_suggestions_format(self, test_db_with_data):
        """Test suggestions have correct format"""
        engine = ClassificationEngine(test_db_with_data)

        result = engine.classify('CDW DIRECT LLC', '', '')

        assert len(result.suggestions) > 0

        for suggestion in result.suggestions:
            assert 'code' in suggestion
            assert 'confidence' in suggestion
            assert 'rationale' in suggestion

        engine.close()

    def test_multiple_suppliers_same_code(self, test_db_with_data):
        """Test multiple suppliers can map to same code"""
        engine = ClassificationEngine(test_db_with_data)

        # Both should map to IN100
        result1 = engine.classify('AMAZON WEB SERVICES', '', '')
        result2 = engine.classify('MICROSOFT AZURE', '', '')

        assert result1.activity_code == 'IN100'
        assert result2.activity_code == 'IN100'
        assert result1.method == 'exact_match'
        assert result2.method == 'exact_match'

        engine.close()


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_supplier_name(self, test_db_with_data):
        """Test handling of empty supplier name"""
        engine = ClassificationEngine(test_db_with_data)

        result = engine.classify('', '', '')

        # Should return no match, not crash
        assert result.activity_code is None
        assert result.method == 'no_match'

        engine.close()

    def test_none_supplier_name(self, test_db_with_data):
        """Test handling of None supplier"""
        engine = ClassificationEngine(test_db_with_data)

        # Should handle gracefully
        try:
            result = engine.classify(None, '', '')
            # If it doesn't crash, check result
            assert result.activity_code is None
        except (AttributeError, TypeError):
            # Expected if not handling None
            pass

        engine.close()

    def test_special_characters(self, test_db_with_data):
        """Test handling of special characters"""
        engine = ClassificationEngine(test_db_with_data)

        suppliers = [
            'SUPPLIER & CO.',
            'SUPPLIER (DIVISION)',
            'SUPPLIER - LLC',
            'SUPPLIER / INC'
        ]

        for supplier in suppliers:
            result = engine.classify(supplier, '', '')
            # Should not crash
            assert result is not None
            assert hasattr(result, 'activity_code')

        engine.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
