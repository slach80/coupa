"""
Database models for Activity Code Classification System
SQLAlchemy ORM models for the 5 core tables
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class ActivityCode(Base):
    """Master list of activity codes from Activity Codes_Active sheet"""
    __tablename__ = 'activity_codes'

    activity_code = Column(String(50), primary_key=True)
    activity_description = Column(Text)
    level1_type = Column(String(100))
    level2_category = Column(String(100))
    level3_name = Column(String(100))
    activity_definition = Column(Text)

    # Relationships
    mappings = relationship("SupplierActivityMapping", back_populates="activity")
    classifications = relationship("ClassificationHistory", back_populates="activity")


class SupplierActivityMapping(Base):
    """Validated supplier → activity code relationships"""
    __tablename__ = 'supplier_activity_mappings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String(255), nullable=False, index=True)
    activity_code = Column(String(50), ForeignKey('activity_codes.activity_code'), nullable=False)
    confidence_score = Column(Float, default=95.0)
    source = Column(String(50))  # 'historical', 'manual', 'learned'
    admin_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    activity = relationship("ActivityCode", back_populates="mappings")


class ClassificationHistory(Base):
    """Complete audit trail of all classifications"""
    __tablename__ = 'classification_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(100), nullable=False)
    line_number = Column(Integer)
    supplier = Column(String(255), nullable=False)
    commodity = Column(String(255))
    description = Column(Text)
    amount = Column(Float)

    # Classification result
    assigned_code = Column(String(50), ForeignKey('activity_codes.activity_code'))
    confidence = Column(Float)
    method = Column(String(50))  # 'exact_match', 'fuzzy_match', 'commodity_match', etc.
    needs_review = Column(Boolean, default=False)

    # Suggestions (stored as JSON-like string for simplicity)
    top_suggestions = Column(Text)  # JSON string of top 3 suggestions

    # Metadata
    classified_at = Column(DateTime, default=datetime.utcnow)
    classified_by = Column(String(100), default='system')

    # Relationships
    activity = relationship("ActivityCode", back_populates="classifications")
    overrides = relationship("ManualOverride", back_populates="classification")
    alerts = relationship("AdminAlert", back_populates="classification")


class ManualOverride(Base):
    """Admin corrections feed learning loop"""
    __tablename__ = 'manual_overrides'

    id = Column(Integer, primary_key=True, autoincrement=True)
    classification_id = Column(Integer, ForeignKey('classification_history.id'), nullable=False)
    original_code = Column(String(50))
    corrected_code = Column(String(50), ForeignKey('activity_codes.activity_code'), nullable=False)
    reason = Column(Text)
    corrected_by = Column(String(100), nullable=False)
    corrected_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    classification = relationship("ClassificationHistory", back_populates="overrides")


class AdminAlert(Base):
    """Non-IT vendors and high-value requiring approval"""
    __tablename__ = 'admin_alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    classification_id = Column(Integer, ForeignKey('classification_history.id'), nullable=False)
    alert_type = Column(String(50))  # 'non_it_vendor', 'high_value', 'low_confidence'
    alert_message = Column(Text)
    suggested_code = Column(String(50))
    resolved = Column(Boolean, default=False)
    resolved_by = Column(String(100))
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    classification = relationship("ClassificationHistory", back_populates="alerts")


# Database connection and session management
class Database:
    """Database connection manager"""

    def __init__(self, db_path='classification.db'):
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.Session = sessionmaker(bind=self.engine)

    def create_tables(self):
        """Create all tables if they don't exist"""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Get a new database session"""
        return self.Session()

    def drop_all_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(self.engine)


if __name__ == '__main__':
    # Test database creation
    db = Database('test_classification.db')
    db.create_tables()
    print("✓ Database schema created successfully")
    print(f"  Tables: {', '.join(Base.metadata.tables.keys())}")
