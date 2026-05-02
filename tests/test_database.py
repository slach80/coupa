"""
Unit tests for database models
"""

import pytest
import os
from datetime import datetime
from classification.database import (
    Database, ActivityCode, SupplierActivityMapping,
    ClassificationHistory, ManualOverride, AdminAlert
)


@pytest.fixture
def test_db():
    """Create a test database"""
    db_path = 'test_classification.db'

    # Remove if exists
    if os.path.exists(db_path):
        os.remove(db_path)

    db = Database(db_path)
    db.create_tables()

    yield db

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


class TestDatabase:
    """Test database schema and operations"""

    def test_create_tables(self, test_db):
        """Test that all tables are created"""
        session = test_db.get_session()

        # Check tables exist
        from sqlalchemy import inspect
        inspector = inspect(test_db.engine)
        tables = inspector.get_table_names()

        assert 'activity_codes' in tables
        assert 'supplier_activity_mappings' in tables
        assert 'classification_history' in tables
        assert 'manual_overrides' in tables
        assert 'admin_alerts' in tables

        session.close()

    def test_activity_code_crud(self, test_db):
        """Test ActivityCode create, read, update, delete"""
        session = test_db.get_session()

        # Create
        code = ActivityCode(
            activity_code='TEST100',
            activity_description='Test Code',
            level1_type='Test',
            level2_category='Testing',
            level3_name='Unit Test',
            activity_definition='Test definition'
        )
        session.add(code)
        session.commit()

        # Read
        retrieved = session.query(ActivityCode).filter_by(activity_code='TEST100').first()
        assert retrieved is not None
        assert retrieved.activity_description == 'Test Code'
        assert retrieved.level1_type == 'Test'

        # Update
        retrieved.activity_description = 'Updated Description'
        session.commit()

        updated = session.query(ActivityCode).filter_by(activity_code='TEST100').first()
        assert updated.activity_description == 'Updated Description'

        # Delete
        session.delete(updated)
        session.commit()

        deleted = session.query(ActivityCode).filter_by(activity_code='TEST100').first()
        assert deleted is None

        session.close()

    def test_supplier_mapping_crud(self, test_db):
        """Test SupplierActivityMapping operations"""
        session = test_db.get_session()

        # Create activity code first
        code = ActivityCode(activity_code='WP100', activity_description='Test')
        session.add(code)
        session.commit()

        # Create mapping
        mapping = SupplierActivityMapping(
            supplier_name='TEST SUPPLIER INC',
            activity_code='WP100',
            confidence_score=95.0,
            source='historical',
            admin_approved=True
        )
        session.add(mapping)
        session.commit()

        # Read
        retrieved = session.query(SupplierActivityMapping).filter_by(
            supplier_name='TEST SUPPLIER INC'
        ).first()

        assert retrieved is not None
        assert retrieved.activity_code == 'WP100'
        assert retrieved.confidence_score == 95.0
        assert retrieved.admin_approved is True
        assert retrieved.created_at is not None

        session.close()

    def test_classification_history_relationships(self, test_db):
        """Test ClassificationHistory with relationships"""
        session = test_db.get_session()

        # Create activity code
        code = ActivityCode(activity_code='DL100', activity_description='Dev')
        session.add(code)
        session.commit()

        # Create classification
        classification = ClassificationHistory(
            invoice_id='INV-001',
            line_number=1,
            supplier='TEST SUPPLIER',
            commodity='Software',
            description='Test description',
            amount=1000.0,
            assigned_code='DL100',
            confidence=95.0,
            method='exact_match',
            needs_review=False,
            top_suggestions='[]'
        )
        session.add(classification)
        session.commit()

        # Verify relationship to activity code
        retrieved = session.query(ClassificationHistory).filter_by(
            invoice_id='INV-001'
        ).first()

        assert retrieved is not None
        assert retrieved.activity.activity_code == 'DL100'

        session.close()

    def test_manual_override(self, test_db):
        """Test ManualOverride creation"""
        session = test_db.get_session()

        # Setup
        code1 = ActivityCode(activity_code='WP100', activity_description='Test1')
        code2 = ActivityCode(activity_code='WP200', activity_description='Test2')
        session.add_all([code1, code2])
        session.commit()

        classification = ClassificationHistory(
            invoice_id='INV-002',
            line_number=1,
            supplier='SUPPLIER',
            assigned_code='WP100',
            confidence=80.0,
            method='fuzzy_match'
        )
        session.add(classification)
        session.commit()

        # Create override
        override = ManualOverride(
            classification_id=classification.id,
            original_code='WP100',
            corrected_code='WP200',
            reason='Supplier should be WP200 not WP100',
            corrected_by='admin@test.com'
        )
        session.add(override)
        session.commit()

        # Verify
        retrieved = session.query(ManualOverride).filter_by(
            classification_id=classification.id
        ).first()

        assert retrieved is not None
        assert retrieved.original_code == 'WP100'
        assert retrieved.corrected_code == 'WP200'
        assert retrieved.corrected_by == 'admin@test.com'

        session.close()

    def test_admin_alert(self, test_db):
        """Test AdminAlert creation"""
        session = test_db.get_session()

        # Setup
        code = ActivityCode(activity_code='SC500', activity_description='Facility')
        session.add(code)
        session.commit()

        classification = ClassificationHistory(
            invoice_id='INV-003',
            line_number=1,
            supplier='JAN-PRO CLEANING',
            confidence=0,
            method='non_it_detected',
            needs_review=True
        )
        session.add(classification)
        session.commit()

        # Create alert
        alert = AdminAlert(
            classification_id=classification.id,
            alert_type='non_it_vendor',
            alert_message='Non-IT vendor detected (CLEANING keyword)',
            suggested_code='SC500',
            resolved=False
        )
        session.add(alert)
        session.commit()

        # Verify
        retrieved = session.query(AdminAlert).filter_by(
            classification_id=classification.id
        ).first()

        assert retrieved is not None
        assert retrieved.alert_type == 'non_it_vendor'
        assert retrieved.resolved is False
        assert retrieved.created_at is not None

        session.close()

    def test_cascade_relationships(self, test_db):
        """Test that relationships work correctly"""
        session = test_db.get_session()

        # Create activity code
        code = ActivityCode(activity_code='IN100', activity_description='Cloud')
        session.add(code)
        session.commit()

        # Create multiple mappings for same code
        mapping1 = SupplierActivityMapping(
            supplier_name='AWS',
            activity_code='IN100',
            confidence_score=95.0
        )
        mapping2 = SupplierActivityMapping(
            supplier_name='AZURE',
            activity_code='IN100',
            confidence_score=95.0
        )
        session.add_all([mapping1, mapping2])
        session.commit()

        # Verify relationships
        activity = session.query(ActivityCode).filter_by(activity_code='IN100').first()
        assert len(activity.mappings) == 2
        assert any(m.supplier_name == 'AWS' for m in activity.mappings)
        assert any(m.supplier_name == 'AZURE' for m in activity.mappings)

        session.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
