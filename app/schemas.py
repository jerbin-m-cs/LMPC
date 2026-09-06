from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# Auth schemas
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Scan schemas - include ALL fields
class ScanResponse(BaseModel):
    id: int
    image_filename: str
    mrp: Optional[str] = None
    net_quantity: Optional[str] = None
    mfg_date: Optional[str] = None
    exp_date: Optional[str] = None
    consumer_care: Optional[str] = None
    manufacturer: Optional[str] = None  # <-- ADD THIS
    country_of_origin: Optional[str] = None  # <-- ADD THIS
    is_compliant: int
    overall_verdict: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ViolationResponse(BaseModel):
    rule_id: str
    field_name: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    severity: str
    description: str

class ScanDetailResponse(ScanResponse):
    ocr_text: Optional[str] = None
    violations: List[ViolationResponse] = []
    
    class Config:
        from_attributes = True