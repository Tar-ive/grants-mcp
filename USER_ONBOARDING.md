# 🚀 Grants MCP Server - User Onboarding Guide

## Welcome to the World's Most Advanced Grant Discovery Platform!

The Grants MCP server provides AI-powered grant discovery and analysis through Claude Desktop and claude.ai. With 9 advanced tools including Phase 3 intelligent scoring, you can find, analyze, and strategically plan grant applications like never before.

## 🎯 What You Can Do

### 📊 **Grant Discovery & Analysis**
- Search 50,000+ government grants with advanced filtering
- Analyze agency funding landscapes and patterns
- Track funding trends and emerging opportunities
- Get detailed grant summaries with eligibility requirements

### 🧠 **Intelligent Scoring (Phase 3)**
- **Grant Match Scorer**: Multi-dimensional scoring using NIH/NSF methodologies
- **Hidden Opportunity Finder**: Discover undersubscribed grants others miss
- **Strategic Application Planner**: Portfolio optimization and timeline management

### 📈 **Advanced Analytics**
- Competition index calculations
- Success probability scoring
- ROI analysis with effort-adjusted calculations
- Transparent calculation breakdowns

## 🔗 Quick Start: Connect to the Cloud Service

### Option 1: Using claude.ai (Web) - Easiest!

1. **Go to claude.ai** and log in
2. **Add the MCP server** in your settings:
   - URL: `https://grants-mcp-xxx-uc.a.run.app/mcp` (replace with actual URL)
   - Name: `Grants MCP`
3. **Start using immediately** - no local setup required!

### Option 2: Claude Desktop Integration

#### Step 1: Find Your Configuration File

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### Step 2: Add the Configuration

```json
{
  "mcpServers": {
    "grants-mcp-cloud": {
      "command": "npx",
      "args": ["mcp-remote", "https://grants-mcp-xxx-uc.a.run.app/mcp"]
    }
  }
}
```

#### Step 3: Restart Claude Desktop

The MCP tools will appear automatically in your Claude session!

## 🛠️ Available Tools

### **Phase 1-2 Tools (Core Discovery)**

#### 1. **opportunity_discovery** 🔍
Search and analyze grant opportunities with advanced filtering.

**Example Usage:**
```
Find renewable energy grants with funding over $500,000
```

**Parameters:**
- `query`: Keywords to search for
- `max_results`: Number of grants to retrieve
- `page`: Page number for pagination
- `grants_per_page`: Results per page
- `filters`: Advanced filtering options

#### 2. **agency_landscape** 🏛️
Map agencies and their funding focus areas.

**Example Usage:**
```
Show me the funding landscape for the Department of Energy
```

**Parameters:**
- `include_opportunities`: Include current opportunities
- `focus_agencies`: Specific agency codes to analyze
- `funding_category`: Filter by category
- `max_agencies`: Maximum agencies to analyze

#### 3. **funding_trend_scanner** 📈
Analyze funding trends and patterns over time.

**Example Usage:**
```
Analyze funding trends for artificial intelligence research over the last 6 months
```

**Parameters:**
- `time_window_days`: Analysis period (default: 90 days)
- `category_filter`: Focus on specific categories
- `agency_filter`: Focus on specific agencies
- `min_award_amount`: Minimum funding threshold

### **Phase 3 Tools (Advanced Analytics)**

#### 4. **grant_match_scorer** 🎯
Multi-dimensional grant scoring with transparent calculations.

**Example Usage:**
```
Score these NSF computer science grants for my research profile
```

**Scoring Dimensions:**
- Technical Fit Score (0-100)
- Competition Index (NIH/NSF methodology)
- ROI Score (effort-adjusted)
- Success Probability (0-100)
- Overall Strategic Score

#### 5. **explain_grant_score** 📊
Get detailed explanations of grant scoring calculations.

**Example Usage:**
```
Explain how the competition index was calculated for grant EPA-R13-STAR-G1
```

#### 6. **hidden_opportunity_finder** 🔍
Discover undersubscribed grants and timing arbitrage opportunities.

**Example Usage:**
```
Find hidden opportunities in climate science funding that others might miss
```

**Detection Methods:**
- Under-subscribed grants analysis
- Cross-category matching
- Geographic advantages
- Timing arbitrage opportunities

#### 7. **get_top_hidden_opportunities** 🏆
Get the top hidden opportunities based on your criteria.

#### 8. **strategic_application_planner** 📋
Portfolio optimization and strategic planning.

**Example Usage:**
```
Create a strategic application plan for my renewable energy research portfolio
```

**Features:**
- Reach/Match/Safety categorization
- Timeline optimization
- Resource allocation guidance
- Collaboration suggestions

#### 9. **optimize_portfolio** ⚡
Advanced portfolio optimization algorithms.

## 🎓 Example Conversations

### **Basic Grant Search**
```
You: Find grants for renewable energy research with at least $100k funding

Claude: I'll search for renewable energy grants with significant funding for you.

[Uses opportunity_discovery tool]

Found 15 relevant grants totaling $45.2M in potential funding:

**Top Opportunities:**
1. **DOE Solar Energy Research** - $2.5M
   - Deadline: March 15, 2024
   - Focus: Next-generation photovoltaic technology
   
2. **NSF Renewable Energy Systems** - $750K
   - Deadline: April 1, 2024
   - Focus: Grid integration and energy storage

Would you like me to score these grants for strategic priority?
```

### **Advanced Strategic Analysis**
```
You: Create a comprehensive grant strategy for my climate tech startup

Claude: I'll create a strategic analysis using multiple tools to optimize your grant portfolio.

[Uses agency_landscape, funding_trend_scanner, grant_match_scorer, and strategic_application_planner]

**Strategic Grant Portfolio Analysis**

**1. Market Landscape**
- 47 relevant opportunities across 8 agencies
- $127M total available funding in your sector
- Competition index ranges from 15-85 (lower is better)

**2. Top Strategic Matches**
- **EPA SBIR Phase I** (Score: 92/100)
  - Low competition (CI: 18)
  - Perfect technical fit
  - 6-month timeline feasible
  
- **DOE ARPA-E** (Score: 87/100)
  - High funding potential ($2M)
  - Strategic value for company growth

**3. Hidden Opportunities**
Found 3 undersubscribed grants with <20% typical application volume:
- USDA Bioenergy Innovation (CI: 12)
- Commerce Technology Partnership (CI: 15)

**4. Strategic Timeline**
- **Q1 2024**: Apply to EPA SBIR (deadline Feb 15)
- **Q2 2024**: Submit DOE ARPA-E (deadline April 30)
- **Q3 2024**: Target USDA Bioenergy (deadline July 1)

**Portfolio Risk Assessment**: Balanced (40% reach, 45% match, 15% safety)
**Estimated Success Probability**: 73%
**Total Funding Potential**: $4.2M
```

### **Competition Analysis**
```
You: How competitive is the NSF computer science program?

Claude: I'll analyze the competition landscape for NSF computer science funding.

[Uses grant_match_scorer and funding_trend_scanner]

**NSF Computer Science Competition Analysis**

**Competition Index**: 34 (Moderate-High Competition)
- Industry Average: 25-35
- Applications per award: ~8-12
- Historical success rate: 12-15%

**Trend Analysis** (Last 12 months):
- Total funding: $245M (+15% vs previous year)
- Number of awards: 287 (-3% vs previous year)
- Average award size: $854K (+18% vs previous year)

**Strategic Insights**:
✅ **Opportunity**: Larger average awards (more funding per grant)
⚠️ **Challenge**: Slightly fewer total awards (higher competition)
🎯 **Recommendation**: Focus on high-impact, interdisciplinary proposals

**Best Application Windows**:
- **Core Programs**: September deadline (lowest competition)
- **CAREER Awards**: July deadline (early career advantage)
- **EAGER/RAPID**: Rolling (emerging opportunities)
```

## 🎯 Pro Tips for Maximum Success

### **1. Use Multi-Tool Strategies**
Don't just search - analyze, score, and plan:
```
1. Start with opportunity_discovery to find grants
2. Use grant_match_scorer to prioritize
3. Run hidden_opportunity_finder for alternatives
4. Create strategy with strategic_application_planner
```

### **2. Leverage Intelligent Scoring**
```
Ask: "Score these 5 grants for my research profile and explain the calculations"
```
You'll get:
- Technical fit analysis
- Competition assessments
- ROI projections
- Success probabilities
- Transparent mathematical breakdowns

### **3. Find Hidden Gems**
```
Ask: "What undersubscribed grants might others overlook in environmental science?"
```
The system detects:
- Low application volume grants
- Cross-category opportunities
- Geographic advantages
- Timing arbitrage

### **4. Strategic Portfolio Planning**
```
Ask: "Create a diversified grant portfolio for my lab with $2M funding target"
```
You'll receive:
- Risk-balanced portfolio (reach/match/safety)
- Optimized timeline
- Resource allocation guidance
- Collaboration opportunities

## 📊 Understanding Scoring Metrics

### **Competition Index (CI)**
- **0-15**: Low competition (high success probability)
- **15-35**: Moderate competition (typical range)
- **35-50**: High competition (requires strong proposal)
- **50+**: Very high competition (reach opportunities)

### **Technical Fit Score**
- **90-100**: Perfect match for your expertise
- **70-89**: Strong alignment
- **50-69**: Moderate fit (may need partnerships)
- **<50**: Significant gap in requirements

### **Success Probability**
- Based on eligibility match, technical fit, and historical data
- Includes competition adjustment
- Transparent calculation breakdown provided

## 🔧 Troubleshooting

### **Tools Not Appearing**
1. Check configuration file syntax
2. Restart Claude Desktop
3. Verify MCP server URL is correct

### **Slow Responses**
- First queries may be slower (cold start)
- Subsequent queries use intelligent caching
- Complex analyses take 10-30 seconds

### **API Limits**
- The service has generous rate limits
- Heavy usage may experience brief delays
- All core functionality remains available

## 📞 Support & Resources

### **Documentation**
- **Technical Documentation**: See `CLOUD_DEPLOYMENT.md`
- **API Reference**: Built into tool descriptions
- **GitHub Repository**: https://github.com/Tar-ive/grants-mcp

### **Best Practices**
1. **Be Specific**: Detailed queries get better results
2. **Use Follow-ups**: Ask for clarifications and deeper analysis
3. **Combine Tools**: Use multiple tools for comprehensive analysis
4. **Save Results**: Copy important analyses for reference

### **Example Workflows**

**Academic Researcher**: Search → Score → Analyze Trends → Plan Timeline
**Startup Founder**: Landscape Analysis → Hidden Opportunities → Strategic Portfolio
**Grant Writer**: Competition Analysis → Success Probability → ROI Assessment
**Institution**: Multi-PI Analysis → Collaboration Opportunities → Resource Planning

## 🌟 Advanced Features

### **Cross-Reference Analysis**
```
"Compare funding opportunities between NIH and NSF for biomedical engineering"
```

### **Temporal Strategy**
```
"What's the optimal timing strategy for submitting 3 grant applications this year?"
```

### **Portfolio Optimization**
```
"Optimize my 8 target grants for maximum expected value with 40-hour weekly time constraint"
```

---

## 🎉 Ready to Transform Your Grant Strategy?

You now have access to the world's most advanced AI-powered grant analysis platform. Start with simple searches and gradually explore the sophisticated strategic planning tools.

**Your success is our success!** 🚀

---

*The Grants MCP server uses industry-standard methodologies from NIH/NSF and provides transparent calculations for all scoring algorithms. All recommendations are based on quantitative analysis of historical funding data and current opportunity landscapes.*