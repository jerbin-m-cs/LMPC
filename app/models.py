from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String, default="inspector")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    scans = relationship("ScannedProduct", back_populates="user")

class ScannedProduct(Base):
    __tablename__ = "scanned_products"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_path = Column(String)
    image_filename = Column(String)
    
    # Extracted fields
    product_name = Column(String, nullable=True)
    mrp = Column(String, nullable=True)
    net_quantity = Column(String, nullable=True)
    mfg_date = Column(String, nullable=True)
    exp_date = Column(String, nullable=True)
    consumer_care = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    country_of_origin = Column(String, nullable=True)
    
    # OCR results
    ocr_text = Column(Text, nullable=True)
    
    # Compliance results
    is_compliant = Column(Integer, default=0)
    overall_verdict = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="scans")
    violations = relationship("Violation", back_populates="product")

class Violation(Base):
    __tablename__ = "violations"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("scanned_products.id"))
    rule_id = Column(String)
    field_name = Column(String)
    expected_value = Column(String, nullable=True)
    actual_value = Column(String, nullable=True)
    severity = Column(String)
    description = Column(Text)
    
    product = relationship("ScannedProduct", back_populates="violations")