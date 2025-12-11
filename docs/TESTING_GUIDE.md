# Phase 2 Testing Guide

## Overview

This guide provides comprehensive testing procedures for all Phase 2 (Intelligence) features. Follow these test cases to validate functionality, accuracy, and user experience.

---

## 🧪 Test Environment Setup

### Prerequisites
```bash
# 1. Ensure dependencies are installed
pip install -r requirements.txt

# 2. Set API key (at least one)
export OPENAI_API_KEY="your-key"

# 3. Run the modern app
./run_modern.sh
# or directly:
streamlit run app_modern.py
```

### Initial Configuration
1. Open app in browser (usually http://localhost:8501)
2. Load sample data from sidebar
3. Enable all Phase 2 features:
   - ✅ Use Hybrid Agent
   - ✅ Show Query Analysis
   - ✅ Use Result Reranking

---

## 📋 Test Suite Overview

| Test Area | Test Cases | Priority |
|-----------|------------|----------|
| Query Analyzer | 8 | High |
| Hybrid Agent Routing | 6 | High |
| Tool Integration | 4 | High |
| Result Reranking | 3 | Medium |
| UI Integration | 5 | Medium |
| Error Handling | 4 | Medium |

---

## 1️⃣ Query Analyzer Tests

### Test 1.1: Simple Retrieval Intent
**Query:** `"Show me apartments in Krakow"`

**Expected Analysis:**
- Intent: `SIMPLE_RETRIEVAL`
- Complexity: `SIMPLE`
- Tools: `[RAG_RETRIEVAL]`
- Extracted Filters: `{city: "Krakow"}`
- Should use agent: `False`

**Expected Processing:**
- Method: 📚 RAG
- Response time: 1-3s
- Results: List of Krakow apartments

**Pass Criteria:**
- ✅ Query classified correctly
- ✅ RAG used (not agent)
- ✅ Results relevant to Krakow
- ✅ Fast response time

---

### Test 1.2: Filtered Search Intent
**Query:** `"Find 2-bedroom apartments under $1000 with parking"`

**Expected Analysis:**
- Intent: `FILTERED_SEARCH`
- Complexity: `MEDIUM`
- Tools: `[RAG_RETRIEVAL]`
- Extracted Filters: `{rooms: 2, max_price: 1000, has_parking: true}`
- Should use agent: `False`

**Expected Processing:**
- Method: 📚 RAG
- Response time: 2-4s
- Results: Properties matching all filters
- Reranking applied: ✨

**Pass Criteria:**
- ✅ All filters extracted correctly
- ✅ Results match filters (2-bed, <$1000, parking)
- ✅ Reranking improves relevance
- ✅ No false positives

---

### Test 1.3: Calculation Intent
**Query:** `"Calculate mortgage for $150,000 property with 20% down at 4.5% interest"`

**Expected Analysis:**
- Intent: `CALCULATION`
- Complexity: `COMPLEX`
- Tools: `[MORTGAGE_CALC]`
- Extracted Filters: None
- Should use agent: `True`

**Expected Processing:**
- Method: 🛠️ Agent + Tools
- Response time: 3-6s
- Output: Detailed mortgage breakdown

**Pass Criteria:**
- ✅ Calculation intent detected
- ✅ Mortgage calculator tool invoked
- ✅ Correct calculations:
  - Down payment: $30,000
  - Loan amount: $120,000
  - Monthly payment: ~$608
  - Total interest: ~$98,880
- ✅ Clear formatting

---

### Test 1.4: Comparison Intent
**Query:** `"Compare apartments in Warsaw vs Krakow"`

**Expected Analysis:**
- Intent: `COMPARISON`
- Complexity: `COMPLEX`
- Tools: `[RAG_RETRIEVAL, COMPARATOR]`
- Extracted Filters: `{city: "Warsaw"}, {city: "Krakow"}`
- Should use agent: `True`

**Expected Processing:**
- Method: 🔀 Hybrid
- Response time: 6-12s
- Output: Side-by-side comparison

**Pass Criteria:**
- ✅ Comparison intent detected
- ✅ Both cities included
- ✅ Statistical comparison provided
- ✅ Clear differences highlighted

---

### Test 1.5: Analysis Intent
**Query:** `"What's the average price per square meter in Krakow?"`

**Expected Analysis:**
- Intent: `ANALYSIS`
- Complexity: `COMPLEX`
- Tools: `[RAG_RETRIEVAL, PYTHON_CODE]`
- Should use agent: `True`

**Expected Processing:**
- Method: 🔀 Hybrid or 🛠️ Agent
- Response time: 5-10s
- Output: Statistical analysis

**Pass Criteria:**
- ✅ Analysis intent detected
- ✅ Calculation performed
- ✅ Average provided with context
- ✅ Sample size mentioned

---

### Test 1.6: Recommendation Intent
**Query:** `"What's the best value apartment for $1000?"`

**Expected Analysis:**
- Intent: `RECOMMENDATION`
- Complexity: `COMPLEX`
- Tools: `[RAG_RETRIEVAL]`
- Should use agent: Depends

**Expected Processing:**
- Method: 📚 RAG or 🔀 Hybrid
- Response time: 3-8s
- Output: Top recommendations with reasoning

**Pass Criteria:**
- ✅ Recommendation intent detected
- ✅ Value-based ranking
- ✅ Explanation provided
- ✅ Multiple options shown

---

### Test 1.7: Conversation Intent
**Query:** `"Tell me more about the last property"` (requires previous context)

**Expected Analysis:**
- Intent: `CONVERSATION`
- Complexity: `SIMPLE` or `MEDIUM`
- Tools: `[RAG_RETRIEVAL]`

**Expected Processing:**
- Method: 📚 RAG
- Response time: 2-4s
- Output: Details about previously mentioned property

**Pass Criteria:**
- ✅ Conversation intent detected
- ✅ Context maintained
- ✅ Relevant details provided
- ✅ References previous query

---

### Test 1.8: Multi-Filter Complex Query
**Query:** `"Show me 2-3 bedroom apartments in Krakow between $800-$1200 with parking and garden near schools"`

**Expected Analysis:**
- Intent: `FILTERED_SEARCH`
- Complexity: `MEDIUM` or `COMPLEX`
- Tools: `[RAG_RETRIEVAL]`
- Extracted Filters:
  ```
  {
    rooms: [2, 3],
    city: "Krakow",
    min_price: 800,
    max_price: 1200,
    has_parking: true,
    has_garden: true
  }
  ```

**Expected Processing:**
- Method: 📚 RAG
- Response time: 3-5s
- Reranking: ✨ Applied

**Pass Criteria:**
- ✅ All filters extracted
- ✅ Results match all criteria
- ✅ Proximity to schools mentioned
- ✅ Results prioritized well

---

## 2️⃣ Hybrid Agent Routing Tests

### Test 2.1: RAG-Only Path (Simple Query)
**Setup:** Enable hybrid agent

**Query:** `"Show me apartments in Warsaw"`

**Expected:**
- Routing: RAG-only
- No tools invoked
- Fast response (~2s)
- Badge: 📚 RAG

**Validation:**
```python
# Check in verbose mode or logs
assert routing_decision == "rag_only"
assert no_tools_used == True
assert response_time < 3s
```

---

### Test 2.2: Agent-Only Path (Pure Calculation)
**Query:** `"Calculate mortgage for $200,000 with 15% down at 5% for 25 years"`

**Expected:**
- Routing: Agent + Tools
- Mortgage calculator tool invoked
- No RAG retrieval needed
- Badge: 🛠️ Agent + Tools

**Validation:**
- ✅ Tool output visible
- ✅ Accurate calculations
- ✅ No property retrieval
- ✅ Clear breakdown

---

### Test 2.3: Hybrid Path (Query + Analysis)
**Query:** `"Compare the average prices of 2-bedroom apartments in all cities"`

**Expected:**
- Routing: Hybrid
- RAG retrieves properties
- Agent performs analysis
- Badge: 🔀 Hybrid

**Validation:**
- ✅ Properties retrieved first
- ✅ Analysis performed second
- ✅ Both steps visible
- ✅ Comprehensive answer

---

### Test 2.4: Toggle Agent Off/On
**Test Steps:**
1. Disable "Use Hybrid Agent"
2. Query: `"Calculate mortgage for $180,000"`
3. **Expected:** Simple RAG response (no calculation)
4. Enable "Use Hybrid Agent"
5. Same query
6. **Expected:** Proper mortgage calculation

**Pass Criteria:**
- ✅ Without agent: Generic/incomplete response
- ✅ With agent: Accurate calculation
- ✅ Clear difference in quality

---

### Test 2.5: Error Recovery
**Query:** `"Calculate mortgage for invalid property"` (intentionally vague)

**Expected:**
- Agent attempts to use tool
- Tool returns error or asks for clarification
- Fallback to RAG or explanation
- No crash

**Pass Criteria:**
- ✅ Graceful error handling
- ✅ User-friendly message
- ✅ No stack trace shown
- ✅ Suggests correct format

---

### Test 2.6: Context Injection
**Query:** `"Compare these properties"` (after viewing several)

**Expected:**
- Agent retrieves recent properties from context
- Performs comparison on actual data
- Uses comparator tool

**Pass Criteria:**
- ✅ Context understood
- ✅ Correct properties compared
- ✅ Detailed comparison
- ✅ No hallucination

---

## 3️⃣ Tool Integration Tests

### Test 3.1: Mortgage Calculator Accuracy
**Test Queries:**

1. `"Calculate mortgage for $100,000, 20% down, 4% rate, 30 years"`
   - Expected monthly: $382

2. `"Calculate mortgage for $250,000, 10% down, 6% rate, 15 years"`
   - Expected monthly: $1,899

3. `"Calculate mortgage for $180,000, 25% down, 3.5% rate, 20 years"`
   - Expected monthly: $781

**Pass Criteria:**
- ✅ All calculations within ±$5 of expected
- ✅ Down payment calculated correctly
- ✅ Total interest calculated correctly
- ✅ Formula: M = P[r(1+r)^n]/[(1+r)^n-1]

---

### Test 3.2: Property Comparator
**Query:** `"Compare a 2-bed apartment at $900 vs a 3-bed at $1200"`

**Expected Output:**
- Side-by-side comparison
- Price per room analysis
- Feature comparison
- Recommendation

**Pass Criteria:**
- ✅ Both properties analyzed
- ✅ Pros/cons listed
- ✅ Value assessment
- ✅ Clear winner or trade-offs

---

### Test 3.3: Price Analyzer
**Query:** `"Analyze the price distribution in Krakow"`

**Expected Output:**
- Average, median, min, max
- Price ranges
- Statistical breakdown
- Sample size

**Pass Criteria:**
- ✅ Statistics calculated
- ✅ Distribution described
- ✅ Sample size mentioned
- ✅ Insights provided

---

### Test 3.4: Multiple Tool Chain
**Query:** `"Find best value 2-bed under $1000 and calculate mortgage"`

**Expected:**
- RAG tool: Retrieve properties
- Comparator tool: Find best value
- Mortgage calc tool: Calculate for selected property
- Chained execution

**Pass Criteria:**
- ✅ All tools used in sequence
- ✅ Results flow logically
- ✅ Final answer comprehensive
- ✅ No tool errors

---

## 4️⃣ Result Reranking Tests

### Test 4.1: Exact Match Boosting
**Setup:** Query with specific keywords

**Query:** `"Affordable studio with garden"`

**Without Reranking:**
- Observe initial order of results

**With Reranking:**
- Properties with "garden" should rank higher
- "Affordable" properties boosted
- Exact keyword matches prioritized

**Pass Criteria:**
- ✅ Reranked order different from initial
- ✅ More relevant results at top
- ✅ Keyword matches prioritized
- ✅ ✨ Badge displayed

---

### Test 4.2: Metadata Alignment
**Query:** `"2-bedroom with parking under $1000"`

**With Reranking:**
- Properties matching all criteria rank highest
- Properties matching 2/3 criteria next
- Properties matching 1/3 criteria lowest

**Pass Criteria:**
- ✅ Perfect matches at top
- ✅ Partial matches ordered by relevance
- ✅ Non-matches filtered or ranked low
- ✅ Visible quality improvement

---

### Test 4.3: Diversity Penalty
**Query:** `"Show me apartments"`

**With Reranking:**
- Results should show variety of cities
- Results should show variety of price ranges
- Not all results from same neighborhood

**Pass Criteria:**
- ✅ Multiple cities represented
- ✅ Price range diversity
- ✅ Not clustering on single feature
- ✅ Better user experience

---

## 5️⃣ UI Integration Tests

### Test 5.1: Query Analysis Display
**Steps:**
1. Enable "Show Query Analysis"
2. Enter query: `"Find 2-bed with parking under $1000"`
3. Observe analysis display

**Expected Display:**
```
🔍 Query Analysis
Intent: filtered_search
Complexity: medium
Tools needed: [rag_retrieval]
Extracted filters: {rooms: 2, has_parking: true, max_price: 1000}
Should use agent: False
```

**Pass Criteria:**
- ✅ Analysis appears before results
- ✅ Expandable section
- ✅ All fields populated correctly
- ✅ Easy to read format

---

### Test 5.2: Processing Badges
**Test Different Query Types:**

1. Simple: Should show 📚 RAG
2. Calculation: Should show 🛠️ Agent + Tools
3. Analysis: Should show 🔀 Hybrid
4. With reranking: Should show ✨ Reranked

**Pass Criteria:**
- ✅ Correct badge for each type
- ✅ Badge visible and clear
- ✅ Consistent placement
- ✅ Informative for user

---

### Test 5.3: Model Switching
**Steps:**
1. Start with GPT-4o-mini
2. Run query: `"Show me apartments"`
3. Switch to Claude 3.5 Haiku
4. Run same query
5. Compare results

**Pass Criteria:**
- ✅ No errors during switch
- ✅ Agent reinitializes correctly
- ✅ Both provide valid results
- ✅ Quality comparable

---

### Test 5.4: Feature Toggle Persistence
**Steps:**
1. Enable all Phase 2 features
2. Refresh page
3. Check if settings persist

**Expected:**
- Session state maintained
- Settings preserved
- No reset to defaults

**Pass Criteria:**
- ✅ Hybrid agent still enabled
- ✅ Query analysis still enabled
- ✅ Reranking still enabled
- ✅ Seamless experience

---

### Test 5.5: Source Attribution
**Query:** `"Show me apartments in Krakow"`

**Expected:**
- Source documents displayed
- Expandable section
- Metadata visible
- Content preview

**Pass Criteria:**
- ✅ Sources section present
- ✅ Click to expand works
- ✅ Metadata shows city, price, etc.
- ✅ Content relevant to query

---

## 6️⃣ Error Handling Tests

### Test 6.1: Invalid API Key
**Setup:** Use invalid or expired API key

**Expected:**
- Clear error message
- No cryptic stack trace
- Guidance on fixing
- App doesn't crash

**Pass Criteria:**
- ✅ User-friendly error
- ✅ Suggests checking API key
- ✅ Can continue with different provider
- ✅ Graceful degradation

---

### Test 6.2: No Data Loaded
**Steps:**
1. Start app without loading data
2. Try to query

**Expected:**
- Warning message
- Prompt to load data
- No crash
- Clear instructions

**Pass Criteria:**
- ✅ Helpful message displayed
- ✅ Points to sidebar
- ✅ Doesn't attempt search
- ✅ User knows what to do

---

### Test 6.3: Malformed Query
**Query:** `"jfkdlsjflkdsjf"` (random characters)

**Expected:**
- Attempts classification
- Returns generic response or asks for clarification
- No crash
- Helpful feedback

**Pass Criteria:**
- ✅ Handles gracefully
- ✅ Doesn't error out
- ✅ Provides feedback
- ✅ Can continue chatting

---

### Test 6.4: Tool Failure Recovery
**Setup:** Simulate tool failure (e.g., mortgage calc with invalid input)

**Expected:**
- Tool error caught
- Fallback to RAG or explanation
- User informed
- Can retry

**Pass Criteria:**
- ✅ No app crash
- ✅ Error explained
- ✅ Alternative provided
- ✅ Recoverable state

---

## 🎯 Performance Tests

### Test P.1: Response Time Benchmarks
Run each query type 5 times and measure:

| Query Type | Target Time | Acceptable Range |
|------------|-------------|------------------|
| Simple RAG | 2s | 1-3s |
| Filtered + Rerank | 3s | 2-4s |
| Agent + Tool | 5s | 3-7s |
| Hybrid Analysis | 8s | 5-12s |

**Pass Criteria:**
- ✅ 80% of queries within target
- ✅ 95% within acceptable range
- ✅ No timeouts
- ✅ Consistent performance

---

### Test P.2: Concurrent Queries
**Setup:** Open multiple browser tabs

**Steps:**
1. Submit query in tab 1
2. Immediately submit query in tab 2
3. Check if both complete

**Pass Criteria:**
- ✅ Both queries complete
- ✅ No interference
- ✅ Correct results in each tab
- ✅ Session isolation

---

### Test P.3: Large Result Sets
**Query:** `"Show me all apartments"` (retrieves many results)

**Expected:**
- Handles large result sets
- UI remains responsive
- Results paginated or limited
- No browser freeze

**Pass Criteria:**
- ✅ Returns promptly
- ✅ UI stays responsive
- ✅ Results manageable
- ✅ No performance degradation

---

## 📊 Test Results Template

```markdown
## Test Session: [Date]

### Configuration
- App Version: V3 - Phase 2
- Model: [Provider/Model]
- Dataset: [Sample/Custom]
- Features Enabled: [Hybrid Agent, Query Analysis, Reranking]

### Results Summary
- Total Tests: X
- Passed: Y
- Failed: Z
- Pass Rate: Y/X%

### Test Details

#### Test 1.1: Simple Retrieval
- Status: ✅ PASS / ❌ FAIL
- Notes: [Any observations]

[Repeat for all tests]

### Issues Found
1. [Issue description]
   - Severity: High/Medium/Low
   - Steps to reproduce
   - Expected vs Actual

### Recommendations
- [Improvements needed]
- [Edge cases to address]
- [Performance optimizations]
```

---

## 🚀 Running the Complete Test Suite

### Quick Test (15 minutes)
Run these essential tests:
- 1.1, 1.2, 1.3 (Query Analyzer)
- 2.1, 2.2 (Agent Routing)
- 3.1 (Mortgage Calculator)
- 4.1 (Reranking)
- 5.1, 5.2 (UI)

### Full Test (60 minutes)
Run all tests in order, document results

### Regression Test
Run after any code changes to ensure nothing broke

---

## 📋 Acceptance Criteria

**Phase 2 is considered fully validated if:**

✅ Query Analyzer: 90%+ accuracy on intent classification
✅ Agent Routing: Correct routing in 95%+ of cases
✅ Tools: All tools function correctly with <5% error rate
✅ Reranking: Measurable improvement in top-3 relevance
✅ UI: All features accessible and working
✅ Performance: 90%+ of queries within target times
✅ Errors: All errors handled gracefully
✅ User Experience: Smooth, intuitive interaction

---

## 🐛 Bug Reporting Template

```markdown
**Title:** [Brief description]

**Test Case:** [Which test revealed this]

**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happened]

**Environment:**
- App Version: V3 Phase 2
- Model: [Provider/Model]
- Browser: [Browser/Version]
- OS: [Operating System]

**Screenshots/Logs:**
[Attach any relevant evidence]

**Severity:**
- [ ] Critical (blocks testing)
- [ ] High (major feature broken)
- [ ] Medium (feature partially broken)
- [ ] Low (minor issue)

**Priority:**
- [ ] P0 (fix immediately)
- [ ] P1 (fix before release)
- [ ] P2 (fix in next iteration)
- [ ] P3 (nice to have)
```

---

## 🎓 Testing Best Practices

1. **Test in Order**: Run tests sequentially to build confidence
2. **Document Everything**: Record observations, even for passing tests
3. **Test Edge Cases**: Try unusual inputs and scenarios
4. **Compare Models**: Test with different AI models
5. **Check Logs**: Review verbose output for issues
6. **User Perspective**: Test as an end user would interact
7. **Repeat Critical Tests**: Run important tests multiple times
8. **Test Combinations**: Try feature combinations
9. **Measure Performance**: Time responses systematically
10. **Report Issues**: Document bugs immediately with details

---

**Happy Testing! 🧪**
### Playwright E2E Setup
```bash
# Install Playwright browsers (required for MCP/CLI)
npx playwright install
npx playwright install chromium

# Run e2e tests
npx playwright test -c playwright.config.ts --reporter=list
```
Note: Playwright is used for CI and local debugging only. The application does not include any MCP Playwright integrations or test‑specific DOM markers.
