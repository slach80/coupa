#!/usr/bin/env python3
"""
Load Activity Codes from SAMPLE.xlsx into the database
Parses Activity Codes_Active sheet and builds supplier mappings
"""

import sys
sys.path.insert(0, '/home/slach/Projects/coupa')

import pandas as pd
from classification.database import Database, ActivityCode, SupplierActivityMapping

SAMPLE_FILE = "/home/slach/Downloads/SAMPLE.xlsx"


def load_activity_codes(session):
    """Load activity codes from Activity Codes_Active sheet"""
    print("\n📥 Loading Activity Codes from SAMPLE.xlsx...")

    df = pd.read_excel(SAMPLE_FILE, sheet_name='Activity Codes_Active')

    codes_loaded = 0
    for _, row in df.iterrows():
        code = ActivityCode(
            activity_code=row['Activity Code'],
            activity_description=row.get('Activity Description', ''),
            level1_type=row.get('[L1] Type', ''),
            level2_category=row.get('[L2] Category', ''),
            level3_name=row.get('[L3] Name', ''),
            activity_definition=row.get('Activity Definition', '')
        )
        session.merge(code)  # Use merge to handle duplicates
        codes_loaded += 1

    session.commit()
    print(f"   ✓ Loaded {codes_loaded} activity codes")
    return codes_loaded


def load_supplier_mappings(session):
    """Extract and load supplier-to-code mappings"""
    print("\n📥 Extracting supplier mappings...")

    df = pd.read_excel(SAMPLE_FILE, sheet_name='Activity Codes_Active')

    mappings_loaded = 0
    for _, row in df.iterrows():
        activity_code = row['Activity Code']

        # Parse pipe-delimited supplier names
        if 'Supplier Names' in row and pd.notna(row['Supplier Names']):
            suppliers = str(row['Supplier Names']).split('|')

            for supplier_name in suppliers:
                supplier_name = supplier_name.strip()
                if supplier_name:
                    # Check if mapping already exists
                    existing = session.query(SupplierActivityMapping).filter_by(
                        supplier_name=supplier_name.upper(),
                        activity_code=activity_code
                    ).first()

                    if not existing:
                        mapping = SupplierActivityMapping(
                            supplier_name=supplier_name.upper(),
                            activity_code=activity_code,
                            confidence_score=95.0,
                            source='historical',
                            admin_approved=True
                        )
                        session.add(mapping)
                        mappings_loaded += 1

    session.commit()
    print(f"   ✓ Loaded {mappings_loaded} supplier-to-code mappings")
    return mappings_loaded


def print_summary(session):
    """Print database summary"""
    print("\n📊 Database Summary")
    print("=" * 60)

    activity_count = session.query(ActivityCode).count()
    mapping_count = session.query(SupplierActivityMapping).count()

    print(f"   Activity Codes:         {activity_count}")
    print(f"   Supplier Mappings:      {mapping_count}")

    # Show sample mappings
    print("\n   Sample Mappings:")
    samples = session.query(SupplierActivityMapping).limit(10).all()
    for mapping in samples:
        print(f"      {mapping.supplier_name:30s} → {mapping.activity_code}")

    print("=" * 60)


def main():
    # Initialize database
    db = Database('classification.db')

    print("=" * 60)
    print("ACTIVITY CODE DATA LOADER")
    print("=" * 60)

    # Create tables
    print("\n🏗️  Creating database schema...")
    db.create_tables()
    print("   ✓ Tables created")

    # Get session
    session = db.get_session()

    try:
        # Load data
        codes_count = load_activity_codes(session)
        mappings_count = load_supplier_mappings(session)

        # Print summary
        print_summary(session)

        print("\n✅ Data loading complete!")
        print(f"\n   Database: classification.db")
        print(f"   {codes_count} activity codes")
        print(f"   {mappings_count} supplier mappings")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


if __name__ == '__main__':
    main()
