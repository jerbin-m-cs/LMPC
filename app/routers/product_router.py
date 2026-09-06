from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..models import User, Product, ScannedProduct
from ..schemas import ProductResponse, ProductCreate
from ..auth import get_current_active_user

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("/save")
async def save_product(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Save scanned product to database for quick reference"""
    
    scan = db.query(ScannedProduct).filter(
        ScannedProduct.id == scan_id,
        ScannedProduct.user_id == current_user.id
    ).first()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Check if product exists
    existing = db.query(Product).filter(
        Product.product_name == scan.product_name
    ).first()
    
    if existing:
        # Update existing
        existing.mrp = scan.mrp or existing.mrp
        existing.net_quantity = scan.net_quantity or existing.net_quantity
        existing.manufacturer = scan.manufacturer or existing.manufacturer
        existing.is_compliant = scan.is_compliant
        existing.last_verified = scan.created_at
        db.commit()
        return {"message": "Product updated", "product": existing}
    
    # Create new
    product = Product(
        product_name=scan.product_name or "Unknown",
        mrp=scan.mrp,
        net_quantity=scan.net_quantity,
        manufacturer=scan.manufacturer,
        country_of_origin=scan.country_of_origin,
        is_compliant=scan.is_compliant,
        last_verified=scan.created_at
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return {"message": "Product saved", "product": product}

@router.get("/search")
async def search_products(
    query: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Search for saved products"""
    
    products = db.query(Product).filter(
        (Product.product_name.ilike(f"%{query}%")) |
        (Product.brand.ilike(f"%{query}%")) |
        (Product.manufacturer.ilike(f"%{query}%"))
    ).all()
    
    return products