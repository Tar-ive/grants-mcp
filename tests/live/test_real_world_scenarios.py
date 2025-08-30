"""Live API tests with real-world grant search scenarios and comprehensive validation."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from mcp_server.tools.utils.api_client import SimplerGrantsAPIClient
from mcp_server.models.grants_schemas import GrantsAPIResponse, OpportunityV1


class TestRealWorldGrantSearches:
    """Test real-world grant search scenarios with live API."""
    
    @pytest.mark.real_api
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_ai_research_grants(self, real_api_client):
        """Search for AI research grants with comprehensive validation."""
        
        query = "artificial intelligence machine learning"
        response = await real_api_client.search_opportunities(
            query=query,
            filters={
                "opportunity_status": ["posted", "forecasted"],
                "category": ["Science and Technology", "Research and Development"]
            },
            pagination={"page_size": 10, "page_offset": 1}
        )
        
        # Validate response structure
        assert "data" in response
        assert "pagination_info" in response
        assert isinstance(response["data"], list)
        
        # If grants found, validate their structure
        if response["data"]:
            for grant in response["data"]:
                # Validate required fields
                assert "opportunity_id" in grant
                assert "opportunity_title" in grant
                assert "agency" in grant
                
                # Check AI relevance in title or description
                title = grant.get("opportunity_title", "").lower()
                summary = grant.get("summary", {})
                description = summary.get("summary_description", "").lower()
                
                ai_keywords = ["artificial intelligence", "machine learning", "ai", "ml", "neural", "deep learning"]
                has_ai_keyword = any(keyword in title or keyword in description for keyword in ai_keywords)
                
                # Log findings for analysis
                print(f"AI Grant Found: {grant.get('opportunity_title')}")
                print(f"Agency: {grant.get('agency_name')}")
                print(f"AI Keywords Present: {has_ai_keyword}")
                
    @pytest.mark.real_api
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_climate_change_grants(self, real_api_client):
        """Search for climate change and environmental grants."""
        
        query = "climate change environmental sustainability"
        response = await real_api_client.search_opportunities(
            query=query,
            filters={
                "opportunity_status": ["posted"],
                "category": ["Environment", "Science"]
            },
            pagination={"page_size": 15, "page_offset": 1}
        )
        
        assert "data" in response
        total_records = response.get("pagination_info", {}).get("total_records", 0)
        
        print(f"Climate grants found: {total_records}")
        
        if response["data"]:
            # Analyze funding amounts for climate grants
            funding_amounts = []
            for grant in response["data"]:
                summary = grant.get("summary", {})
                ceiling = summary.get("award_ceiling")
                if ceiling:
                    funding_amounts.append(ceiling)
                    
                print(f"Climate Grant: {grant.get('opportunity_title')}")
                print(f"Award Ceiling: ${ceiling:,}" if ceiling else "Award Ceiling: Not specified")
                print(f"Agency: {grant.get('agency_name')}")
                print("---")
            
            if funding_amounts:
                avg_funding = sum(funding_amounts) / len(funding_amounts)
                max_funding = max(funding_amounts)
                print(f"Average funding: ${avg_funding:,.0f}")
                print(f"Maximum funding: ${max_funding:,}")
                
    @pytest.mark.real_api
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_healthcare_innovation_grants(self, real_api_client):
        """Search for healthcare and medical innovation grants."""
        
        queries = [
            "healthcare innovation medical technology",
            "biomedical research drug development",
            "health disparities community health"
        ]
        
        all_results = []
        
        for query in queries:
            response = await real_api_client.search_opportunities(
                query=query,
                filters={"opportunity_status": ["posted", "forecasted"]},
                pagination={"page_size": 10, "page_offset": 1}
            )
            
            all_results.extend(response.get("data", []))
            
            # Add delay between requests to respect rate limits
            await asyncio.sleep(1)
            
        print(f"Total healthcare grants found: {len(all_results)}")
        
        # Analyze agencies funding healthcare research
        agencies = {}
        for grant in all_results:
            agency = grant.get("agency_name", "Unknown")
            if agency in agencies:
                agencies[agency] += 1
            else:
                agencies[agency] = 1
                
        print("Top healthcare funding agencies:")
        for agency, count in sorted(agencies.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {agency}: {count} grants")
            
    @pytest.mark.real_api
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_education_research_grants(self, real_api_client):
        """Search for education and STEM education grants."""
        
        query = "education STEM learning curriculum"
        response = await real_api_client.search_opportunities(
            query=query,
            filters={
                "opportunity_status": ["posted"],
                "category": ["Education"]
            },
            pagination={"page_size": 20, "page_offset": 1}
        )
        
        assert "data" in response
        education_grants = response.get("data", [])
        
        print(f"Education grants found: {len(education_grants)}")
        
        # Analyze education focus areas
        focus_areas = {
            "K-12": 0,
            "Higher Education": 0, 
            "STEM": 0,
            "Teacher Training": 0,
            "Curriculum": 0
        }
        
        for grant in education_grants:
            title = grant.get("opportunity_title", "").lower()
            description = grant.get("summary", {}).get("summary_description", "").lower()
            text = f"{title} {description}"
            
            if any(term in text for term in ["k-12", "k12", "elementary", "secondary", "grade"]):
                focus_areas["K-12"] += 1
            if any(term in text for term in ["university", "college", "higher education", "undergraduate", "graduate"]):
                focus_areas["Higher Education"] += 1
            if any(term in text for term in ["stem", "science", "technology", "engineering", "mathematics"]):
                focus_areas["STEM"] += 1
            if any(term in text for term in ["teacher", "educator", "faculty", "instructor"]):
                focus_areas["Teacher Training"] += 1
            if any(term in text for term in ["curriculum", "pedagogy", "learning", "instruction"]):
                focus_areas["Curriculum"] += 1
                
        print("Education grant focus areas:")
        for area, count in focus_areas.items():
            if count > 0:
                print(f"  {area}: {count} grants")


class TestGrantAnalyticsScenarios:
    """Test analytics and trend analysis with real data."""
    
    @pytest.mark.real_api
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_funding_trends_analysis(self, real_api_client):
        """Analyze funding trends across different agencies."""
        
        # Get recent grants from multiple agencies
        target_agencies = ["NSF", "NIH", "DOE", "NASA", "EPA"]
        agency_data = {}
        
        for agency in target_agencies:
            try:
                response = await real_api_client.search_opportunities(
                    query="",  # Empty query to get all recent grants
                    filters={
                        "agency": [agency],
                        "opportunity_status": ["posted"]
                    },
                    pagination={"page_size": 25, "page_offset": 1}
                )
                
                grants = response.get("data", [])
                agency_data[agency] = {
                    "count": len(grants),
                    "grants": grants,
                    "total_funding": 0,
                    "avg_award": 0,
                    "categories": {}
                }
                
                # Calculate funding statistics
                funding_amounts = []
                for grant in grants:
                    summary = grant.get("summary", {})
                    ceiling = summary.get("award_ceiling")
                    if ceiling:
                        funding_amounts.append(ceiling)
                        agency_data[agency]["total_funding"] += ceiling
                        
                    # Track categories
                    category = grant.get("category", "Other")
                    if category in agency_data[agency]["categories"]:
                        agency_data[agency]["categories"][category] += 1
                    else:
                        agency_data[agency]["categories"][category] = 1
                
                if funding_amounts:
                    agency_data[agency]["avg_award"] = sum(funding_amounts) / len(funding_amounts)
                
                # Rate limit respect
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Error fetching data for {agency}: {e}")
                agency_data[agency] = {"count": 0, "error": str(e)}
        
        # Generate trend analysis report
        print("FUNDING TRENDS ANALYSIS")
        print("=" * 50)
        
        for agency, data in agency_data.items():
            if data.get("count", 0) > 0:
                print(f"\n{agency}:")
                print(f"  Active Grants: {data['count']}")
                print(f"  Total Funding: ${data['total_funding']:,}")
                print(f"  Average Award: ${data.get('avg_award', 0):,.0f}")
                
                # Top categories
                top_categories = sorted(
                    data['categories'].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:3]
                
                print(f"  Top Categories:")
                for cat, count in top_categories:
                    print(f"    {cat}: {count} grants")
            else:
                print(f"\n{agency}: No data available")
                if "error" in data:
                    print(f"  Error: {data['error']}")
                    
    @pytest.mark.real_api
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_deadline_urgency_analysis(self, real_api_client):
        """Analyze grant deadlines to identify urgent opportunities."""
        
        response = await real_api_client.search_opportunities(
            query="",
            filters={"opportunity_status": ["posted"]},
            pagination={"page_size": 50, "page_offset": 1}
        )
        
        grants = response.get("data", [])
        now = datetime.now()
        
        deadline_analysis = {
            "urgent": [],      # < 30 days
            "soon": [],        # 30-60 days  
            "moderate": [],    # 60-90 days
            "future": [],      # > 90 days
            "no_deadline": []  # No close date
        }
        
        for grant in grants:
            summary = grant.get("summary", {})
            close_date_str = summary.get("close_date")
            
            if not close_date_str:
                deadline_analysis["no_deadline"].append(grant)
                continue
                
            try:
                # Parse close date (assuming YYYY-MM-DD format)
                close_date = datetime.strptime(close_date_str.split('T')[0], "%Y-%m-%d")
                days_until_close = (close_date - now).days
                
                grant_info = {
                    "title": grant.get("opportunity_title", ""),
                    "agency": grant.get("agency_name", ""),
                    "close_date": close_date_str,
                    "days_remaining": days_until_close,
                    "funding": summary.get("award_ceiling", 0)
                }
                
                if days_until_close < 0:
                    continue  # Skip expired grants
                elif days_until_close <= 30:
                    deadline_analysis["urgent"].append(grant_info)
                elif days_until_close <= 60:
                    deadline_analysis["soon"].append(grant_info)
                elif days_until_close <= 90:
                    deadline_analysis["moderate"].append(grant_info)
                else:
                    deadline_analysis["future"].append(grant_info)
                    
            except ValueError:
                # Invalid date format
                deadline_analysis["no_deadline"].append(grant)
        
        # Generate deadline urgency report
        print("GRANT DEADLINE URGENCY ANALYSIS")
        print("=" * 50)
        
        categories = [
            ("URGENT (< 30 days)", "urgent"),
            ("SOON (30-60 days)", "soon"), 
            ("MODERATE (60-90 days)", "moderate"),
            ("FUTURE (> 90 days)", "future")
        ]
        
        for label, key in categories:
            grants_in_category = deadline_analysis[key]
            print(f"\n{label}: {len(grants_in_category)} grants")
            
            if grants_in_category:
                # Sort by deadline urgency
                sorted_grants = sorted(grants_in_category, key=lambda x: x["days_remaining"])
                
                for grant in sorted_grants[:5]:  # Show top 5
                    print(f"  • {grant['title'][:60]}...")
                    print(f"    {grant['agency']} | {grant['days_remaining']} days | ${grant['funding']:,}")
        
        print(f"\nGrants without deadlines: {len(deadline_analysis['no_deadline'])}")
        
    @pytest.mark.real_api
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_competitive_landscape_analysis(self, real_api_client):
        """Analyze the competitive landscape for specific research areas."""
        
        research_areas = [
            ("Quantum Computing", "quantum computing quantum information"),
            ("Renewable Energy", "renewable energy solar wind biomass"),
            ("Cancer Research", "cancer oncology tumor malignancy"),
            ("Cybersecurity", "cybersecurity information security cyber")
        ]
        
        competitive_analysis = {}
        
        for area_name, query in research_areas:
            try:
                response = await real_api_client.search_opportunities(
                    query=query,
                    filters={"opportunity_status": ["posted", "forecasted"]},
                    pagination={"page_size": 30, "page_offset": 1}
                )
                
                grants = response.get("data", [])
                
                # Calculate competitiveness metrics
                total_funding = 0
                award_amounts = []
                agencies = set()
                
                for grant in grants:
                    summary = grant.get("summary", {})
                    
                    # Track funding
                    ceiling = summary.get("award_ceiling")
                    if ceiling:
                        award_amounts.append(ceiling)
                        total_funding += ceiling
                        
                    # Track agencies
                    agency = grant.get("agency_name")
                    if agency:
                        agencies.add(agency)
                
                competitive_analysis[area_name] = {
                    "opportunity_count": len(grants),
                    "total_funding": total_funding,
                    "avg_award": sum(award_amounts) / len(award_amounts) if award_amounts else 0,
                    "max_award": max(award_amounts) if award_amounts else 0,
                    "min_award": min(award_amounts) if award_amounts else 0,
                    "funding_agencies": len(agencies),
                    "competitiveness_score": len(grants) * len(agencies) if grants and agencies else 0
                }
                
                await asyncio.sleep(2)  # Rate limiting
                
            except Exception as e:
                print(f"Error analyzing {area_name}: {e}")
                competitive_analysis[area_name] = {"error": str(e)}
        
        # Generate competitive landscape report
        print("COMPETITIVE LANDSCAPE ANALYSIS")
        print("=" * 50)
        
        # Sort areas by competitiveness score
        sorted_areas = sorted(
            [(k, v) for k, v in competitive_analysis.items() if "error" not in v],
            key=lambda x: x[1].get("competitiveness_score", 0),
            reverse=True
        )
        
        for area_name, metrics in sorted_areas:
            print(f"\n{area_name}:")
            print(f"  Opportunities Available: {metrics['opportunity_count']}")
            print(f"  Total Funding Pool: ${metrics['total_funding']:,}")
            print(f"  Average Award: ${metrics['avg_award']:,.0f}")
            print(f"  Funding Range: ${metrics['min_award']:,} - ${metrics['max_award']:,}")
            print(f"  Active Agencies: {metrics['funding_agencies']}")
            print(f"  Competitiveness Score: {metrics['competitiveness_score']}")
            
            # Interpretation
            score = metrics['competitiveness_score']
            if score > 100:
                print(f"  Assessment: HIGHLY COMPETITIVE - Many opportunities and agencies")
            elif score > 50:
                print(f"  Assessment: MODERATELY COMPETITIVE - Good opportunities available")
            elif score > 20:
                print(f"  Assessment: LIMITED COMPETITION - Fewer opportunities")
            else:
                print(f"  Assessment: LOW COMPETITION - Niche area or limited funding")


class TestDataQualityValidation:
    """Test data quality and consistency with real API responses."""
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    async def test_data_completeness_audit(self, real_api_client):
        """Audit data completeness across different grant types."""
        
        response = await real_api_client.search_opportunities(
            query="",
            pagination={"page_size": 100, "page_offset": 1}
        )
        
        grants = response.get("data", [])
        
        completeness_metrics = {
            "total_grants": len(grants),
            "fields": {}
        }
        
        # Define critical fields to audit
        critical_fields = [
            "opportunity_id", "opportunity_title", "agency_name", 
            "opportunity_status", "category"
        ]
        
        summary_fields = [
            "award_ceiling", "award_floor", "close_date", "post_date",
            "summary_description", "applicant_eligibility_description"
        ]
        
        # Audit critical fields
        for field in critical_fields:
            missing_count = 0
            empty_count = 0
            
            for grant in grants:
                value = grant.get(field)
                if value is None:
                    missing_count += 1
                elif isinstance(value, str) and value.strip() == "":
                    empty_count += 1
                    
            completeness_metrics["fields"][field] = {
                "missing": missing_count,
                "empty": empty_count,
                "complete": len(grants) - missing_count - empty_count,
                "completion_rate": (len(grants) - missing_count - empty_count) / len(grants) if grants else 0
            }
        
        # Audit summary fields
        for field in summary_fields:
            missing_count = 0
            empty_count = 0
            
            for grant in grants:
                summary = grant.get("summary", {})
                if summary:
                    value = summary.get(field)
                    if value is None:
                        missing_count += 1
                    elif isinstance(value, str) and value.strip() == "":
                        empty_count += 1
                else:
                    missing_count += 1
                    
            completeness_metrics["fields"][f"summary.{field}"] = {
                "missing": missing_count,
                "empty": empty_count,
                "complete": len(grants) - missing_count - empty_count,
                "completion_rate": (len(grants) - missing_count - empty_count) / len(grants) if grants else 0
            }
        
        # Generate data quality report
        print("DATA QUALITY AUDIT REPORT")
        print("=" * 50)
        print(f"Total Grants Analyzed: {completeness_metrics['total_grants']}")
        print()
        
        # Sort fields by completion rate
        sorted_fields = sorted(
            completeness_metrics["fields"].items(),
            key=lambda x: x[1]["completion_rate"],
            reverse=True
        )
        
        print("Field Completeness Analysis:")
        print(f"{'Field':<35} {'Complete':<8} {'Missing':<8} {'Empty':<8} {'Rate':<8}")
        print("-" * 70)
        
        for field, metrics in sorted_fields:
            rate = metrics["completion_rate"] * 100
            print(f"{field:<35} {metrics['complete']:<8} {metrics['missing']:<8} {metrics['empty']:<8} {rate:<7.1f}%")
        
        # Identify data quality issues
        print("\nData Quality Issues:")
        low_quality_fields = [
            field for field, metrics in sorted_fields 
            if metrics["completion_rate"] < 0.8
        ]
        
        if low_quality_fields:
            for field in low_quality_fields:
                metrics = completeness_metrics["fields"][field]
                print(f"  • {field}: {metrics['completion_rate']*100:.1f}% complete")
        else:
            print("  No significant data quality issues detected")
            
    @pytest.mark.real_api
    @pytest.mark.asyncio
    async def test_api_response_consistency(self, real_api_client):
        """Test API response consistency across multiple requests."""
        
        # Make the same request multiple times
        query = "research innovation"
        responses = []
        
        for i in range(3):
            response = await real_api_client.search_opportunities(
                query=query,
                filters={"opportunity_status": ["posted"]},
                pagination={"page_size": 10, "page_offset": 1}
            )
            responses.append(response)
            await asyncio.sleep(1)  # Rate limiting
        
        # Validate consistency
        print("API RESPONSE CONSISTENCY CHECK")
        print("=" * 50)
        
        # Check pagination info consistency
        pagination_infos = [r.get("pagination_info", {}) for r in responses]
        total_records = [p.get("total_records", 0) for p in pagination_infos]
        
        print(f"Total Records Reported: {total_records}")
        
        if len(set(total_records)) == 1:
            print("✅ Pagination info is consistent")
        else:
            print("❌ Pagination info varies between requests")
            
        # Check data structure consistency
        all_consistent = True
        for i, response in enumerate(responses):
            if "data" not in response:
                print(f"❌ Response {i+1}: Missing 'data' field")
                all_consistent = False
            elif not isinstance(response["data"], list):
                print(f"❌ Response {i+1}: 'data' is not a list")
                all_consistent = False
                
            if "pagination_info" not in response:
                print(f"❌ Response {i+1}: Missing 'pagination_info' field")
                all_consistent = False
        
        if all_consistent:
            print("✅ Response structure is consistent")
            
        # Check for duplicate opportunities across requests
        all_opportunity_ids = []
        for response in responses:
            for grant in response.get("data", []):
                opp_id = grant.get("opportunity_id")
                if opp_id:
                    all_opportunity_ids.append(opp_id)
        
        unique_ids = set(all_opportunity_ids)
        print(f"Total Opportunity IDs: {len(all_opportunity_ids)}")
        print(f"Unique Opportunity IDs: {len(unique_ids)}")
        
        if len(all_opportunity_ids) == len(unique_ids):
            print("✅ No duplicate opportunities found")
        else:
            duplicates = len(all_opportunity_ids) - len(unique_ids)
            print(f"⚠️  Found {duplicates} duplicate opportunities")