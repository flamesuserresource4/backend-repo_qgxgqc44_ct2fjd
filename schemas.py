"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# Example schemas (retain examples):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# New schemas for site content preservation

class NavigationItem(BaseModel):
    label: str
    href: str

class SiteContent(BaseModel):
    """
    Preserves content from a source site while allowing redesigned presentation.
    Collection name: "sitecontent"
    """
    source_url: str = Field(..., description="Source site URL")
    language: Optional[str] = Field(None, description="Detected language code")
    raw_html: Optional[str] = Field(None, description="Raw HTML of the page body")
    raw_text: Optional[str] = Field(None, description="All text content flattened")
    sections: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Structured sections when available")
    navigation: Optional[List[NavigationItem]] = Field(default_factory=list, description="Top-level nav items when available")

# Add your own schemas here:
# --------------------------------------------------

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!
