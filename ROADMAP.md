# Grants MCP Development Roadmap

## Phase 3: Advanced Analytics & Scoring System

### Planned Additional Tools

#### 1. Grant Match Scorer (`grant_match_scorer`)
**Purpose**: Answer "Which grants are actually worth my time?"

**Core Features**:
- **Technical Fit Score** (0-100): Keyword matching, category alignment, institutional focus
- **Competition Index** (NIH/NSF methodology): Application-to-award ratios with historical data
- **ROI Score** (0-100): Award amount vs effort investment analysis
- **Success Probability** (0-100): Based on eligibility matching and past success rates
- **Timing Score** (0-100): Preparation time adequacy assessment

**Mathematical Foundation**:
```python
# Competition Index (based on NIH methodology)
CI = (Total_Applications / Number_of_Awards) * 100
WCI = CI * (1 / sqrt(Award_Ceiling)) * Agency_Weight_Factor

# Success Probability Score
SPS = (Awards / Expected_Applications) * Eligibility_Score * Technical_Fit_Score

# ROI Calculation
ROI = ((Award_Amount - Application_Cost) / Application_Cost) * Success_Probability
```

#### 2. Hidden Opportunity Finder (`hidden_opportunity_finder`)
**Purpose**: Answer "What opportunities am I missing?"

**Discovery Methods**:
- **Under-subscribed Grants**: Identify grants with low application volumes
- **Emerging Funders**: Detect new funding agencies or programs
- **Cross-Category Matching**: Find grants outside typical search categories
- **Geographic Advantages**: Location-based funding preferences
- **Timing Arbitrage**: Off-cycle or unusual deadline opportunities

**Hidden Opportunity Score (HOS)**:
```python
# Novel metric for undersubscribed grants
Visibility_Index = (Search_Result_Position * Category_Popularity) / 100
Undersubscription = max(0, 100 - (Applications_Last_Year / Awards_Available) * 20)
HOS = (Undersubscription * 0.4) + ((100 - Visibility_Index) * 0.3) + (Cross_Category_Score * 0.3)
```

#### 3. Strategic Application Planner (`strategic_application_planner`)
**Purpose**: Answer "How do I maximize my win rate?"

**Planning Features**:
- **Portfolio Diversification**: Reach/match/safety grant categorization
- **Timeline Optimization**: Deadline management and workload balancing
- **Collaboration Suggestions**: Multi-PI or institutional partnerships
- **Resource Allocation**: Budget and time distribution across applications
- **Reuse Opportunities**: Leveraging existing materials and data

**Strategic Metrics**:
- **Portfolio Balance Score**: Ensures diversified risk profile
- **Timeline Feasibility**: Realistic preparation time assessment  
- **Collaboration Synergy**: Partnership opportunity scoring
- **Reuse Efficiency**: Material repurposing potential

### Implementation Architecture

```
src/mcp_server/analytics/
├── scoring_engine.py           # Main orchestrator for all scoring
├── metrics/
│   ├── competition_metrics.py  # CI calculations
│   ├── success_metrics.py      # SPS calculations  
│   ├── roi_metrics.py          # ROI calculations
│   ├── timing_metrics.py       # Timing calculations
│   └── hidden_metrics.py       # HOS calculations
├── database/
│   ├── session_manager.py      # SQLite session persistence
│   ├── score_storage.py        # Score caching and storage
│   └── analytics_cache.py      # Enhanced caching for calculations
├── transparency/
│   ├── calculation_explainer.py # Transparent score breakdowns
│   └── report_generator.py     # Formatted analysis reports
└── utils/
    ├── numpy_calculator.py     # Vectorized mathematical operations
    └── industry_constants.py   # NIH/NSF benchmark constants
```

### Tools Integration Plan

#### Current Tools (Phase 1-2) ✅
1. `opportunity_discovery` - Basic search and filtering
2. `agency_landscape` - Agency funding pattern analysis  
3. `funding_trend_scanner` - Temporal trend analysis

#### Phase 3 Tools (Planned) 🚧
4. `grant_match_scorer` - Multi-dimensional scoring system
5. `hidden_opportunity_finder` - Undersubscribed grant detection
6. `strategic_application_planner` - Portfolio optimization

### Database Schema (Phase 3)

```sql
-- Grant scoring sessions
CREATE TABLE scoring_sessions (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    search_query TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Individual grant scores
CREATE TABLE grant_scores (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    opportunity_id TEXT,
    technical_fit_score REAL,
    competition_index REAL,
    roi_score REAL,
    success_probability REAL,
    timing_score REAL,
    overall_score REAL,
    calculation_details JSON,
    FOREIGN KEY (session_id) REFERENCES scoring_sessions(id)
);

-- Strategic planning data
CREATE TABLE application_plans (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    grant_ids TEXT, -- JSON array
    portfolio_balance REAL,
    timeline_feasibility REAL,
    total_funding_potential REAL,
    recommendation_tier TEXT, -- reach/match/safety
    FOREIGN KEY (session_id) REFERENCES scoring_sessions(id)
);
```

### Transparency & Explainability

All scoring calculations will provide detailed breakdowns:

```json
{
  "grant_id": "EPA-R13-STAR-G1",
  "overall_score": 78.5,
  "scores": {
    "technical_fit": {
      "value": 85.0,
      "calculation": "keyword_match(0.9) * category_alignment(0.95) * institutional_focus(0.9)",
      "details": {
        "keyword_matches": ["renewable", "solar", "energy efficiency"],
        "category_alignment": "Environmental Technology - Perfect Match",
        "institutional_focus": "R1 Research University - High Priority"
      }
    },
    "competition_index": {
      "value": 45.2,
      "calculation": "(226 applications / 5 awards) * 100",
      "interpretation": "Moderate competition",
      "industry_benchmark": "EPA average: 35-45"
    },
    "roi_score": {
      "value": 892.0,
      "calculation": "(($500K - $15K) / $15K) * 0.72 probability",
      "components": {
        "award_amount": 500000,
        "application_cost": 15000,
        "success_probability": 0.72
      }
    }
  },
  "recommendation": "Strong Match - High Priority Application",
  "next_actions": [
    "Begin preliminary research immediately",
    "Contact program officer for guidance",
    "Identify potential collaborators"
  ]
}
```

### Performance Targets (Phase 3)

- **Grant Scoring**: <2 seconds for 10 grants, <10 seconds for 100 grants
- **Hidden Opportunities**: Discover 5-10 overlooked grants per search
- **Strategic Planning**: Generate portfolio recommendations in <5 seconds
- **Database Operations**: <100ms for score retrieval, <500ms for complex analytics
- **Cache Hit Rates**: >80% for repeated calculations

### Success Metrics

**Quantitative Goals**:
- Reduce grant search time by 70%
- Increase application success rate by 2-3x through better targeting
- Identify 15-25% more relevant opportunities via hidden opportunity detection
- Improve portfolio ROI by 40% through strategic planning

**Qualitative Goals**:
- Transparent, explainable scoring that users trust
- Intuitive strategic recommendations
- Seamless integration with existing workflow
- Actionable insights rather than just data

### Technology Stack Additions (Phase 3)

**New Dependencies**:
- `numpy` - Vectorized mathematical operations
- `sqlite3` - Session persistence and analytics storage
- `pandas` (optional) - Data manipulation for complex analytics
- `scikit-learn` (optional) - Advanced matching algorithms

**Enhanced Caching**:
- Persistent SQLite cache for expensive calculations
- NumPy array caching for vectorized operations
- Session-based caching for multi-tool workflows

### Development Priorities

1. **Phase 3.1**: Implement `grant_match_scorer` with basic scoring algorithms
2. **Phase 3.2**: Add `hidden_opportunity_finder` with undersubscription detection
3. **Phase 3.3**: Build `strategic_application_planner` with portfolio optimization
4. **Phase 3.4**: Enhanced analytics, reporting, and visualization capabilities

### Testing Strategy (Phase 3)

**Unit Tests**:
- Individual scoring algorithm accuracy
- Mathematical calculation correctness
- Edge case handling

**Integration Tests**:  
- Multi-tool workflow scenarios
- Database persistence and retrieval
- Cache performance under load

**Validation Tests**:
- Scoring accuracy against known successful/unsuccessful applications
- Hidden opportunity detection validation
- Strategic planning recommendation quality

---

This roadmap provides the framework for implementing the remaining analytics tools that will transform the Grants MCP from a search tool into a comprehensive grant strategy platform.