# How to Add Real Government Schemes for AI FOR BHARAT Hackathon

## Why Real Schemes Matter

For a hackathon, **real government schemes** will:
- ✅ Impress judges with actual research
- ✅ Show real-world impact
- ✅ Make your demo more credible
- ✅ Stand out from teams using fake data

## Quick Start: Top 30 Real Schemes (Recommended)

### Step 1: Get the Data

I recommend manually adding these **30 most popular schemes** that cover all major categories:

#### Agriculture (5 schemes)
1. **PM-KISAN** - ₹6000/year to farmers
2. **Kisan Credit Card** - Low-interest loans
3. **PM Fasal Bima Yojana** - Crop insurance
4. **Soil Health Card Scheme** - Free soil testing
5. **PM Kusum Yojana** - Solar pumps for farmers

#### Education (5 schemes)
1. **PM Vidya Lakshmi** - Education loans
2. **National Scholarship Portal** - Scholarships for students
3. **Mid-Day Meal Scheme** - Free meals in schools
4. **Beti Bachao Beti Padhao** - Girl child education
5. **Post Matric Scholarship SC/ST** - Higher education support

#### Health (5 schemes)
1. **Ayushman Bharat (PM-JAY)** - ₹5 lakh health insurance
2. **Janani Suraksha Yojana** - Maternity benefits
3. **PM Suraksha Bima Yojana** - ₹12/year accident insurance
4. **Pradhan Mantri Matru Vandana Yojana** - ₹5000 for pregnant women
5. **Mission Indradhanush** - Free vaccination

#### Housing (3 schemes)
1. **PM Awas Yojana (Gramin)** - ₹1.2 lakh for rural housing
2. **PM Awas Yojana (Urban)** - Affordable urban housing
3. **Credit Linked Subsidy Scheme** - Home loan subsidy

#### Women (3 schemes)
1. **Sukanya Samriddhi Yojana** - Girl child savings
2. **Mahila Shakti Kendra** - Women empowerment
3. **Ujjwala Yojana** - Free LPG connections

#### Employment (4 schemes)
1. **MGNREGA** - 100 days guaranteed work
2. **PM Mudra Yojana** - Business loans up to ₹10 lakh
3. **Stand Up India** - Loans for SC/ST/Women entrepreneurs
4. **Atmanirbhar Bharat Rozgar Yojana** - Employment incentives

#### Senior Citizens (2 schemes)
1. **Indira Gandhi Old Age Pension** - ₹200-500/month
2. **PM Vaya Vandana Yojana** - Pension scheme

#### Financial Inclusion (3 schemes)
1. **PM Jan Dhan Yojana** - Free bank accounts
2. **Atal Pension Yojana** - Pension for unorganized sector
3. **PM Jeevan Jyoti Bima** - ₹330/year life insurance

### Step 2: Data Sources

**Official Government Portals:**
1. **MyScheme.gov.in** - https://www.myscheme.gov.in/
   - Best source, has 200+ schemes
   - Structured data with eligibility, benefits, application process

2. **India.gov.in** - https://www.india.gov.in/my-government/schemes
   - Central government schemes
   - Official information

3. **Ministry Websites:**
   - Agriculture: https://agricoop.gov.in/
   - Education: https://www.education.gov.in/
   - Health: https://www.mohfw.gov.in/

### Step 3: Manual Data Entry Template

Create a file `data/real_schemes_manual.json` with this structure:

```json
[
  {
    "scheme_id": "PM-KISAN-001",
    "scheme_name": "Pradhan Mantri Kisan Samman Nidhi",
    "scheme_name_translations": {
      "hi": "प्रधानमंत्री किसान सम्मान निधि",
      "ta": "பிரதம மந்திரி கிசான் சம்மான் நிதி"
    },
    "description": "Direct income support of ₹6000 per year to all farmer families across India, paid in three equal installments of ₹2000 each.",
    "description_translations": {
      "hi": "भारत भर के सभी किसान परिवारों को प्रति वर्ष ₹6000 की प्रत्यक्ष आय सहायता, तीन समान किस्तों में ₹2000 प्रत्येक।"
    },
    "category": "agriculture",
    "authority": "central",
    "applicable_states": ["ALL"],
    "eligibility_criteria": {
      "occupation": "farmer",
      "land_holding": "any",
      "age_min": 18
    },
    "benefits": "₹6000 per year in three installments of ₹2000 each, directly transferred to bank account",
    "benefits_translations": {
      "hi": "प्रति वर्ष ₹6000 तीन किस्तों में ₹2000 प्रत्येक, सीधे बैंक खाते में स्थानांतरित"
    },
    "application_process": "1. Visit PM-KISAN portal (pmkisan.gov.in)\n2. Click on 'Farmer Corner' > 'New Farmer Registration'\n3. Enter Aadhaar number and mobile number\n4. Fill registration form with land details\n5. Submit documents: Aadhaar, bank account, land records\n6. Verification by local authorities\n7. Amount credited within 30 days",
    "application_process_translations": {
      "hi": "1. PM-KISAN पोर्टल (pmkisan.gov.in) पर जाएं\n2. 'किसान कॉर्नर' > 'नया किसान पंजीकरण' पर क्लिक करें\n3. आधार नंबर और मोबाइल नंबर दर्ज करें"
    },
    "official_url": "https://pmkisan.gov.in/",
    "helpline_numbers": ["1800-180-1551", "011-23381092"],
    "status": "active",
    "start_date": "2019-02-01T00:00:00",
    "end_date": null
  }
]
```

### Step 4: Quick Scraping Script (Advanced)

If you want to automate, here's a simple scraper for MyScheme:

```python
import requests
from bs4 import BeautifulSoup
import json

# Note: This is a simplified example
# MyScheme might require authentication or have rate limits

def scrape_myscheme():
    schemes = []
    
    # Example: Scrape scheme list
    url = "https://www.myscheme.gov.in/schemes"
    
    # Add your scraping logic here
    # Be respectful: add delays, check robots.txt
    
    return schemes

# Better: Use their API if available
# Or manually copy 30 schemes from the website
```

### Step 5: Import Real Schemes

```bash
# After creating your JSON file with real schemes
python scripts/import_schemes.py --file data/real_schemes_manual.json --format json
```

## Hackathon Strategy

### For Demo (Minimum 10 schemes):
Focus on **most popular schemes** that everyone knows:
1. PM-KISAN (farmers love this)
2. Ayushman Bharat (health insurance)
3. PM Awas Yojana (housing)
4. MGNREGA (employment)
5. Beti Bachao Beti Padhao (women)
6. PM Mudra Yojana (business loans)
7. Sukanya Samriddhi (girl child)
8. Ujjwala Yojana (LPG)
9. Jan Dhan Yojana (banking)
10. Mid-Day Meal (education)

### For Impressive Demo (30 schemes):
Add all schemes from the list above.

### For Production-Ready (100+ schemes):
Use web scraping or hire someone on Fiverr ($20-50) to manually enter 100 schemes.

## Time Estimates

| Approach | Time | Schemes | Quality |
|----------|------|---------|---------|
| Manual (Top 10) | 2-3 hours | 10 | ⭐⭐⭐⭐⭐ |
| Manual (Top 30) | 6-8 hours | 30 | ⭐⭐⭐⭐⭐ |
| Scraping | 4-6 hours | 50-100 | ⭐⭐⭐⭐ |
| Fiverr | $20-50 | 100+ | ⭐⭐⭐⭐ |
| Sample data | 5 minutes | 100 | ⭐⭐ |

## My Recommendation for Hackathon

**Do this (4-5 hours total):**

1. **Manually add 15-20 real schemes** (3-4 hours)
   - Focus on most popular ones
   - Get accurate data from official sources
   - Add proper Hindi translations

2. **Fill remaining with sample data** (5 minutes)
   ```bash
   python scripts/generate_sample_schemes.py --count 80
   ```

3. **During demo, showcase the real schemes**
   - "Show me PM-KISAN details"
   - "What is Ayushman Bharat?"
   - "Housing schemes for rural areas"

This gives you:
- ✅ Real data for impressive demo
- ✅ Enough schemes to show variety
- ✅ Manageable time investment
- ✅ Credibility with judges

## Quick Start Template

I'll create a starter file with 5 real schemes for you:

```bash
# I'll create this file with real data
cat > data/starter_real_schemes.json << 'EOF'
[
  {
    "scheme_id": "PM-KISAN-001",
    "scheme_name": "PM-KISAN",
    "description": "₹6000/year direct income support to farmers",
    "category": "agriculture",
    "authority": "central",
    "applicable_states": ["ALL"],
    "eligibility_criteria": {"occupation": "farmer"},
    "benefits": "₹6000 per year in 3 installments",
    "application_process": "Register at pmkisan.gov.in with Aadhaar",
    "official_url": "https://pmkisan.gov.in/",
    "helpline_numbers": ["1800-180-1551"],
    "status": "active"
  }
]
EOF
```

Want me to create a complete file with 20 real schemes for you?
