# MyScheme.gov.in Scraping Guide

## 🎯 Goal
Scrape 10-15 more REAL government schemes from MyScheme.gov.in to add to your database.

## 📋 Recommended Schemes to Scrape

### Agriculture (2 more)
1. **Kisan Credit Card (KCC)**
   - URL: https://www.myscheme.gov.in/schemes/kcc
   - Category: agriculture
   - Authority: central

2. **PM Fasal Bima Yojana (PMFBY)**
   - URL: https://www.myscheme.gov.in/schemes/pmfby
   - Category: agriculture
   - Authority: central

### Education (3 more)
3. **National Scholarship Portal**
   - URL: https://www.myscheme.gov.in/schemes/nsp
   - Category: education
   - Authority: central

4. **Mid-Day Meal Scheme**
   - URL: https://www.myscheme.gov.in/schemes/mdm
   - Category: education
   - Authority: central

5. **PM Vidya Lakshmi**
   - URL: https://www.myscheme.gov.in/schemes/pmvl
   - Category: education
   - Authority: central

### Health (2 more)
6. **Janani Suraksha Yojana (JSY)**
   - URL: https://www.myscheme.gov.in/schemes/jsy
   - Category: health
   - Authority: central

7. **PM Suraksha Bima Yojana (PMSBY)**
   - URL: https://www.myscheme.gov.in/schemes/pmsby
   - Category: health
   - Authority: central

### Housing (1 more)
8. **PM Awas Yojana - Urban (PMAY-U)**
   - URL: https://www.myscheme.gov.in/schemes/pmay-u
   - Category: housing
   - Authority: central

### Women (2 more)
9. **Sukanya Samriddhi Yojana (SSY)**
   - URL: https://www.myscheme.gov.in/schemes/ssy
   - Category: women
   - Authority: central

10. **Ujjwala Yojana**
    - URL: https://www.myscheme.gov.in/schemes/pmuy
    - Category: women
    - Authority: central

### Employment (2 more)
11. **PM Mudra Yojana**
    - URL: https://www.myscheme.gov.in/schemes/pmmy
    - Category: employment
    - Authority: central

12. **Stand Up India**
    - URL: https://www.myscheme.gov.in/schemes/sui
    - Category: employment
    - Authority: central

### Financial (2 more)
13. **PM Jan Dhan Yojana (PMJDY)**
    - URL: https://www.myscheme.gov.in/schemes/pmjdy
    - Category: financial_inclusion
    - Authority: central

14. **Atal Pension Yojana (APY)**
    - URL: https://www.myscheme.gov.in/schemes/apy
    - Category: financial_inclusion
    - Authority: central

## 📝 How to Scrape

### Method 1: Manual Copy-Paste (Easiest)

1. **Visit MyScheme.gov.in**
   - Go to https://www.myscheme.gov.in
   - Search for the scheme name

2. **Copy Information**
   - Scheme name
   - Description
   - Eligibility criteria
   - Benefits
   - Application process
   - Official URL
   - Helpline numbers

3. **Fill Template**
   - Open `data/myscheme_template.json`
   - Copy the template for each scheme
   - Fill in the information
   - Save as `data/myscheme_scraped.json`

### Method 2: Python Script (Advanced)

```python
import requests
from bs4 import BeautifulSoup
import json

def scrape_scheme(url):
    """Scrape scheme details from MyScheme.gov.in"""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract information (adjust selectors based on actual HTML)
    scheme = {
        "scheme_id": "",  # Generate manually
        "scheme_name": soup.find('h1', class_='scheme-title').text.strip(),
        "description": soup.find('div', class_='scheme-description').text.strip(),
        "category": "",  # Determine manually
        "authority": "central",
        "applicable_states": ["ALL"],
        "eligibility_criteria": {},  # Extract from page
        "benefits": soup.find('div', class_='scheme-benefits').text.strip(),
        "application_process": soup.find('div', class_='application-process').text.strip(),
        "official_url": url,
        "helpline_numbers": [],  # Extract from page
        "status": "active",
        "start_date": None,
        "end_date": None
    }
    
    return scheme

# Scrape multiple schemes
schemes = []
urls = [
    "https://www.myscheme.gov.in/schemes/kcc",
    "https://www.myscheme.gov.in/schemes/pmfby",
    # Add more URLs
]

for url in urls:
    scheme = scrape_scheme(url)
    schemes.append(scheme)

# Save to file
with open('data/myscheme_scraped.json', 'w') as f:
    json.dump(schemes, f, indent=2)
```

## 📋 Template Structure

Use this structure for each scheme:

```json
{
  "scheme_id": "UNIQUE-ID",
  "scheme_name": "Full Scheme Name",
  "scheme_name_translations": {
    "hi": "हिंदी नाम"
  },
  "description": "Full description",
  "description_translations": {
    "hi": "हिंदी विवरण"
  },
  "category": "agriculture|education|health|housing|women|senior_citizens|employment|financial_inclusion|social_welfare|skill_development",
  "authority": "central|state",
  "applicable_states": ["ALL"],
  "eligibility_criteria": {
    "age_min": 18,
    "occupation": "any",
    "income_max": 500000
  },
  "benefits": "Benefits description",
  "benefits_translations": {
    "hi": "लाभ विवरण"
  },
  "application_process": "Step by step process",
  "application_process_translations": {
    "hi": "आवेदन प्रक्रिया"
  },
  "official_url": "https://...",
  "helpline_numbers": ["1800-XXX-XXXX"],
  "status": "active",
  "start_date": "2020-01-01T00:00:00",
  "end_date": null
}
```

## 🔑 Key Fields to Get Right

### 1. scheme_id
- Format: `CATEGORY-NAME-001`
- Example: `KCC-001`, `PMFBY-001`, `NSP-001`
- Must be unique

### 2. category
Choose from:
- `agriculture`
- `education`
- `health`
- `housing`
- `women`
- `senior_citizens`
- `employment`
- `financial_inclusion`
- `social_welfare`
- `skill_development`

### 3. authority
- `central` - for national schemes
- `state` - for state-specific schemes

### 4. applicable_states
- `["ALL"]` - for central schemes
- `["MH", "GJ"]` - for state schemes (use state codes)

### 5. eligibility_criteria
Common fields:
```json
{
  "age_min": 18,
  "age_max": 60,
  "occupation": "farmer|student|any",
  "income_max": 500000,
  "gender": "male|female|any",
  "land_holding": "any|small|marginal"
}
```

### 6. status
- `active` - currently running
- `expired` - no longer active
- `upcoming` - not yet started

## 📥 After Scraping

### 1. Validate JSON
```bash
# Check if JSON is valid
python -c "import json; json.load(open('data/myscheme_scraped.json'))"
```

### 2. Import Schemes
```bash
python scripts/import_schemes.py --file data/myscheme_scraped.json --format json
```

### 3. Verify Import
```bash
python -c "
from app.scheme_repository import SchemeRepository
repo = SchemeRepository()
schemes = repo.get_all_schemes()
print(f'Total schemes: {len(schemes)}')

# Check specific scheme
scheme = repo.get_scheme_by_id('KCC-001')
if scheme:
    print(f'Found: {scheme.scheme_name}')
"
```

### 4. Test Bot
```bash
python -c "
import asyncio
from app.yconnect_pipeline import YConnectPipeline

async def test():
    pipeline = YConnectPipeline()
    response = await pipeline.process_message(
        'Kisan Credit Card ke baare mein batao',
        '+919876543210'
    )
    print(response)

asyncio.run(test())
"
```

## 🎯 Quality Checklist

Before importing, verify each scheme has:
- ✅ Unique scheme_id
- ✅ Complete description (at least 100 words)
- ✅ Hindi translation for name and description
- ✅ Correct category
- ✅ Valid eligibility criteria
- ✅ Detailed benefits
- ✅ Step-by-step application process
- ✅ Official URL (working link)
- ✅ At least one helpline number
- ✅ Correct status (active/expired/upcoming)

## 💡 Tips

1. **Start with popular schemes** - PM-KISAN, Ayushman Bharat are already done
2. **Focus on central schemes** - Easier to verify, applicable to all states
3. **Get Hindi translations** - Critical for rural users
4. **Verify helpline numbers** - Call them to confirm they work
5. **Test official URLs** - Make sure links are not broken
6. **Check dates** - Ensure start_date is in the past for active schemes

## 🚨 Common Mistakes

1. ❌ Invalid JSON syntax (missing commas, quotes)
2. ❌ Duplicate scheme_ids
3. ❌ Wrong category names (use exact names from list)
4. ❌ Missing required fields
5. ❌ Incorrect date format (use ISO 8601: `2020-01-01T00:00:00`)
6. ❌ Empty translations (at least add Hindi)

## 📚 Resources

- MyScheme Portal: https://www.myscheme.gov.in
- India.gov.in: https://www.india.gov.in/schemes
- Ministry Websites: Check individual ministry sites for detailed info

## 🎬 After Scraping

Once you have 10-15 more schemes:

1. Import them: `python scripts/import_schemes.py --file data/myscheme_scraped.json --format json`
2. Restart app: `docker-compose restart app`
3. Test queries for each new scheme
4. Update your demo script with new schemes
5. Practice queries before hackathon

---

**Good luck with scraping! 🚀**

Need help? Check the template in `data/myscheme_template.json`
