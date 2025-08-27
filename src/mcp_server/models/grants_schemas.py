"""Pydantic models for Simpler Grants API responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OpportunitySummary(BaseModel):
    """Summary information for a grant opportunity."""
    
    award_ceiling: Optional[float] = None
    award_floor: Optional[float] = None
    estimated_total_program_funding: Optional[float] = None
    expected_number_of_awards: Optional[int] = None
    post_date: Optional[str] = None
    close_date: Optional[str] = None
    archive_date: Optional[str] = None
    summary_description: Optional[str] = None
    additional_info_url: Optional[str] = None
    agency_contact_description: Optional[str] = None
    agency_email_address: Optional[str] = None
    agency_phone_number: Optional[str] = None
    applicant_eligibility_description: Optional[str] = None
    applicant_types: Optional[List[str]] = None
    funding_category: Optional[str] = None
    funding_instrument: Optional[str] = None


class OpportunityV1(BaseModel):
    """Grant opportunity model matching API v1 schema."""
    
    opportunity_id: str  # Can be UUID or integer as string
    opportunity_number: str
    opportunity_title: str
    opportunity_status: str
    agency: str
    agency_code: str
    agency_name: str
    summary: OpportunitySummary
    category: Optional[str] = None
    category_explanation: Optional[str] = None
    
    model_config = {"extra": "allow"}  # Allow additional fields from API


class AgencyV1(BaseModel):
    """Agency model matching API v1 schema."""
    
    agency_code: str
    agency_name: str
    sub_agency_code: Optional[str] = None
    sub_agency_name: Optional[str] = None
    top_level_agency_name: Optional[str] = None
    
    model_config = {"extra": "allow"}


class PaginationInfo(BaseModel):
    """Pagination information from API responses."""
    
    page_size: int
    page_offset: Optional[int] = None  # Can be page_offset or page_number
    page_number: Optional[int] = None  # Can be page_offset or page_number
    total_records: int
    total_pages: Optional[int] = None
    
    model_config = {"extra": "allow"}
    
    def get_page_number(self) -> int:
        """Get the current page number."""
        return self.page_number or self.page_offset or 1


class GrantsAPIResponse(BaseModel):
    """Standard API response structure."""
    
    data: List[Dict[str, Any]]  # Can be opportunities or agencies
    pagination_info: PaginationInfo
    message: Optional[str] = None
    status_code: Optional[int] = None
    errors: Optional[List[Dict[str, Any]]] = None
    facet_counts: Optional[Dict[str, Dict[str, int]]] = None
    
    model_config = {"extra": "allow"}
    
    def get_opportunities(self) -> List[OpportunityV1]:
        """Convert data to opportunity models."""
        opportunities = []
        for item in self.data:
            try:
                opportunities.append(OpportunityV1(**item))
            except Exception as e:
                # Log but don't fail on individual item parsing errors
                print(f"Error parsing opportunity: {e}")
        return opportunities
    
    def get_agencies(self) -> List[AgencyV1]:
        """Convert data to agency models."""
        agencies = []
        for item in self.data:
            try:
                agencies.append(AgencyV1(**item))
            except Exception as e:
                # Log but don't fail on individual item parsing errors
                print(f"Error parsing agency: {e}")
        return agencies