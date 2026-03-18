# Indian Job Market Research for Reqruit
## Comprehensive 23-Dimension Analysis (March 2026)

---

## 1. Job Platforms: Landscape, Features, APIs & Market Share

### Market Leaders

| Platform | Monthly Visits | Strength | Target Segment |
|----------|---------------|----------|----------------|
| **Naukri.com** | 50M+ users, 7.83 crore resumes | Largest resume DB, 500K+ recruiters, fills 80%+ postings | All segments, dominant in India |
| **LinkedIn India** | 25.61% global job-board share | Professional networking, referrals, employer branding | White-collar, mid-senior |
| **Indeed India** | 32.34% global share | Volume, international reach | All levels |
| **Apna** | 10M+ downloads, 2Cr+ users | Blue-collar, Tier 2/3, vernacular | Entry-level, blue-collar |
| **Instahyre** | 0.27% market share | Invite-only, curated tech/startup roles | Mid-senior tech |
| **TimesJobs** | Declining | Legacy brand, part of Times Group | General |
| **Shine.com** | Declining | HT Media owned | General |

### Niche Platforms Worth Integrating
- **Cutshort**: Curated tech roles, skill-based matching
- **Hirist/BigShyft**: Premium tech roles
- **iimjobs/Hirect**: Management and leadership roles
- **Wellfound (AngelList)**: Startup jobs
- **Foundit (formerly Monster India)**: General with strong analytics

### API & Data Access

**Naukri.com**: No public API. Enterprise-only access (paid) for ATS vendors and large partners. Available endpoints include job posting/requisition, resume search, applicant tracking, and webhooks. For Reqruit, third-party scraping solutions exist:
- **Apify scrapers**: Multiple actors for Naukri job data extraction
- **ScrapingBee**: Naukri-specific scraping API
- **TheirStack**: Job postings in JSON format

**LinkedIn**: Official API (limited), focused on company pages and job postings for partners. LinkedIn Talent Solutions API requires partnership.

**Indeed**: Publisher API available for job search integration (XML feed).

### Reqruit Opportunity
Build a unified job aggregation layer that pulls from multiple platforms. Since official APIs are limited, consider:
- RSS/XML feeds where available
- Partnership applications with Naukri/LinkedIn
- Third-party data providers (TheirStack, Apify)
- User-authenticated integrations (apply-on-behalf with stored credentials)

---

## 2. Campus Placements

### How Indian Campus Recruitment Works

**Placement Season Timeline**:
- **Pre-Placement Offers (PPOs)**: July-August (from summer internships)
- **Phase 1 (Dream/Super-Dream)**: August-December
- **Phase 2 (Regular)**: January-March
- **Phase 3 (Remaining)**: April onwards

**Company Tiers**:
| Category | CTC Range | Examples |
|----------|----------|---------|
| **Super Dream** | >25 LPA | Google, Microsoft, Goldman Sachs, Tower Research |
| **Dream** | 12-25 LPA | Amazon, Samsung, Adobe, Qualcomm |
| **Regular** | 6-12 LPA | TCS Digital, Infosys, Cognizant, Capgemini |
| **Mass Recruiters** | 3.5-6 LPA | TCS, Wipro, HCL (bulk hiring) |

**CGPA Cutoffs (2025-2026)**:
- Service-based companies: 6.0 CGPA (60%)
- Product companies: 6.5 CGPA (65%)
- Investment banks: 7.0 CGPA (70%)
- Sweet spot for top tech: 7.5-8.0 CGPA

**Key Trends (2025-26)**:
- More students rejecting PPOs (10-20% increase in PPO offers, but more rejections)
- IIT Delhi: 1,275 offers including 300+ PPOs by December 2025
- AI/ML roles surging on campuses
- Companies returning to campuses in force after post-COVID lull

### Reqruit Opportunity
- Campus placement calendar tracker
- CGPA-to-eligibility matcher (which companies can you apply to?)
- PPO decision advisor (compare PPO vs open-market options)
- Mock placement interview prep (company-specific patterns)
- Placement committee integration for colleges

---

## 3. Walk-in Interviews

### Current State
Walk-in drives remain prevalent in India, especially for:
- **IT Services/BPO/KPO**: TCS, Wipro, Cognizant, Capgemini conduct regular walk-ins
- **Freshers**: First-job candidates, especially from Tier 2/3 colleges
- **Support Roles**: Customer support, technical support, data entry
- **Retail & Hospitality**: Store staff, restaurant staff
- **Healthcare**: Nursing staff, lab technicians
- **Manufacturing**: Shop floor, quality control

**Key Cities for Walk-ins**: Chennai, Bangalore, Hyderabad, Mumbai, Pune, Delhi, Kolkata, Noida

**Platforms Tracking Walk-ins**:
- FreshersVoice.com: Dedicated walk-in drive listings
- Naukri.com: Walk-in filter available
- Indeed: Walk-in keyword search
- RemarkHR: IT walk-in interviews aggregator

### Reqruit Opportunity
- Walk-in drive aggregator with location-based alerts
- Map integration showing walk-in venues and dates
- Document checklist generator (what to carry)
- Walk-in success rate predictor based on historical data

---

## 4. Notice Period Culture

### Standard Notice Periods
| Level | Typical Notice Period |
|-------|---------------------|
| Entry-level/Freshers | 15-30 days |
| Mid-level (3-7 yrs) | 30-60 days |
| Senior/Leadership | 60-90 days |
| IT Services (all levels) | 60-90 days (strict) |

### The "Immediate Joiner" Paradox
- Companies increasingly demand immediate joiners (especially tech, e-commerce, BFSI, consulting)
- But most candidates are locked into 60-90 day notice periods
- This creates a systemic mismatch that frustrates both sides

### Buyout Mechanics
- Employee pays remaining notice period salary to employer for early release
- New employer sometimes reimburses buyout amount
- Negotiation is common but not guaranteed
- Some companies (TCS, Infosys, Wipro) have strict no-early-release policies

### Reqruit Opportunity
- **Notice Period Optimizer**: Help candidates plan job switches around notice periods
- **Buyout Calculator**: Calculate buyout cost and ROI of early joining
- **Notice Period Filter**: Match candidates with companies that accept their notice period
- **"Serving Notice" Job Board**: Connect candidates currently serving notice with hiring companies
- **Negotiation Scripts**: AI-generated buyout negotiation templates

---

## 5. CTC Structure

### Standard Indian CTC Breakdown

```
CTC (Cost to Company)
├── Gross Salary (Monthly)
│   ├── Basic Salary (40-50% of CTC) -- fully taxable
│   ├── HRA (House Rent Allowance) -- partially tax-exempt if renting
│   ├── Special Allowance -- fully taxable
│   ├── Conveyance Allowance
│   ├── Medical Allowance
│   ├── LTA (Leave Travel Allowance)
│   └── Other Allowances
├── Employee PF (12% of Basic) -- deducted from salary
├── Employer PF (12% of Basic) -- employer's cost, part of CTC
├── Gratuity (4.81% of Basic) -- paid after 5 years
├── Insurance (Group health/life) -- employer cost
├── Variable Pay / Performance Bonus (10-30% of CTC)
└── ESOPs (if applicable) -- taxed at exercise
```

### 2025-26 Regulatory Changes
- **New Labour Codes**: Basic + DA must be at least 50% of total compensation
- **Impact**: Higher PF contributions, lower take-home for same CTC
- **New Tax Regime (default)**: Income tax-free up to 12.75L for salaried (including 75K standard deduction)

### CTC vs In-Hand Reality
For a 10 LPA CTC, typical monthly in-hand: ~65,000-72,000 (depending on tax regime and structure)

### Reqruit Opportunity
- **CTC Decoder**: Input CTC, output detailed monthly in-hand salary
- **Offer Comparator**: Compare two offers side-by-side (different CTC structures)
- **Tax Regime Advisor**: Old vs New regime recommendation based on individual situation
- **"Real Salary" Calculator**: What your CTC actually means after all deductions

---

## 6. IT Services Hiring

### The Big-4 IT Services (FY2025-26)

| Company | Workforce | FY26 Trend | Fresher Plans |
|---------|-----------|-----------|---------------|
| **TCS** | 600K+ | Reduced ~12,000 roles (skill realignment) | Selective |
| **Infosys** | 300K+ | Added ~5,000 (cautious) | Moderate |
| **Wipro** | 240K+ | Added ~6,500 | Moderate |
| **HCL Tech** | 220K+ | Aggressive fresher hiring | 20,000+ freshers |

**Combined**: Top IT firms expect to onboard **82,000 graduates in FY2026**

### Service-Based vs Product-Based Distinction

| Dimension | Service-Based | Product-Based |
|-----------|--------------|---------------|
| Hiring Volume | Mass (thousands) | Selective (hundreds) |
| Typical CTC (Fresher) | 3.5-6 LPA | 10-30+ LPA |
| Work Nature | Client projects, maintenance | Own product development |
| Notice Period | 60-90 days (strict) | 30-60 days |
| Growth | Slower, bench time | Faster, more ownership |
| Examples | TCS, Infosys, Wipro | Google, Flipkart, Razorpay |

### "Twin Hiring" Pattern (2025)
- Hiring in advanced skills (AI, cloud, cybersecurity): Growing
- Legacy roles (manual testing, basic Java): Shrinking/flat
- Sector hiring intent: ~59% in H1 2025

### Reqruit Opportunity
- Service-vs-Product company classifier
- Mass hiring drive alerts (NQT, InfyTQ, etc.)
- "Bench risk" indicator for service company roles
- Career path simulator: Service -> Product transition roadmap

---

## 7. Startup Culture & Job Market

### Geographic Hubs

| City | Startup Specialization | Key Ecosystems |
|------|----------------------|----------------|
| **Bangalore** | Deep tech, SaaS, fintech | Koramangala, HSR Layout, Indiranagar |
| **Delhi NCR** | E-commerce, edtech, D2C | Gurugram, Noida |
| **Mumbai** | Fintech, media-tech | BKC, Andheri, Powai |
| **Hyderabad** | Enterprise SaaS, biotech | HITEC City, Gachibowli |
| **Pune** | SaaS, automotive-tech | Hinjewadi, Kharadi |
| **Chennai** | SaaS (Zoho ecosystem), manufacturing-tech | OMR, Guindy |

### Funding & Hiring (2025-26)
- AI funding: $665M in 2025 (50% YoY surge)
- Enterprise SaaS investments: Up 66%
- Sector-specific growth: Retail/E-commerce/FMCG (35-40%), Fintech (25-30%), Auto/Travel (20-25%), SaaS/HealthTech (15-20%)

### Hiring Patterns
- Fresher hires (0-3 yrs): Fell to 41% (from 53% in April 2024)
- Prioritizing 4-6 years (28%) and 7-10 years (15%) for specialized roles
- Startups increasingly hiring from Tier-2 cities (32% of planned hiring)

### Reqruit Opportunity
- Startup health checker (funding stage, burn rate, runway)
- Equity/ESOP valuation calculator
- Startup culture fit assessment
- "Startup vs Corporate" decision framework

---

## 8. Government Jobs

### Major Exam Bodies & Exams

| Body | Key Exams | Posts | Scale |
|------|----------|-------|-------|
| **UPSC** | CSE (IAS/IPS/IFS), CDS, NDA, ESE | Civil Services, Defense, Engineering | ~1,000 posts/year |
| **SSC** | CGL, CHSL, MTS, GD Constable | Central Govt Group B/C | ~50,000+ posts/year |
| **IBPS** | PO, Clerk, SO, RRB | Banking sector | ~40,000+ posts/year |
| **RRB** | NTPC, JE, Group D, ALP | Railways | ~100,000+ posts/year |
| **State PSCs** | State civil services | State administration | Varies by state |

### Popular Prep Platforms
- **Oliveboard**: Banking, SSC, Railways mock tests
- **Testbook**: Comprehensive govt exam prep
- **Unacademy**: Video lectures, live classes
- **BYJU's Exam Prep**: Structured courses
- **SarkariResult/FreeJobAlert**: Notifications aggregator

### Reqruit Opportunity
- Exam eligibility checker (age, education, attempts remaining)
- Exam calendar with smart reminders
- Previous year paper analysis and pattern prediction
- "Govt vs Private" career comparison tool
- Application deadline tracker across all recruitment bodies

---

## 9. Blue Collar & Gig Economy

### Major Platforms

| Platform | Focus | Scale |
|----------|-------|-------|
| **Apna** | Blue-collar jobs, Tier 2/3 | 2 Cr+ users, unicorn |
| **WorkIndia** | Blue/grey collar | 30M job seekers, 100K businesses/month |
| **Aasaan Jobs** | Entry-level, vernacular | Regional focus |
| **nia.one** | Gig worker, daily wage | Growing |

### Market Data
- Blue-collar gig jobs: Up 92% in 2024
- Last-mile logistics: Primary growth driver
- 58% of blue-collar jobs pay < Rs 20,000/month
- Delhi leads gig economy (17.7%), followed by Mumbai (16.57%)

### Key Features of Successful Blue-Collar Platforms
- Direct chat between employer and candidate
- Vernacular/multi-language support
- Background verification
- Digital contracts
- Upskilling programs

### Reqruit Opportunity
- If expanding to blue-collar: Vernacular UI, voice-based job search
- Gig economy dashboard (daily/weekly earnings tracker)
- Skill-to-earning potential mapper
- Shift management and scheduling assistant

---

## 10. Freelancing

### Market Size
- India freelance platforms market: $221.9M (2024) -> projected $775.6M by 2030 (24% CAGR)
- India has ~15 million freelancers
- Indian freelancers make up ~9% of Upwork users
- ~50% of India's workforce engages in freelancing or independent work

### Platform Landscape

| Platform | Strength | Fee Structure |
|----------|----------|--------------|
| **Upwork** | Long-term contracts, higher rates | 10% + 3% processing |
| **Fiverr** | Quick gigs, service packages | 20% + 2-3% processing |
| **Freelancer.com** | Competitions, wide range | 10% or $5 min |
| **Truelancer** | INR payments, local clients | Lower fees |
| **Toptal** | Elite freelancers only | Network model |

### Growth Drivers
- Internet penetration expansion
- Digital literacy improvements
- Global remote work acceptance
- India's cost advantage for international clients

### Reqruit Opportunity
- Freelance income estimator by skill/platform
- Portfolio builder optimized for Indian market
- Rate card generator based on market data
- Tax calculator for freelance income (GST, ITR-4)

---

## 11. Job Seeker Frustrations

### Top Pain Points

1. **Ghost Jobs**: ~30% of tech job postings in 2026 are estimated to be ghost jobs (posted with no intent to hire)
2. **Salary Non-Disclosure**: Only ~50% of job postings include salary info (up from 26% in 2022, but still frustrating)
   - Senior roles: Only 13% disclose salary
   - Junior/mid: ~32% disclose
3. **Recruiter Spam**: Mass outreach via WhatsApp, email, LinkedIn with irrelevant opportunities
4. **Fake Listings**: Data harvesting disguised as job postings
5. **Application Black Holes**: Apply and never hear back
6. **CTC Manipulation**: Inflating CTC with components candidates never receive
7. **Notice Period Mismatch**: "Immediate joiner only" for roles where everyone has 90-day notice
8. **Location Bait-and-Switch**: Job listed as Bangalore, actual posting in tier-3 city
9. **Bond/Service Agreements**: Forced 1-2 year bonds with penalty clauses, especially for freshers
10. **Unpaid Assessments**: Long take-home assignments with no compensation or feedback

### Reqruit Opportunity
- **Ghost Job Detector**: ML model to flag likely ghost postings (age, repost frequency, company hiring velocity)
- **Salary Estimator**: Predict salary range even when not disclosed
- **Application Tracker**: Status tracking with automated follow-ups
- **Recruiter Reputation Score**: Based on response rates and candidate feedback
- **"Red Flag" Alerts**: Warn about suspicious postings, bonds, forced relocations

---

## 12. Job Market Scams

### Common Scam Types

1. **Fake Offer Letters**: Professional-looking offers from real companies, now AI-generated
2. **Registration/Processing Fees**: Demand Rs 5,000-50,000 for "guaranteed placement"
3. **Data Harvesting**: Fake job posts to collect Aadhaar, PAN, bank details
4. **Resume Scraping & Resale**: Harvest resumes from portals, sell to fraud companies
5. **OTP Fraud**: "Verify your identity for interview" -> steal OTP for financial fraud
6. **Fake Interview Calls**: WhatsApp/Telegram messages impersonating company HR
7. **Task-Based Scams**: "Complete this task for Rs 500" -> escalating "investment" demands
8. **Placement Scams in Colleges**: Private colleges inflating placement numbers

### Scale of Problem
- 56% of Indian job seekers have encountered scams
- Job scams: 150% rise in financial losses YoY
- 15% of all cybercrimes in India (2020-2023) were job-related

### Notable 2025-26 Cases
- Nestle India had to issue public statement about fake recruitment using their name
- AI-generated deepfake interviews emerging as new threat
- Mass WhatsApp/Telegram campaigns using company logos

### Reqruit Opportunity
- **Scam Detection Engine**: Flag suspicious postings, verify company authenticity
- **Company Verification**: Cross-reference with MCA (Ministry of Corporate Affairs) database
- **Offer Letter Validator**: Check against known templates and verify company email domains
- **Safe Application Guarantees**: Only show verified employer listings
- **Scam Reporting & Community Alerts**: Crowdsourced scam database

---

## 13. Salary Transparency Platforms

### Platform Comparison

| Platform | India Coverage | Data Quality | Unique Value |
|----------|---------------|-------------|-------------|
| **AmbitionBox** | Excellent (India-focused) | Good, anonymous submissions | Company reviews + salary + interview questions |
| **Glassdoor India** | Good | Moderate (older data skews low) | Global comparisons, CEO ratings |
| **levels.fyi** | Growing (tech-focused) | High (verified submissions) | Level-wise breakdown, TC comparisons |
| **PayScale India** | Moderate | Moderate | Skills-based pay analysis |
| **Salary.in** | Emerging | Variable | India-specific |

### Important Caveats
- Data often spans 10+ years, skewing averages lower than current market
- Self-reported data has inherent biases
- CTC vs in-hand confusion in submissions
- Regional variations not always captured

### Salary Disclosure Progress (India)
- 2022: 26% of job postings disclosed salary
- 2023: 47% disclosed
- 2025: 50%+ disclosed (Indeed India data)
- IT, BFSI, Consulting leading the transparency push

### Reqruit Opportunity
- **Salary Intelligence Engine**: Aggregate data from multiple platforms
- **Real-time Market Rate**: Current salary ranges by role/city/experience
- **Offer Benchmarker**: "Is this offer competitive?" instant analysis
- **Salary Trajectory Predictor**: Expected earnings over 5/10 years by career path

---

## 14. Resume Format (India vs US)

### Key Differences

| Element | Indian Format | US Format |
|---------|--------------|-----------|
| **Photo** | Sometimes included (legacy practice) | Never included |
| **Personal Details** | DOB, gender, marital status, nationality | Not included (anti-discrimination) |
| **Father's Name** | Common in biodata format | Never included |
| **Declaration** | "I declare the above is true..." with signature | Not used |
| **Length** | 2-3 pages acceptable | Strictly 1 page (entry), 2 max |
| **Format Name** | "CV" or "Biodata" | "Resume" |
| **Academic Details** | 10th, 12th marks included | Only degree and university |
| **Objective** | Still common | Replaced by "Summary" |

### Modern Indian Resume Trends (2025-26)
- MNCs and IT companies moving toward US-style resumes
- ATS systems cannot process photos (hurts ATS score)
- Government and traditional companies still expect biodata format
- Startups prefer LinkedIn profiles over traditional resumes

### Reqruit Opportunity
- **Smart Resume Builder**: Auto-detect target company type and format accordingly
- **Format Switcher**: Convert between Indian biodata, Indian modern, and US formats
- **ATS Score Checker**: Ensure resume passes ATS filters
- **Declaration Generator**: Auto-generate for traditional companies
- **"Resume vs LinkedIn" Optimizer**: Ensure consistency and completeness

---

## 15. WFH in Tier 2/3 Cities

### Growth Metrics
- Tier 2/3 city hiring activity: Growing 21-23% YoY (vs 14% in Tier 1 metros)
- Tier-2 cities now account for 32% of all planned hiring (vs 53% in Tier 1)
- Coimbatore: Fastest-growing hiring market in 2025

### Key Tier 2/3 Hubs

| City | Specialization | Infrastructure |
|------|---------------|---------------|
| **Jaipur** | IT services, BPO, digital marketing | Growing coworking ecosystem |
| **Indore** | IT, fintech, cleanest city advantage | Strong coworking growth |
| **Lucknow** | IT parks, government tech | Improving connectivity |
| **Coimbatore** | Manufacturing-tech, SaaS | Fastest-growing hiring market |
| **Kochi** | IT (Infopark, SmartCity) | Strong infra |
| **Ahmedabad** | Pharma, FMCG, textile-tech | Growing startup scene |
| **Chandigarh** | IT, education-tech | Quality of life advantage |

### Coworking Growth
- India coworking market: $271.7M (2024) -> $829.2M by 2033 (13.2% CAGR)
- 30-40% increase in coworking demand in Tier 2/3 cities post-pandemic

### Challenges
- Broadband consistency uneven in smaller towns
- Limited networking/community events
- Fewer in-person collaboration opportunities
- Career growth perception bias ("out of sight, out of mind")

### Reqruit Opportunity
- **City Comparison Tool**: Compare cities by cost of living, salary, WFH friendliness
- **Remote Job Filter**: Specifically tag "truly remote" vs "hybrid" vs "office"
- **Coworking Space Finder**: Integrated directory for Tier 2/3 cities
- **Salary Arbitrage Calculator**: Tier 1 salary + Tier 2/3 cost of living = savings

---

## 16. CTC Calculator Tool

### Components to Model

**Income Components**:
- Basic Salary (40-50% of CTC)
- HRA (40-50% of Basic, depends on city: metro vs non-metro)
- Special Allowance (balancing figure)
- LTA, Conveyance, Medical allowances
- Variable Pay / Bonus

**Deductions**:
- Employee PF: 12% of Basic (up to 15,000 basic or full basic)
- Professional Tax: Varies by state (Rs 200/month in most states)
- Income Tax: Old vs New regime calculation
- ESI: If salary < 21,000/month

**Employer Costs (in CTC but not in salary)**:
- Employer PF: 12% of Basic
- Gratuity: 4.81% of Basic (paid after 5 years)
- Group Insurance premiums

### Tax Regime Comparison (FY 2025-26)

**New Tax Regime** (default):
- 0-4L: Nil
- 4-8L: 5%
- 8-12L: 10%
- 12-16L: 15%
- 16-20L: 20%
- 20-24L: 25%
- >24L: 30%
- Standard deduction: Rs 75,000
- Effective: Tax-free up to 12.75L for salaried

**Old Tax Regime**:
- Deductions: 80C (1.5L), 80D (health insurance), HRA, home loan interest
- Better for those with high deductions (home loan + HRA + insurance)

### Existing Tools to Study
- ctctoinhand.in
- ctccalc.in
- moneygyaan.com
- cleartax.in salary calculator

### Reqruit Opportunity
- **Offer Comparison Calculator**: Side-by-side CTC breakdown of two offers
- **Take-Home Estimator**: Quick monthly in-hand from CTC
- **Tax Regime Advisor**: Personalized old vs new recommendation
- **"What CTC to Ask For"**: Reverse calculator - desired in-hand -> required CTC

---

## 17. Background Verification (BGV) Process

### Standard Checks in Indian IT

1. **Identity Verification**: Aadhaar authentication, PAN card, Voter ID
2. **Address Verification**: Physical or digital address confirmation
3. **Education Verification**: Degree certificates, university records, CGPA/marks
4. **Employment History**: Previous employer HR verification, dates, designation, reason for exit
5. **Criminal Records**: Police verification, court records
6. **Reference Checks**: Manager/colleague references from previous jobs
7. **Drug Testing**: Some MNCs (rare in Indian IT)
8. **Credit Check**: For BFSI roles

### Common Issues
- **30% of IT resumes contain discrepancies**
- Fake degrees from unrecognized institutions
- Inflated job titles or extended employment durations
- Gaps in employment not disclosed
- Deepfake technology in remote interviews (emerging threat)

### Process Timeline
- Standard: 2-5 working days
- With educational verification: 7-15 days
- Leadership/senior roles: Up to 30 days

### Legal Framework
- Digital Personal Data Protection Act, 2023: Explicit consent required
- IT Act, 2000: Digital consent and data protection protocols
- No centralized criminal database (unlike US)

### Major BGV Providers
- FactSuite, AuthBridge, OnGrid, SpringVerify, IDfy

### Reqruit Opportunity
- **Pre-BGV Self-Audit**: Help candidates verify their own records before BGV
- **Document Organizer**: Store and organize all BGV-required documents
- **Discrepancy Advisor**: Flag potential issues and suggest corrections
- **BGV Status Tracker**: Track verification progress across companies

---

## 18. H1B from India

### Lottery Statistics (2025-2026)

| Metric | FY 2025 | FY 2026 |
|--------|---------|---------|
| Registrations | 343,981 | Reduced (new rules) |
| Selection Rate | 21.8% | 35% |
| Approval Rate | 97% | ~97% |

### Major Changes
- **$100,000 one-time fee** (from September 2025) for new H-1B petitions
- **Wage-weighted lottery**: Higher-paying roles get up to 4x entries
- **Social media screening** (December 2025): Causing visa slot rescheduling

### GCC (Global Capability Centers) as Alternative Pathway
- GCCs in India increasingly seen as long-term hubs
- Companies investing in GCCs instead of H-1B transfers
- 40% surge in Tier-2 cities hosting GCCs
- Roles: AI/ML, cloud architecture, cybersecurity, data engineering

### L1 Visa Transfer
- No lottery, no yearly cap
- Requires 1 year of employment at overseas office
- L1A (managers/executives), L1B (specialized knowledge)
- Stamping slots concentrated in Chennai and Hyderabad

### Reqruit Opportunity
- **H1B Probability Calculator**: Based on wage level, employer, role
- **GCC Job Board**: Specifically for GCC positions in India
- **Immigration Pathway Advisor**: H1B vs L1 vs EB-1/2/3 comparison
- **Visa Interview Prep**: City-specific slot availability and preparation tips
- **"Stay in India" Alternative Finder**: Comparable GCC roles at global pay

---

## 19. City-wise Job Markets

### Detailed City Profiles

**Bangalore (Bengaluru)**
- **Identity**: India's Silicon Valley, tech capital
- **Dominant Sectors**: IT/Software, startups, GCCs, biotech
- **3,000+ IT companies** including Google, Amazon, Microsoft, Flipkart
- **Salary Premium**: Engineering leaders earn 15-20% more than other metros; AI/ML specialists 12-18% above national average
- **Cost**: High rent (Koramangala/HSR: 25-40K for 2BHK), traffic challenges
- **Growth**: Leading hiring with 3pp growth in 2026

**Mumbai**
- **Identity**: Financial capital
- **Dominant Sectors**: Banking, investment banking, consulting, fintech, media, entertainment
- **Salary**: Highest for finance roles
- **Cost**: Most expensive city (rent in BKC/Lower Parel among highest in Asia)
- **Key Areas**: BKC, Lower Parel, Andheri, Powai

**Hyderabad**
- **Identity**: Emerging tech + pharma hub
- **Dominant Sectors**: IT, pharma, biotech, GCCs
- **Key Players**: Microsoft, Google, Facebook India offices
- **Cost Advantage**: Real estate 20-30% lower than Bangalore
- **Growth**: Co-leading with Bangalore at 3pp growth in 2026
- **Key Areas**: HITEC City, Gachibowli, Madhapur

**Pune**
- **Identity**: Western India's IT capital + auto hub
- **Dominant Sectors**: IT services, automotive, manufacturing, SaaS
- **1,000+ IT companies**
- **Key Areas**: Hinjewadi, Kharadi, Magarpatta
- **Lifestyle**: Moderate cost, good quality of life

**Delhi NCR (Gurugram/Noida/Delhi)**
- **Identity**: Diverse economy, corporate HQs
- **Dominant Sectors**: E-commerce, consulting, FMCG, media, startups
- **Gurugram**: Corporate HQs, MNC offices (Golf Course Road, Cyber City)
- **Noida**: IT sector, BPOs, media (Film City)
- **Growth**: Flat in 2026

**Chennai**
- **Identity**: Manufacturing + IT hub
- **Dominant Sectors**: Automotive, manufacturing, IT services, SaaS (Zoho)
- **Key Areas**: OMR (IT Corridor), Guindy, SIPCOT
- **Cost**: More affordable than Bangalore/Mumbai

### Reqruit Opportunity
- **City Recommender**: Based on skills, salary expectations, cost of living preferences
- **Industry Heat Map**: Visual representation of which sectors dominate where
- **Relocation Guide**: Cost of living comparison, housing, commute data
- **City-specific Job Alerts**: Targeted by city + sector combinations

---

## 20. Skills in Demand

### Top Skills (2025-2026)

**Tier 1 - Extreme Demand (3X+ growth in postings)**:
- Generative AI / LLM Engineering
- Prompt Engineering
- AI/ML Engineering
- Cloud Architecture (AWS/Azure/GCP)
- Cybersecurity

**Tier 2 - High Demand**:
- Data Engineering (PySpark, Spark SQL, Databricks, Snowflake)
- Full-Stack Development (React/Next.js + Node.js/Python)
- DevOps/Platform Engineering
- Semiconductor Design
- Data Science

**Tier 3 - Steady Demand**:
- Product Management
- UI/UX Design
- Digital Marketing
- Mobile Development (React Native, Flutter)
- QA Automation

### Talent Gap
- For every 10 open GenAI roles, only 1 qualified engineer available
- AI talent gap expected to reach 53% by 2026
- Cloud computing: 55-60% demand-supply mismatch
- India needs 1 million skilled AI professionals by 2026

### Salary Ranges for Hot Skills
- Senior GenAI/AI roles: Up to Rs 60 LPA
- Cloud architects: 30-50 LPA
- Data engineers (5+ yrs): 20-35 LPA
- Full-stack (3-5 yrs): 12-25 LPA

### Reqruit Opportunity
- **Skill Gap Analyzer**: Compare user skills vs market demand
- **Upskilling Roadmap**: Personalized learning paths for in-demand skills
- **Skill-to-Salary Mapper**: How much each skill adds to earning potential
- **"Future-Proof" Score**: Rate user's skill set against 2-3 year market trends

---

## 21. Salary Negotiation Culture

### Indian Negotiation Patterns

**Standard Appraisal Hikes**:
- Average annual increment: ~9.8% for FY 2026-27
- IT/Consulting/Startups: 11%+
- Non-tech sectors: 6-8%

**Job Switch Hikes**:
| Switch Type | Expected Hike |
|-------------|--------------|
| IT Services -> IT Services | 20-35% |
| IT Services -> Product Company | 40-100% |
| Same sector lateral | 25-40% |
| Niche skills (AI/Cloud) | 50-100%+ |

### Common Negotiation Tactics (HR Side)
1. **"What's your current CTC?"** - Anchor salary to current, not market rate
2. **Lowballing**: Initial offer 15-20% below budget
3. **"Budget is fixed"**: Often negotiable, especially for strong candidates
4. **Variable inflation**: High variable % to show attractive CTC but lower fixed
5. **"We'll review in 6 months"**: Promise of early review rarely materializes

### What Candidates Should Do
- Research market rates on AmbitionBox/levels.fyi before negotiating
- Have 2-3 competing offers for leverage
- Negotiate on fixed pay, not CTC
- Ask for joining bonus instead of higher CTC if facing resistance
- Get everything in writing

### Reqruit Opportunity
- **Negotiation Coach**: AI-powered salary negotiation preparation
- **Counter-Offer Generator**: Suggest counter-offer amount and justification
- **Market Rate Evidence Pack**: Compile salary data to support negotiation
- **"What to Say" Scripts**: Scenario-based negotiation conversation guides
- **Offer Evaluation Checklist**: Beyond just CTC (growth, learning, culture, WLB)

---

## 22. Referral Culture

### How Referrals Dominate Indian Hiring
- **21% of all hires** come through referrals (highest single channel)
- **40% of all hires** come through referral programs (with only 7% of applicants)
- Referred candidates: 2X faster to hire (14-21 days vs 30-45 days)
- 46% more likely to respond to messages if connected to someone at the company
- 30-40% lower hiring costs vs job boards

### Indian Referral Bonus Structure
- Junior roles: Rs 5,000-15,000
- Mid-level: Rs 15,000-30,000
- Senior/niche: Rs 30,000-50,000+
- Some companies offer up to 1L for critical roles

### Referral Platforms in India
- **LinkedIn**: Primary professional networking for referrals
- **Call For Referral**: India-specific referral platform
- **Refer.me**: Referral networking
- **Company internal portals**: Most large IT firms have dedicated referral portals

### The Referral Problem
- Creates echo chambers (similar backgrounds get referred)
- Disadvantages first-generation professionals without industry networks
- Can lead to nepotism in smaller companies
- "Cold referrals" (referring strangers for bonus) dilute quality

### Reqruit Opportunity
- **Referral Network Builder**: Help users build connections at target companies
- **"Ask for Referral" Templates**: Cold outreach messages that work
- **Referral Match**: Connect job seekers with employees at target companies willing to refer
- **Referral Tracker**: Track referral status across multiple companies
- **Network Gap Analyzer**: Identify which target companies user lacks connections at

---

## 23. Contract & Temp Staffing

### Market Leaders

| Company | Specialty | Scale |
|---------|----------|-------|
| **TeamLease** | Pioneer in temp staffing, compliance-first | 3,500+ clients, 28 states |
| **Quess Corp** | Largest staffing firm in India | 500K+ associates |
| **Randstad India** | AI-powered matching (90% accuracy) | Global network |
| **ManpowerGroup India** | Executive search + staffing | Multi-sector |
| **Adecco India** | Global staffing | IT and manufacturing |

### Contract Staffing Models

1. **Fixed-Term Contract**: 6-12 months, specific project
2. **Contract-to-Hire (C2H)**: 3-6 month trial, convert to permanent
3. **Temp Staffing**: Daily/weekly/monthly, variable demand
4. **Staff Augmentation**: Supplementing existing team
5. **Managed Services**: Outsourced function management

### Industry Trends (2025-26)
- AI/Cloud/Cybersecurity: 15-20% increase in contract hiring intent
- Niche roles: Up to 35% increase
- Contract roles growing faster than permanent in IT sector
- Companies using contract-to-hire to reduce mis-hire risk

### Compliance Landscape
- EPFO regulations tightening
- Professional tax obligations
- Labour codes requiring better contract worker protections
- TeamLease's "zero-leakage" compliance framework is industry benchmark

### Reqruit Opportunity
- **Contract vs Permanent Advisor**: Compare financial outcomes over 1-3 years
- **Contract Rate Calculator**: Market rates for contract roles by skill/city
- **C2H Conversion Tracker**: Track contract-to-hire conversion rates by company
- **Compliance Checker**: Ensure contract terms meet labour law requirements
- **Benefits Gap Analysis**: What contract workers miss vs permanent employees

---

## Cross-Cutting Reqruit Product Recommendations

### Must-Build Features (High Impact, Unique to India)

1. **CTC Decoder + Offer Comparator** - Every Indian job seeker needs this
2. **Ghost Job Detector** - Address the #1 frustration
3. **Scam Alert System** - Trust differentiator
4. **Notice Period Optimizer** - Solve the systemic mismatch
5. **Salary Intelligence Engine** - Aggregate AmbitionBox + Glassdoor + levels.fyi
6. **Referral Network Builder** - Democratize access to referrals
7. **Resume Format Switcher** - Indian biodata / Modern / US format

### India-Specific Data Models to Build

- CTC structure parser (extract components from offer letters)
- Notice period predictor (by company/industry)
- Salary range estimator (by role/city/experience/company-type)
- Company type classifier (service/product/startup/GCC/government)
- Job posting authenticity scorer
- Skill demand forecaster

### Monetization Angles

- **B2C Premium**: CTC calculator, salary negotiation coach, resume builder
- **B2B (Recruiters)**: Verified candidate profiles, notice period data, market intelligence
- **B2B (Companies)**: Salary benchmarking reports, hiring analytics
- **Partnerships**: Integration with AmbitionBox, job boards, staffing companies

---

*Research compiled: March 2026*
*Data sources: Web research across 60+ sources*
