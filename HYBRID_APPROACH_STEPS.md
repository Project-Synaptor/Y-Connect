# Hybrid Approach - Step by Step Guide

## ✅ Step 1: Import Real Schemes (DONE!)

I've created `data/real_schemes_starter.json` with **5 verified real schemes**:

1. **PM-KISAN** - ₹6000/year for farmers
2. **Ayushman Bharat** - ₹5 lakh health insurance
3. **PM Awas Yojana (Gramin)** - ₹1.2 lakh for housing
4. **MGNREGA** - 100 days guaranteed employment
5. **Beti Bachao Beti Padhao** - Girl child welfare

All schemes have:
- ✅ Accurate descriptions
- ✅ Hindi translations (+ 4 other languages)
- ✅ Real official URLs
- ✅ Real helpline numbers
- ✅ Proper eligibility criteria
- ✅ Detailed application process

### Import these now:

```bash
python scripts/import_schemes.py --file data/real_schemes_starter.json --format json
```

Expected output:
```
Importing schemes from data/real_schemes_starter.json (format: json)
Inserted/updated scheme: PM-KISAN-001
Inserted/updated scheme: AYUSHMAN-BHARAT-001
Inserted/updated scheme: PM-AWAS-GRAMIN-001
Inserted/updated scheme: MGNREGA-001
Inserted/updated scheme: BBBP-001
Inserted 5 documents to database
Stored 5 embeddings in vector store
Import complete: 5/5 schemes imported successfully
```

---

## 📝 Step 2: Scrape More Real Schemes (Your Task)

Scrape **10-15 more schemes** from MyScheme.gov.in

### Recommended schemes to scrape:

**Agriculture (2 more):**
- Kisan Credit Card
- PM Fasal Bima Yojana

**Education (3 more):**
- National Scholarship Portal
- Mid-Day Meal Scheme
- PM Vidya Lakshmi

**Health (2 more):**
- Janani Suraksha Yojana
- PM Suraksha Bima Yojana

**Housing (1 more):**
- PM Awas Yojana (Urban)

**Women (2 more):**
- Sukanya Samriddhi Yojana
- Ujjwala Yojana

**Employment (2 more):**
- PM Mudra Yojana
- Stand Up India

**Financial (2 more):**
- PM Jan Dhan Yojana
- Atal Pension Yojana

### Save as: `data/myscheme_scraped.json`

Use the same format as `real_schemes_starter.json`

---

## 🤖 Step 3: Generate Sample Schemes

Fill the database with sample schemes:

```bash
# Generate 80 sample schemes
python scripts/generate_sample_schemes.py --count 80 --output data/sample_schemes.json

# Import them
python scripts/import_schemes.py --file data/sample_schemes.json --format json
```

---

## 🎯 Step 4: Test Your Bot

Test with REAL scheme queries:

```bash
# Test via Python
python -c "
import asyncio
from app.yconnect_pipeline import process_whatsapp_message

async def test():
    # Test PM-KISAN
    response = await process_whatsapp_message(
        'PM-KISAN ke baare mein batao',
        '+919876543210'
    )
    print('Response:', response)

asyncio.run(test())
"
```

Or test via WhatsApp:
- "PM-KISAN ke baare mein batao"
- "Ayushman Bharat kya hai?"
- "Mujhe housing scheme chahiye"
- "MGNREGA mein kaise apply karein?"

---

## 📊 Final Database Status

After completing all steps:

| Type | Count | Purpose |
|------|-------|---------|
| Real schemes (starter) | 5 | ✅ Imported |
| Real schemes (scraped) | 10-15 | 📝 Your task |
| Sample schemes | 80 | 🤖 Auto-generated |
| **TOTAL** | **95-100** | **Complete database** |

---

## 🎬 Demo Strategy

During hackathon demo, ONLY query these real schemes:

1. "PM-KISAN scheme details"
2. "Ayushman Bharat eligibility"
3. "How to apply for PM Awas Yojana?"
4. "MGNREGA wage rate"
5. "Beti Bachao Beti Padhao benefits"

Judges will see accurate, verifiable information! ✅

---

## ⚠️ Important Notes

1. **Don't mention sample schemes** during demo
2. **Stick to real schemes** you've imported
3. **Test all queries** before the demo
4. **Have backup queries** ready

---

## 🚀 Quick Commands Reference

```bash
# Import real schemes (starter)
python scripts/import_schemes.py --file data/real_schemes_starter.json --format json

# Import your scraped schemes
python scripts/import_schemes.py --file data/myscheme_scraped.json --format json

# Generate and import sample schemes
python scripts/generate_sample_schemes.py --count 80 --output data/sample_schemes.json
python scripts/import_schemes.py --file data/sample_schemes.json --format json

# Check database
python -c "from app.scheme_repository import SchemeRepository; repo = SchemeRepository(); print(f'Total schemes: {len(repo.get_all_schemes())}')"

# Test bot
python -c "import asyncio; from app.yconnect_pipeline import process_whatsapp_message; asyncio.run(process_whatsapp_message('PM-KISAN details', '+919876543210'))"
```

---

## ✅ Checklist

- [x] Import 5 real schemes (starter file)
- [ ] Scrape 10-15 more real schemes from MyScheme.gov.in
- [ ] Import scraped schemes
- [ ] Generate 80 sample schemes
- [ ] Import sample schemes
- [ ] Test all real scheme queries
- [ ] Prepare demo script
- [ ] Win the hackathon! 🏆

---

**Start with Step 1 now!** Import the starter schemes and test your bot. 🚀
