# Global Job Market Universality Research for Reqruit

**Date**: 2026-03-14
**Purpose**: Comprehensive research on making Reqruit a globally universal AI job hunting assistant

---

## Table of Contents

1. [Regional Job Markets & APIs](#1-regional-job-markets--apis)
2. [Non-Tech Sector Platforms](#2-non-tech-sector-platforms)
3. [User Profile Archetypes](#3-user-profile-archetypes)
4. [Localization Requirements](#4-localization-requirements)
5. [Compensation Structure Normalization](#5-compensation-structure-normalization)
6. [Legal & Visa Pathways](#6-legal--visa-pathways)
7. [Architecture Recommendations](#7-architecture-recommendations)

---

## 1. Regional Job Markets & APIs

### 1.1 Global Job Aggregator APIs (Start Here)

These provide the fastest path to global coverage without individual board integrations:

| API | Coverage | Access | Notes |
|-----|----------|--------|-------|
| **JSearch (RapidAPI)** | Global (Google for Jobs, LinkedIn, Indeed, Glassdoor, ZipRecruiter) | Freemium via RapidAPI | #1 recommended starting point. 500 results/query, 30+ data points per listing |
| **Adzuna API** | 16+ countries (US, UK, AU, CA, DE, FR, IN, BR, etc.) | Free tier available at developer.adzuna.com | Real-time posts, historical data, salary statistics, standardized titles |
| **Reed API** | UK-focused | Free at reed.co.uk/developers | UK job search and details API |
| **EURES** | 27 EU countries + EEA | Scraper APIs via Apify; no official public REST API | 2M+ job posts across Europe |
| **LinkedIn Job Posting API** | Global | Restricted: requires LinkedIn Talent Solutions Partner status (<10% approval rate, 3-6 month process). AWLI closed to new partners Oct 2025 | Do NOT rely on this as primary source |

**Recommendation**: Start with JSearch + Adzuna for immediate global coverage. These two APIs together cover most major markets.

### 1.2 India

India is a critical market with unique platforms beyond global aggregators.

| Platform | Focus | API Access | Scale |
|----------|-------|------------|-------|
| **Naukri.com** (InfoEdge) | White-collar, all sectors | Enterprise/partner API only. Requires commercial agreement. ATS vendors get integration support via dedicated integration manager | 100K+ active listings |
| **Apna** | Blue-collar + entry-level white-collar | No public API. Employer ATS integration, CSV export, WhatsApp alerts. Built on Google Cloud (BigQuery, Vertex AI, Kubernetes) | 190M+ users, 70+ professional communities (carpenters, electricians, delivery) |
| **Instahyre** | Tech hiring (curated) | No public API. SmartRecruiters marketplace integration exists | 10,000+ companies (Google, Amazon, Flipkart, Microsoft) |
| **LinkedIn India** | Professional/tech | Same restrictions as global LinkedIn API | Major player for white-collar |
| **Indeed India** | Cross-sector | Via JSearch aggregation | Broad coverage |

**India-specific hiring patterns**:
- CTC (Cost to Company) is the standard compensation metric, not base salary
- Notice periods are commonly 60-90 days (vs 2 weeks in US)
- Campus hiring seasons (Jan-Apr) are a major recruitment channel
- Regional language job posts increasingly important (Hindi, Tamil, Telugu, Kannada, Bengali)
- WhatsApp is a primary communication channel for blue-collar hiring

### 1.3 Brazil / Latin America

| Platform | Coverage | API Access | Notes |
|----------|----------|------------|-------|
| **Catho** | Brazil | No public API; ATS integrations available | 70% of Brazil's top 100 companies use it. 17M+ registered candidates |
| **InfoJobs Brasil** | Brazil | No public API | 23M monthly visits, 16M registered candidates. Owned by Redarbor/Adevinta |
| **Computrabajo** | LATAM-wide (20+ countries) | No public API | Owned by Redarbor. Dominant in Spanish-speaking LATAM |
| **Vagas.com.br** | Brazil | Unclear | Major Brazilian portal |
| **Indeed LATAM** | Regional | Via JSearch/Adzuna | Growing presence |

**LATAM hiring patterns**:
- CLT (Consolidacao das Leis do Trabalho) employment law governs Brazil: 13th salary, FGTS, vacation bonus mandatory
- Portuguese required for Brazil, Spanish for rest of LATAM
- "Pretensao salarial" (salary expectation) commonly requested upfront
- Remote work (home office) regulatory framework established in Brazil post-COVID
- Redarbor consolidation means potential future unified API across Computrabajo + InfoJobs

### 1.4 Europe

| Platform | Coverage | API Access | Notes |
|----------|----------|------------|-------|
| **EURES** | EU/EEA-wide | Scraping via Apify; no official REST API. Data from national PES systems | 2M+ cross-border listings. Free public portal |
| **StepStone** | Germany, Benelux, Central Europe | ATS partner integrations | AI-powered matching. Part of Axel Springer |
| **XING (now onlyfy)** | DACH region (DE/AT/CH) | Limited API for partners | Dominant in German-speaking markets |
| **Arbetsformedlingen** | Sweden | Public data available | Swedish PES |
| **Pole Emploi / France Travail** | France | API available at emploi-store-dev.fr | French PES with developer portal |
| **Indeed Europe** | Pan-European | Via JSearch/Adzuna | Broad coverage |
| **Adzuna** | UK, DE, FR, NL, AT, etc. | developer.adzuna.com | Best API option for European coverage |

**European hiring patterns**:
- GDPR compliance is mandatory for any data handling
- Works councils and employee representation requirements vary by country
- Notice periods: 1-3 months standard (Germany up to 7 months for long tenure)
- Collective bargaining agreements (Tarifvertrage in Germany) set minimum pay scales
- Right to disconnect laws in France, Spain, Portugal
- EU Blue Card pathway for non-EU tech workers

### 1.5 Middle East / Gulf

| Platform | Coverage | API Access | Notes |
|----------|----------|------------|-------|
| **Bayt.com** | Pan-Gulf + MENA | API/XML feeds available (confirmed via WhiteCarrot ATS integration) | 44M professionals, 40K+ employers. Founded 2000 |
| **GulfTalent** | Gulf region | API/XML feeds available | 9M+ professionals, 7,400+ active jobs |
| **Naukrigulf** | Gulf (Indian diaspora focus) | Partner API (same parent as Naukri.com - InfoEdge) | Strong for Indian expat job seekers |
| **LinkedIn MENA** | Professional | Same restrictions as global | Growing rapidly |

**Gulf hiring patterns**:
- Kafala (sponsorship) system: employer sponsors worker's visa and residency
- Tax-free salaries in UAE, Qatar, Bahrain, Kuwait (but Saudi introducing VAT/fees)
- Housing allowance, transport allowance, annual flights home are standard benefits
- Nationalization quotas: Saudization (Nitaqat), Emiratization mandate local hiring percentages
- Medical fitness tests mandatory for work permits
- Friday-Saturday weekend (some shifting to Saturday-Sunday)

### 1.6 Southeast Asia

| Platform | Coverage | API Access | Notes |
|----------|----------|------------|-------|
| **JobStreet** (SEEK-owned) | MY, PH, SG, ID | Unified under SEEK platform. Data extraction APIs via Apify | 36M active talent profiles, 240K+ jobs |
| **JobsDB** (SEEK-owned) | HK, TH | Unified with JobStreet under SEEK | Scraper APIs available |
| **9cv9** | SEA-wide | Job posting API available | Growing platform |
| **Indeed SEA** | Regional | Via JSearch | Broad coverage |

**SEA hiring patterns**:
- High mobile-first usage (especially Philippines, Indonesia)
- Contract/project-based work common
- Overseas worker remittance integration important (Philippines OFW)
- Bahasa Indonesia/Malay, Thai, Vietnamese, Filipino language support needed
- Singapore has strict foreign worker quotas (EP, S Pass)

### 1.7 Africa

| Platform | Coverage | API Access | Notes |
|----------|----------|------------|-------|
| **Jobberman** | West Africa (Nigeria, Ghana, Kenya) | No public API confirmed | Part of ROAM (Ringier One Africa Media) |
| **BrighterMonday** | East Africa (Kenya, Tanzania, Uganda) | No public API confirmed | Same parent as Jobberman (ROAM) |
| **Fuzu** | Pan-African | No public API confirmed | 2.5M+ users, AI-driven matching. Career dev + job matching |
| **LinkedIn Africa** | Professional | Same restrictions as global | Growing tech scene (Nigeria, Kenya, South Africa) |

**African hiring patterns**:
- Mobile-first/mobile-only users dominant
- USSD/SMS-based job matching still relevant in some markets
- Informal economy is massive (80%+ in many countries)
- Language: English (Nigeria, Kenya, Ghana), French (Francophone Africa), Arabic (North Africa), Portuguese (Mozambique, Angola)
- Payment: mobile money (M-Pesa) more common than bank transfers
- Youth bulge: median age ~19 across continent

---

## 2. Non-Tech Sector Platforms

### 2.1 Blue-Collar / Gig Economy

| Platform | Focus | Markets | API |
|----------|-------|---------|-----|
| **Apna** | Blue-collar + entry-level | India | No public API. Employer tools only |
| **TaskRabbit** | Skilled home services | US, UK, Canada, select EU | Developer portal at developer.taskrabbit.com. "Delivery by Dolly" API live, skilled services API "coming soon" |
| **Skillit** | Construction trades | US | 190K+ vetted craft workers. Electricians, welders, plumbers, carpenters |
| **BlueRecruit** | Skilled trades | US | Trades workers-employers matching |
| **PeopleReady** | Construction, energy staffing | US | Enterprise staffing platform |
| **UrbanCompany** (formerly UrbanClap) | Home services | India, UAE, AU | App-based. No public API |

### 2.2 Sports Recruitment

| Platform | Focus | Markets | API |
|----------|-------|---------|-----|
| **TransferRoom** | Professional football (soccer) transfers | Global | Club-to-club platform. Requirements + Pitch Opportunities features. Integrated into Football Manager 26 |
| **Teamworks** | College + pro athlete recruiting | US | Unified recruiting tech stack |
| **ProductiveRecruit** | College athletics (23 sports) | US | 80K+ college coaches database |
| **Haystack Sports** | College recruiting | US | 56K+ college coaches |
| **Catapult** | Performance + recruiting | Global | Wearable-integrated recruiting |

### 2.3 Creative Industries

| Platform | Focus | Markets | Notes |
|----------|-------|---------|-------|
| **Behance** (Adobe) | Design, illustration, photography | Global | Job posting: $399/listing. Portfolio-based matching |
| **Dribbble** | UI/UX design | Global | Job posting: $299/30 days. Designer Search subscription |
| **Mandy** | Film, TV, theatre, creative | Global | Cast, crew, design roles |
| **Curation Zone** | Cross-platform creative talent aggregation | Global | AI-aggregates from Behance, Vimeo, Dribbble, Mandy, etc. Normalizes credential data |
| **Artstation** | Games, film, media, entertainment | Global | Portfolio + job board |

### 2.4 Healthcare

| Platform | Focus | API | Notes |
|----------|-------|-----|-------|
| **SeekOut Healthcare** | Doctors, nurses, allied health | ATS integrations | 31M+ healthcare profiles |
| **iCIMS** | Full healthcare hiring | API available | Market-leading ATS for healthcare |
| **hireEZ** | Clinical recruitment | API available | AI-powered healthcare sourcing |
| **Paradox (Olivia)** | Healthcare conversational AI hiring | API available | AI chatbot for high-volume healthcare hiring |
| **symplr** | Healthcare ATS + credentialing | API available | Compliance-focused |

**Healthcare-specific requirements**:
- License verification APIs (state/country specific)
- Credential management and compliance tracking (HIPAA in US)
- Shift-based scheduling integration
- Continuing education tracking
- Background check integrations (AuthBridge, IDfy in India)

### 2.5 Trades / Skilled Labor

| Platform | Focus | Markets |
|----------|-------|---------|
| **Skillit** | Construction (electricians, welders, plumbers, carpenters, heavy equipment) | US |
| **BlueRecruit** | General trades | US |
| **iHireConstruction** | Construction management + trades | US |
| **Tradesmen International** | Staffing for trades | US |
| **FieldEngineer** | Telecom field engineers | Global |

---

## 3. User Profile Archetypes

### 3.1 Unqualified / Daily Wage Workers

**Characteristics**:
- Often no formal resume or digital presence
- Mobile-only (often feature phones, not smartphones)
- Prefer voice/vernacular language interfaces
- Need hyperlocal job matching (within walking/transit distance)
- Cash or mobile money payment preference
- No formal email address

**Platforms serving this segment**:
- India: Apna (70+ communities), MGNREGA (govt guaranteed 125 days/year employment for rural workers)
- Global: TaskRabbit, daily wage worker platforms
- Africa: Informal job matching via WhatsApp groups, M-Pesa-integrated platforms

**Reqruit implications**:
- WhatsApp/SMS-based interface option (not just web/app)
- Voice-based job search in local languages
- Simplified profile: name, phone, location, skills (checkboxes), availability
- No resume upload required -- skills self-declaration + verification badges
- Geolocation-based matching with radius filter
- Support for daily/weekly pay cycle tracking

### 3.2 International Visa Seekers

**Characteristics**:
- Typically skilled workers seeking employment in a foreign country
- Need visa sponsorship information prominently displayed
- Want salary comparisons adjusted for PPP and cost of living
- Interested in relocation packages, housing support
- Need credential/degree equivalency information

**Common pathways**:
- India -> US (H-1B), India -> Gulf (work permit), India -> Canada (Express Entry)
- LATAM -> US (H-1B, TN for Mexico/Canada), LATAM -> Europe (EU Blue Card)
- Africa -> Gulf, Africa -> Europe
- SEA -> Gulf, SEA -> Singapore/AU/NZ

**Reqruit implications**:
- "Visa sponsorship" filter on every job search
- Visa pathway recommender based on profile (nationality, skills, experience)
- Salary comparison with PPP adjustment
- Relocation cost estimator
- Credential equivalency checker (WES, ENIC-NARIC databases)
- Timeline estimator for visa processing

### 3.3 Remote / Cross-Border Workers

**Characteristics**:
- Work from their home country for foreign employers
- Need to understand tax implications, compliance
- Want to be paid in local currency or USD/EUR
- Need time zone compatibility matching
- May use EOR (Employer of Record) services

**Platforms enabling this**:
- **Deel**: 150+ countries, 120+ currencies, crypto payments, immigration support in 25+ countries
- **Remote.com**: 200+ countries, ISO27001 certified, 100% owned-entity model
- **Oyster HR**: Hybrid model for global reach
- **HireGlobal by Toptal**: Launched 2025, built on Toptal's 12+ year talent network

**Reqruit implications**:
- Remote work filter with time zone overlap calculator
- EOR/contractor status indicator on jobs
- Multi-currency salary display
- Tax jurisdiction advisory (not legal advice, but informational)
- "Work from anywhere" vs "remote but must be in country X" distinction

---

## 4. Localization Requirements

### 4.1 Multilingual AI Support

**Priority languages** (by market size and demand):

| Tier | Languages | Markets |
|------|-----------|---------|
| **Tier 1** | English, Hindi, Spanish, Portuguese, Arabic | US/UK/AU/IN, India, LATAM, Brazil, MENA |
| **Tier 2** | French, German, Mandarin, Japanese, Bahasa Indonesia/Malay | France/Africa, DACH, China, Japan, SEA |
| **Tier 3** | Tamil, Telugu, Kannada, Bengali, Thai, Vietnamese, Korean, Turkish, Swahili | Indian states, SEA, Korea, Turkey, East Africa |

**Technical approach**:
- Modern LLMs (GPT-4, Claude, Gemini) natively support 50+ languages
- For Reqruit's LangGraph agents: set system prompt language dynamically based on user locale
- Google Dialogflow CX: pre-trained multilingual models with real-time language switching
- Hinglish (Hindi + English code-mixing) is critical for Indian market -- models now handle this well
- Arabic: RTL rendering, complex morphology. Needs specific UI consideration
- Use language detection on first message to auto-switch

**NLP-specific challenges**:
- Job title normalization across languages ("Software Engineer" = "Ingeniero de Software" = "Engenheiro de Software")
- Resume parsing in non-Latin scripts
- Skill extraction from vernacular descriptions
- Salary parsing with different number formats (1,00,000 in India vs 100,000 in US)

### 4.2 Salary & Compensation APIs

| API/Tool | Data | Cost | Notes |
|----------|------|------|-------|
| **Levels.fyi API** | Tech salaries by company/level/role | API access available. LLM-friendly data at /companies/[name]/salaries.md | Best for tech sector. Verified data (W2, offer letters) |
| **Glassdoor API** | Broad salary data | Developer program | Wider industry coverage than Levels.fyi |
| **PayScale** | Compensation data by role/region | Enterprise API | Traditional comp data provider |
| **World Bank PPP Data** | Purchasing power parity conversion factors | Free | 196 countries. Essential for cross-border salary comparison |
| **PPPCalculator.info** | PPP salary conversion | Free web tool (no API confirmed) | Uses World Bank ICP data |

### 4.3 Currency Handling APIs

| API | Currencies | Free Tier | Update Frequency |
|-----|------------|-----------|------------------|
| **Frankfurter** | 30+ (ECB data) | Fully free, open-source | Daily |
| **ExchangeRate-API** | 161 | 1,500 requests/month free | Daily |
| **Open Exchange Rates** | 170+ | 1,000 requests/month free | Hourly (paid) |
| **Fixer.io** | 170 | 100 requests/month free | Hourly |
| **Currencylayer** | 168 | 100 requests/month free | Hourly |
| **Freecurrencyapi.com** | 32 | 5,000 requests/month free | Daily |

**Recommendation**: Use Frankfurter (free, open-source, reliable ECB data) for display currency conversion. Cache exchange rates daily. Store all monetary values in a canonical form (amount + currency code ISO 4217).

### 4.4 Regional Job Board API Summary

| Region | Best API Path | Fallback |
|--------|--------------|----------|
| **US/Canada** | JSearch + Adzuna | Direct Indeed/LinkedIn scraping (risky) |
| **UK** | Reed API + Adzuna UK | JSearch |
| **Europe** | Adzuna (multi-country) | EURES scraping, France Travail API |
| **India** | JSearch (Indeed India) | Naukri partner API (if approved) |
| **LATAM** | Adzuna Brazil | JSearch |
| **Gulf/MENA** | Bayt XML feed + GulfTalent feed | JSearch |
| **SEA** | JobStreet/JobsDB scrapers (Apify) | JSearch |
| **Africa** | JSearch | LinkedIn + local platform partnerships |

---

## 5. Compensation Structure Normalization

### 5.1 Compensation Models by Region

| Region | Model | Components | Tax |
|--------|-------|------------|-----|
| **US** | Base Salary + Bonus + Equity (RSU/Options) | Annual base, signing bonus, performance bonus, stock vesting over 4 years | Federal + State income tax |
| **India (CTC)** | Cost to Company | Basic (40-60% of CTC) + HRA + DA + Special Allowance + PF (12%) + Gratuity + Insurance + variable pay. In-hand is ~60-70% of CTC | Income tax slabs + cess |
| **UK** | Annual Salary + Benefits | Base salary, pension contribution (employer min 3%), NI, bonus | PAYE + NI |
| **Germany** | Brutto (Gross) | Base salary, 13th month (common), bonus, company pension | Progressive income tax + solidarity surcharge + church tax |
| **Gulf (UAE/Qatar)** | Monthly Salary + Allowances | Basic salary + housing allowance + transport + annual flight + end-of-service gratuity | Tax-free (mostly) |
| **Brazil (CLT)** | Monthly Salary | Base + 13th salary + vacation bonus (1/3 extra) + FGTS (8%) + transport voucher + meal voucher | INSS + IRRF |
| **Japan** | Annual Salary (Nenshu) | Base + bonus (typically 2-6 months) + overtime | Income tax + residence tax + social insurance |
| **Australia** | Base + Super | Base salary + superannuation (11.5% in 2025) + bonus | PAYG withholding |

### 5.2 Normalization Strategy for Reqruit

```
CompensationNormalized:
  raw_amount: Decimal
  raw_currency: str (ISO 4217)
  raw_structure: str (CTC|BASE|GROSS|TOTAL_COMP)

  # Computed fields
  estimated_annual_gross: Decimal  # Normalized to annual gross
  estimated_annual_net: Decimal    # After estimated taxes
  ppp_adjusted_usd: Decimal        # PPP-adjusted for comparison

  # Breakdown
  base_component: Decimal
  variable_component: Decimal      # Bonus, commission
  equity_component: Decimal        # RSU/ESOP annualized
  benefits_value: Decimal          # Insurance, retirement, allowances

  # Metadata
  pay_frequency: str (MONTHLY|BIWEEKLY|ANNUAL)
  includes_employer_contributions: bool
  region_code: str
```

**Conversion rules**:
- India CTC -> Annual Gross: CTC * 0.85 (approximate, excludes employer PF/gratuity)
- India CTC -> Take-home: CTC * 0.65-0.70 (depends on tax slab)
- US Total Comp -> Base: varies widely (base might be 50-80% of TC in tech)
- Gulf salary -> Equivalent taxed salary: multiply by 0.7-0.75 for comparison with taxed jurisdictions
- Brazil CLT -> Annual: monthly * 13.33 (13th salary + vacation bonus)

### 5.3 Indian Number System Support

India uses the lakh/crore system:
- 1 lakh = 1,00,000 (100,000)
- 1 crore = 1,00,00,000 (10,000,000)
- "12 LPA" = 12 Lakhs Per Annum = INR 1,200,000/year

Reqruit must parse and display:
- "12 LPA", "12L", "12 lakhs per annum"
- "1.2 Cr", "1.2 crore"
- Number formatting: 1,00,000 (Indian) vs 100,000 (Western)

---

## 6. Legal & Visa Pathways

### 6.1 US Pathways (from India and globally)

| Visa | Type | Requirements | Timeline | Notes |
|------|------|-------------|----------|-------|
| **H-1B** | Specialty occupation | Bachelor's degree, employer sponsorship, lottery selection | Lottery in March, start Oct 1. Process: 3-6 months after selection | Cap: 85,000/year. Final rule Jan 2025 updated Form I-129. Data available via USCIS H-1B Employer Data Hub and DOL LCA disclosure data |
| **L-1A** | Intra-company transfer (executive/manager) | 1+ year with company abroad, managerial role | 2-6 months | Up to 7 years total stay |
| **L-1B** | Intra-company transfer (specialized knowledge) | 1+ year with company, specialized knowledge | 2-6 months | Up to 5 years total stay |
| **O-1** | Extraordinary ability | Demonstrated extraordinary achievement | 2-4 months | No cap, no lottery |
| **EB-1C** | Green card via L-1A | Multinational manager/executive | 1-3 years | Direct path to permanent residency |

**Data sources for Reqruit**:
- USCIS H-1B Employer Data Hub (official, public)
- h1bdata.info: millions of LCA salary records, searchable
- h1bgrader.com: sponsor grades, approval rates, salary data
- DOL LCA disclosure files (bulk download, public domain)

### 6.2 EU Blue Card

| Aspect | Details |
|--------|---------|
| **Eligibility** | Higher education qualification OR 5+ years relevant professional experience |
| **Salary threshold** | >= 1.5x average gross annual salary in the member state |
| **Contract** | Minimum 6-month employment contract required |
| **Countries** | 25 of 27 EU states (Denmark and Ireland opted out) |
| **Duration** | Up to 4 years, renewable |
| **Fast-track PR** | Germany: permanent settlement in 21 months with B1 German |
| **Family** | Spouse gets immediate unrestricted work permit |
| **Portability** | After 12 months, can move to another EU country |

**Software developers** are among the most common EU Blue Card applicants.

### 6.3 Gulf Work Permits

| Country | Sponsor System | Process Time | Key Requirements |
|---------|---------------|-------------|------------------|
| **UAE** | Employer-sponsored via MOHRE | 2-4 weeks | Job offer, medical fitness, security clearance, educational certificates attested |
| **Saudi Arabia** | Employer-sponsored via MOHR | 2-4 weeks | Visa Authorization Number from MoFA, medical screening, skill-based classification (mandatory since July 2025) |
| **Qatar** | Employer-sponsored | 2-4 weeks | Medical, security, educational verification |
| **Kuwait** | Employer-sponsored | 4-8 weeks | Medical, educational verification |
| **Bahrain** | Employer-sponsored via LMRA | 2-3 weeks | Flexible labor market system |
| **Oman** | Employer-sponsored | 3-6 weeks | Medical, educational verification |

**Common Gulf features**:
- All operate under kafala/sponsorship model (reforms ongoing in some states)
- Nationalization quotas affect hiring probability
- End-of-service gratuity (typically 21 days' salary per year for first 5 years, 30 days after)
- Standard packages include: housing allowance, transport, annual flights, medical insurance

### 6.4 Intra-Company Transfers (Global)

| Country | Visa Type | Min Tenure | Max Stay | Salary Threshold |
|---------|-----------|-----------|----------|-----------------|
| **US** | L-1A/L-1B | 1 year in past 3 years | 7 years (L-1A) / 5 years (L-1B) | Prevailing wage |
| **UK** | Senior/Specialist Worker (Global Business Mobility) | 12 months | 5 years (9 for high earners) | GBP 52,500 or going rate (from July 2025) |
| **Canada** | ICT Work Permit (LMIA-exempt) | Varies | Varies | None specified |
| **EU** | ICT Directive | 3-12 months depending on member state | 3 years (managers) / 1 year (trainees) | National thresholds |
| **Japan** | Intra-company Transferee | 1+ year | 1-5 years | Company must demonstrate need |

### 6.5 Visa Pathway Recommender Data Model

```
VisaPathway:
  source_country: str
  target_country: str
  visa_type: str
  eligibility_criteria:
    min_experience_years: int
    education_level: str  # HIGH_SCHOOL, BACHELORS, MASTERS, PHD
    required_skills: list[str]
    salary_threshold: MonetaryAmount
    language_requirements: list[LanguageRequirement]
  process:
    steps: list[ProcessStep]
    estimated_timeline_days: int
    estimated_cost: MonetaryAmount
    success_rate_percent: float  # Where data available
  benefits:
    family_sponsorship: bool
    path_to_pr: bool
    pr_timeline_months: int
    work_rights_for_spouse: bool
```

---

## 7. Architecture Recommendations

### 7.1 Data Model Extensions

**Job Listing model additions**:
```python
class JobListing(Document):
    # ... existing fields ...

    # Globalization fields
    country_code: str                    # ISO 3166-1 alpha-2
    region_code: Optional[str]           # e.g., "IN-KA" for Karnataka
    source_board: str                    # e.g., "jsearch", "adzuna", "naukri"
    source_board_id: str                 # Original ID on source platform

    # Compensation
    compensation: CompensationInfo

    # Visa/work authorization
    visa_sponsorship: Optional[bool]
    work_authorization_required: list[str]  # e.g., ["US_CITIZEN", "GREEN_CARD", "H1B"]
    remote_policy: str                   # "ONSITE", "HYBRID", "REMOTE_LOCAL", "REMOTE_GLOBAL"

    # Localization
    language: str                        # ISO 639-1 language of the posting
    required_languages: list[str]        # Languages required for the role

class CompensationInfo(BaseModel):
    min_amount: Optional[Decimal]
    max_amount: Optional[Decimal]
    currency: str                        # ISO 4217
    period: str                          # "HOURLY", "DAILY", "MONTHLY", "ANNUAL"
    structure: str                       # "BASE", "CTC", "TOTAL_COMP", "GROSS"
    includes: list[str]                  # ["BASE", "BONUS", "EQUITY", "PF", "INSURANCE"]
    display_format: str                  # "12 LPA", "$150,000", "AED 25,000/month"
    ppp_usd_equivalent: Optional[Decimal]
```

**User Profile model additions**:
```python
class UserProfile(Document):
    # ... existing fields ...

    # Globalization
    nationality: list[str]               # Can hold dual/multiple
    current_country: str
    work_authorization: dict[str, str]   # {"US": "H1B", "IN": "CITIZEN", "UK": "TIER2"}
    preferred_countries: list[str]
    willing_to_relocate: bool
    remote_preference: str

    # Language
    preferred_language: str              # UI language
    spoken_languages: list[LanguageSkill]

    # Compensation
    expected_compensation: CompensationExpectation
    current_compensation: Optional[CompensationInfo]

class LanguageSkill(BaseModel):
    language: str                        # ISO 639-1
    proficiency: str                     # "NATIVE", "FLUENT", "PROFESSIONAL", "BASIC"

class CompensationExpectation(BaseModel):
    min_acceptable: Decimal
    preferred: Decimal
    currency: str
    structure_preference: str            # "CTC", "BASE", "TOTAL_COMP"
```

### 7.2 Job Board Integration Architecture

```
                    +------------------+
                    |  Job Aggregator  |
                    |    Service       |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +-------v----+  +------v------+
     | JSearch     |  | Adzuna     |  | Regional    |
     | Adapter     |  | Adapter    |  | Adapters    |
     +--------+---+  +-------+----+  +------+------+
              |              |              |
              +--------------+--------------+
                             |
                    +--------v---------+
                    | Normalization     |
                    | Pipeline          |
                    | - Title mapping   |
                    | - Salary parsing  |
                    | - Location geo    |
                    | - Deduplication   |
                    +--------+---------+
                             |
                    +--------v---------+
                    | Weaviate Vector   |
                    | Store + MongoDB   |
                    +------------------+
```

**Adapter interface** (each job board gets one):
```python
class JobBoardAdapter(ABC):
    @abstractmethod
    async def search(self, query: JobSearchQuery) -> list[RawJobListing]: ...

    @abstractmethod
    async def get_details(self, job_id: str) -> RawJobListing: ...

    @abstractmethod
    def normalize(self, raw: RawJobListing) -> JobListing: ...

    @property
    @abstractmethod
    def supported_countries(self) -> list[str]: ...

    @property
    @abstractmethod
    def rate_limits(self) -> RateLimitConfig: ...
```

### 7.3 Compensation Normalization Service

```python
class CompensationNormalizer:
    """Normalizes compensation across regions and structures."""

    async def normalize_to_annual_gross(
        self, amount: Decimal, currency: str,
        structure: str, country: str
    ) -> Decimal:
        """Convert any comp structure to annual gross."""
        ...

    async def ppp_convert(
        self, amount: Decimal,
        from_country: str, to_country: str
    ) -> Decimal:
        """PPP-adjusted conversion for standard of living comparison."""
        ...

    async def exchange_convert(
        self, amount: Decimal,
        from_currency: str, to_currency: str
    ) -> Decimal:
        """Market exchange rate conversion."""
        ...

    async def estimate_take_home(
        self, gross: Decimal, country: str,
        state_region: Optional[str] = None
    ) -> Decimal:
        """Estimate net/take-home pay after taxes."""
        ...

    def parse_indian_salary(self, text: str) -> CompensationInfo:
        """Parse '12 LPA', '1.2 Cr', '50,000/month' etc."""
        ...
```

### 7.4 Visa Pathway Recommender Agent (LangGraph)

```python
# New LangGraph node for visa pathway recommendations
class VisaPathwayAgent:
    """Recommends visa pathways based on user profile and target jobs."""

    async def recommend(
        self, user_profile: UserProfile,
        target_job: JobListing
    ) -> list[VisaPathway]:
        """
        Given a user's nationality, skills, experience and a target job,
        recommend viable visa pathways ranked by:
        1. Probability of success
        2. Processing time
        3. Cost
        4. Long-term benefits (path to PR, family sponsorship)
        """
        ...
```

### 7.5 Phased Implementation Plan

**Phase 1 (MVP Global)**:
- JSearch + Adzuna integration (covers 80% of markets)
- Frankfurter currency API
- English + Hindi language support
- Basic salary display with currency conversion
- Visa sponsorship filter (boolean)

**Phase 2 (Regional Depth)**:
- Reed API (UK), Bayt XML feed (Gulf), France Travail API (France)
- CTC <-> Base salary normalization for India
- PPP salary comparison
- Arabic, Spanish, Portuguese language support
- Gulf work permit information

**Phase 3 (Blue Collar + Specialized)**:
- WhatsApp integration for blue-collar job matching
- TaskRabbit API integration
- Healthcare credential verification
- Visa pathway recommender agent
- H-1B data integration (USCIS + DOL datasets)

**Phase 4 (Full Universality)**:
- Regional job board partnerships (Naukri, Catho, JobStreet)
- Full multilingual support (Tier 1-3 languages)
- Sports/creative industry verticals
- EOR platform integrations (Deel, Remote)
- Mobile money payment tracking (M-Pesa for Africa)
- Voice-based job search for low-literacy users

---

## Sources

### Regional Job Markets
- [Naukri API Integration - Workable](https://help.workable.com/hc/en-us/articles/26298085189271-Integrating-with-Naukri)
- [Naukri API Docs & SDKs](https://apitracker.io/a/naukri)
- [Apna Case Study - Google Cloud](https://cloud.google.com/customers/apna)
- [Apna - Blue Collar Unicorn](https://insidestartups.substack.com/p/apna-jobs-how-does-a-blue-collar)
- [Instahyre - SmartRecruiters Marketplace](https://marketplace.smartrecruiters.com/partners/instahyre)
- [LATAM Tech Job Boards Guide](https://www.linkedin.com/pulse/ultimate-guide-global-tech-job-boards-part-4-latam-region-khomich-088oe)
- [Brazil Job Boards](https://www.manatal.com/blog/tech-job-boards-brazil)
- [Redarbor acquires InfoJobs Brasil](https://www.cuatrecasas.com/en/global/corporate/art/redarbor-consolidates-position-in-latam-by-acquiring-majority-stake-in-infojobs-brasil-1)
- [Bayt.com](https://www.bayt.com/)
- [GulfTalent](https://www.gulftalent.com/)
- [UAE Job Sites 2026](https://www.saviorhire.com/post/best-job-websites-in-uae)
- [SE Asia Job Boards Guide 2026](https://www.hyperworkrecruitment.com/post/the-ultimate-guide-to-southeast-asia-job-boards-2026-edition)
- [JobsDB Scraper API - Apify](https://apify.com/lexis-solutions/jobsdb/api/openapi)
- [HR Tech Platforms in Africa](https://www.breedj.com/which-are-the-hr-tech-platforms-in-africa/)
- [Top Job Boards Africa](https://www.linkedin.com/pulse/top-job-boards-africa-ashton-ngwenya-gkm7e)
- [EURES Portal](https://eures.europa.eu/index_en)
- [EURES Jobs Scraper - Apify](https://apify.com/lexis-solutions/eures-eu-jobs-scraper/api)
- [European Job Search Sites](https://euroinfopedia.com/job-search-websites-for-europe/)

### Job Board APIs
- [Adzuna Developer API](https://developer.adzuna.com/)
- [Adzuna Public API](https://publicapi.dev/adzuna-api)
- [JSearch API on RapidAPI](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
- [JSearch API Details](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch/details)
- [Reed API](https://www.reed.co.uk/developers)
- [LinkedIn API Guide 2026](https://www.outx.ai/blog/linkedin-api-guide)
- [LinkedIn Job Posting API](https://learn.microsoft.com/en-us/linkedin/talent/job-postings/api/overview)
- [TaskRabbit Developer Portal](https://developer.taskrabbit.com/docs/overview)

### Compensation & Currency
- [CTC Calculator India](https://cleartax.in/s/ctc-cost-to-company)
- [Indian Salary Structures 2025](https://quikchex.in/salary-structures-india-need-know-2/)
- [Levels.fyi API Access](https://www.levels.fyi/api-access/)
- [Glassdoor Salaries API](https://www.glassdoor.com/developer/salariesApiActions.htm)
- [PPP Salary Converter](https://pppcalculator.info/)
- [ParityDeals PPP Calculator](https://www.paritydeals.com/ppp-calculator/)
- [Frankfurter Exchange Rate API](https://frankfurter.dev/)
- [ExchangeRate-API](https://www.exchangerate-api.com/)
- [Open Exchange Rates](https://openexchangerates.org/)
- [Currencylayer](https://currencylayer.com/)

### Visa & Immigration
- [USCIS H-1B Employer Data Hub](https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub)
- [H1B Database](https://h1bdata.info/)
- [H1B Grader](https://h1bgrader.com/)
- [EU Blue Card - European Commission](https://home-affairs.ec.europa.eu/policies/migration-and-asylum/eu-immigration-portal/eu-blue-card_en)
- [EU Blue Card Germany Guide](https://www.migrationvisportal.com/2025/10/eu-blue-card-germany-countries-apply-2025-guide.html)
- [Gulf Work Visa Guide](https://terratern.com/blog/work-visa-for-gulf-countries/)
- [UAE Work Visa Process](https://sceaa.org.au/uae-work-visa-process-dec-2025/)
- [Saudi Arabia Work Visa](https://www.globalization-partners.com/globalpedia/saudi-arabia/visa-permits/)
- [Gulf Work Visas Expat Guide 2025-2026](https://careerroutegulf.com/gulf-work-visas/)
- [Intra-Company Transfer Guide](https://www.centuroglobal.com/article/intra-company-transfer/)
- [L-1 Visa Guide](https://www.gozellaw.com/blog/l1-visa-intra-company-transfer-usa)
- [UK Senior/Specialist Worker Visa](https://connaughtlaw.com/senior-or-specialist-worker-visa-complete-guide/)
- [Canada ICT Work Permit](https://cifile.org/immigration-to-canada/intra-company-transfer/)

### Non-Tech Sectors
- [Skillit - Construction Hiring](https://skillit.com/)
- [BlueRecruit](https://bluerecruit.us/)
- [SeekOut Healthcare](https://www.seekout.com/products/healthcare)
- [iCIMS Healthcare](https://www.icims.com/products/industry/hospital-healthcare-recruiting-software/)
- [Curation Zone - Creative Talent](https://www.curationzone.com/articles/curation-zone-streamlines-creative-talent-discovery-for-agencies-and-brands)
- [TransferRoom](https://www.footballmanager.com/fm26/features/powered-transferroom-fm26s-recruitment-revamp)

### Multilingual AI
- [Top Multilingual AI Models 2025](https://local-ai-zone.github.io/guides/best-ai-multilingual-models-ultimate-ranking-2025.html)
- [Multilingual Chatbot Guide 2026](https://quickchat.ai/post/multilingual-chatbots)
- [Building Multilingual Chatbots](https://www.solulab.com/how-to-build-a-multilingual-chatbot/)

### Cross-Border Employment
- [Deel vs Remote vs Oyster Comparison](https://arc.dev/employer-blog/best-eor-services/)
- [Deel](https://www.deel.com/)
- [MGNREGA - India Rural Employment](https://mg-nrega.com/)
- [Daily Wage Worker Platform](https://www.dailywageworker.com/)
