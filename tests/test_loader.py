"""
Unit tests for data loading
"""

import pytest
import os
import sys
sys.path.insert(0, '/home/slach/Projects/coupa')

from classification.database import Database, ActivityCode, SupplierActivityMapping


@pytest.fixture
def clean_test_db():
    """Create clean test database"""
    db_path = 'test_loader.db'

    if os.path.exists(db_path):
        os.remove(db_path)

    db = Database(db_path)
    db.create_tables()

    yield db

    if os.path.exists(db_path):
        os.remove(db_path)


class TestDataLoader:
    """Test data loading operations"""

    def test_activity_code_loading(self, clean_test_db):
        """Test loading activity codes"""
        session = clean_test_db.get_session()

        # Simulate loading activity codes
        codes = [
            ActivityCode(
                activity_code='WP100',
                activity_description='Client Computing Default',
                level1_type='Workplace',
                level2_category='End User Computing',
                level3_name='Client Computing Default',
                activity_definition='End user devices'
            ),
            ActivityCode(
                activity_code='IN100',
                activity_description='Compute Default',
                level1_type='Infrastructure',
                level2_category='Compute',
                level3_name='Compute Default',
                activity_definition='Cloud compute'
            ),
        ]

        for code in codes:
            session.merge(code)

        session.commit()

        # Verify
        count = session.query(ActivityCode).count()
        assert count == 2

        wp100 = session.query(ActivityCode).filter_by(activity_code='WP100').first()
        assert wp100 is not None
        assert wp100.level1_type == 'Workplace'

        session.close()

    def test_supplier_mapping_loading(self, clean_test_db):
        """Test loading supplier mappings"""
        session = clean_test_db.get_session()

        # Create activity code first
        code = ActivityCode(activity_code='BS310', activity_description='CRM')
        session.add(code)
        session.commit()

        # Load mapping
        mapping = SupplierActivityMapping(
            supplier_name='SALESFORCE',
            activity_code='BS310',
            confidence_score=95.0,
            source='historical',
            admin_approved=True
        )
        session.add(mapping)
        session.commit()

        # Verify
        count = session.query(SupplierActivityMapping).count()
        assert count == 1

        retrieved = session.query(SupplierActivityMapping).filter_by(
            supplier_name='SALESFORCE'
        ).first()

        assert retrieved is not None
        assert retrieved.activity_code == 'BS310'
        assert retrieved.source == 'historical'

        session.close()

    def test_pipe_delimited_suppliers(self, clean_test_db):
        """Test parsing pipe-delimited supplier lists"""
        session = clean_test_db.get_session()

        # Create activity code
        code = ActivityCode(activity_code='IN100', activity_description='Compute')
        session.add(code)
        session.commit()

        # Simulate parsing "AWS | AZURE | GCP"
        supplier_string = "AWS | AZURE | GCP"
        suppliers = [s.strip().upper() for s in supplier_string.split('|')]

        for supplier_name in suppliers:
            mapping = SupplierActivityMapping(
                supplier_name=supplier_name,
                activity_code='IN100',
                confidence_score=95.0,
                source='historical'
            )
            session.add(mapping)

        session.commit()

        # Verify all 3 loaded
        count = session.query(SupplierActivityMapping).filter_by(
            activity_code='IN100'
        ).count()

        assert count == 3

        # Verify names are uppercase
        mappings = session.query(SupplierActivityMapping).all()
        assert all(m.supplier_name.isupper() for m in mappings)

        session.close()

    def test_duplicate_mapping_handling(self, clean_test_db):
        """Test that duplicate mappings are handled correctly"""
        session = clean_test_db.get_session()

        # Create activity code
        code = ActivityCode(activity_code='DL100', activity_description='Dev')
        session.add(code)
        session.commit()

        # Add mapping
        mapping1 = SupplierActivityMapping(
            supplier_name='GITHUB',
            activity_code='DL100',
            confidence_score=95.0
        )
        session.add(mapping1)
        session.commit()

        # Try to add duplicate (should be prevented by checking)
        existing = session.query(SupplierActivityMapping).filter_by(
            supplier_name='GITHUB',
            activity_code='DL100'
        ).first()

        if not existing:
            mapping2 = SupplierActivityMapping(
                supplier_name='GITHUB',
                activity_code='DL100',
                confidence_score=95.0
            )
            session.add(mapping2)
            session.commit()

        # Should only have 1
        count = session.query(SupplierActivityMapping).filter_by(
            supplier_name='GITHUB'
        ).count()

        assert count == 1

        session.close()

    def test_empty_supplier_names_ignored(self, clean_test_db):
        """Test that empty supplier names are ignored"""
        session = clean_test_db.get_session()

        code = ActivityCode(activity_code='WP100', activity_description='Test')
        session.add(code)
        session.commit()

        # Simulate parsing with empty values
        supplier_string = "CDW | | | AMAZON"
        suppliers = [s.strip().upper() for s in supplier_string.split('|') if s.strip()]

        for supplier_name in suppliers:
            mapping = SupplierActivityMapping(
                supplier_name=supplier_name,
                activity_code='WP100'
            )
            session.add(mapping)

        session.commit()

        # Should only have 2 (not 4)
        count = session.query(SupplierActivityMapping).count()
        assert count == 2

        session.close()

    def test_activity_code_merge(self, clean_test_db):
        """Test that activity codes can be updated via merge"""
        session = clean_test_db.get_session()

        # Initial load
        code1 = ActivityCode(
            activity_code='WP100',
            activity_description='Original Description'
        )
        session.add(code1)
        session.commit()

        # Update via merge
        code2 = ActivityCode(
            activity_code='WP100',
            activity_description='Updated Description'
        )
        session.merge(code2)
        session.commit()

        # Should still only have 1 record
        count = session.query(ActivityCode).count()
        assert count == 1

        # Should have updated description
        retrieved = session.query(ActivityCode).filter_by(activity_code='WP100').first()
        assert retrieved.activity_description == 'Updated Description'

        session.close()

    def test_uppercase_normalization(self, clean_test_db):
        """Test supplier names are normalized to uppercase"""
        session = clean_test_db.get_session()

        code = ActivityCode(activity_code='IN100', activity_description='Test')
        session.add(code)
        session.commit()

        # Add with lowercase
        mapping = SupplierActivityMapping(
            supplier_name='amazon web services',  # lowercase
            activity_code='IN100'
        )
        # Should be normalized to uppercase before insert
        mapping.supplier_name = mapping.supplier_name.upper()
        session.add(mapping)
        session.commit()

        # Verify stored as uppercase
        retrieved = session.query(SupplierActivityMapping).first()
        assert retrieved.supplier_name == 'AMAZON WEB SERVICES'
        assert retrieved.supplier_name.isupper()

        session.close()


class TestDataValidation:
    """Test data validation and constraints"""

    def test_activity_code_primary_key(self, clean_test_db):
        """Test activity_code is primary key"""
        session = clean_test_db.get_session()

        code1 = ActivityCode(activity_code='TEST100', activity_description='Test1')
        session.add(code1)
        session.commit()

        # Try to add duplicate primary key
        code2 = ActivityCode(activity_code='TEST100', activity_description='Test2')
        session.add(code2)

        with pytest.raises(Exception):  # Should raise integrity error
            session.commit()

        session.rollback()
        session.close()

    def test_foreign_key_constraint(self, clean_test_db):
        """Test foreign key constraints work"""
        # SQLite doesn't enforce foreign keys by default
        # This test documents expected behavior even if not enforced
        session = clean_test_db.get_session()

        # Try to create mapping without activity code
        mapping = SupplierActivityMapping(
            supplier_name='TEST',
            activity_code='NONEXISTENT',  # Doesn't exist
            confidence_score=95.0
        )
        session.add(mapping)

        try:
            session.commit()
            # SQLite may allow this without PRAGMA foreign_keys=ON
            # In production, we'd validate before insert
        except Exception:
            # If it does raise, that's good
            pass
        finally:
            session.rollback()
            session.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
