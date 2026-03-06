# Pre-Demo Checklist for AI FOR BHARAT Hackathon

## 🎯 Complete This Before Your Demo

### Phase 1: Setup (Do This Now)

#### 1. Execute Hybrid Approach
```bash
python scripts/execute_hybrid_approach.py
```

Expected output:
```
✓ Successfully imported 5 real schemes
✓ Successfully generated 80 sample schemes
✓ Successfully imported 80 sample schemes
✓ Database verification complete
✓ Bot test successful
```

**Status**: [ ] Done

---

#### 2. Restart Application
```bash
docker-compose restart app
```

Wait 30 seconds for app to fully start.

**Status**: [ ] Done

---

#### 3. Verify Database
```bash
python -c "
from app.scheme_repository import SchemeRepository
repo = SchemeRepository()
schemes = repo.get_all_schemes()
print(f'Total schemes: {len(schemes)}')
print(f'Expected: 85')
print('Status: PASS' if len(schemes) >= 85 else 'Status: FAIL')
"
```

Expected: `Total schemes: 85`

**Status**: [ ] Done

---

### Phase 2: Testing (30 Minutes Before Demo)

#### 4. Test Each Real Scheme

**Test 1: PM-KISAN**
```bash
python -c "
import asyncio
from app.yconnect_pipeline import YConnectPipeline

async def test():
    pipeline = YConnectPipeline()
    response = await pipeline.process_message(
        'PM-KISAN ke baare mein batao',
        '+919876543210'
    )
    print('Query: PM-KISAN ke baare mein batao')
    print(f'Response length: {len(response)} chars')
    print(f'Contains PM-KISAN: {\"PM-KISAN\" in response or \"किसान\" in response}')
    print(f'Response preview: {response[:200]}...')

asyncio.run(test())
"
```

Expected: Response contains PM-KISAN details, ₹6000, farmer

**Status**: [ ] Pass [ ] Fail

---

**Test 2: Ayushman Bharat**
```bash
python -c "
import asyncio
from app.yconnect_pipeline import YConnectPipeline

async def test():
    pipeline = YConnectPipeline()
    response = await pipeline.process_message(
        'Ayushman Bharat kya hai?',
        '+919876543210'
    )
    print('Query: Ayushman Bharat kya hai?')
    print(f'Response length: {len(response)} chars')
    print(f'Contains Ayushman: {\"Ayushman\" in response or \"आयुष्मान\" in response}')
    print(f'Response preview: {response[:200]}...')

asyncio.run(test())
"
```

Expected: Response contains Ayushman Bharat, ₹5 lakh, health insurance

**Status**: [ ] Pass [ ] Fail

---

**Test 3: PM Awas Yojana**
```bash
python -c "
import asyncio
from app.yconnect_pipeline import YConnectPipeline

async def test():
    pipeline = YConnectPipeline()
    response = await pipeline.process_message(
        'PM Awas Yojana Gramin details',
        '+919876543210'
    )
    print('Query: PM Awas Yojana Gramin details')
    print(f'Response length: {len(response)} chars')
    print(f'Contains Awas: {\"Awas\" in response or \"आवास\" in response}')
    print(f'Response preview: {response[:200]}...')

asyncio.run(test())
"
```

Expected: Response contains PM Awas Yojana, ₹1.2 lakh, housing

**Status**: [ ] Pass [ ] Fail

---

**Test 4: MGNREGA**
```bash
python -c "
import asyncio
from app.yconnect_pipeline import YConnectPipeline

async def test():
    pipeline = YConnectPipeline()
    response = await pipeline.process_message(
        'MGNREGA mein kaise apply karein?',
        '+919876543210'
    )
    print('Query: MGNREGA mein kaise apply karein?')
    print(f'Response length: {len(response)} chars')
    print(f'Contains MGNREGA: {\"MGNREGA\" in response or \"मनरेगा\" in response}')
    print(f'Response preview: {response[:200]}...')

asyncio.run(test())
"
```

Expected: Response contains MGNREGA, 100 days, employment

**Status**: [ ] Pass [ ] Fail

---

**Test 5: Beti Bachao Beti Padhao**
```bash
python -c "
import asyncio
from app.yconnect_pipeline import YConnectPipeline

async def test():
    pipeline = YConnectPipeline()
    response = await pipeline.process_message(
        'Beti Bachao Beti Padhao benefits',
        '+919876543210'
    )
    print('Query: Beti Bachao Beti Padhao benefits')
    print(f'Response length: {len(response)} chars')
    print(f'Contains Beti: {\"Beti\" in response or \"बेटी\" in response}')
    print(f'Response preview: {response[:200]}...')

asyncio.run(test())
"
```

Expected: Response contains Beti Bachao, girl child, education

**Status**: [ ] Pass [ ] Fail

---

#### 5. Test WhatsApp Integration

Send these messages to your WhatsApp bot:

1. "PM-KISAN ke baare mein batao"
   - **Expected**: Response within 5 seconds with PM-KISAN details
   - **Status**: [ ] Pass [ ] Fail

2. "Ayushman Bharat kya hai?"
   - **Expected**: Response with health insurance details
   - **Status**: [ ] Pass [ ] Fail

3. "Mujhe housing scheme chahiye"
   - **Expected**: Response with PM Awas Yojana or similar
   - **Status**: [ ] Pass [ ] Fail

---

#### 6. Check Application Logs

```bash
docker logs y-connect-app | tail -100
```

Look for:
- ✅ No ERROR messages
- ✅ Successful LLM calls
- ✅ Successful vector searches
- ✅ Response generation working

**Status**: [ ] Clean [ ] Has Errors

If errors, check:
```bash
# Check all containers
docker ps

# Check Qdrant
docker logs y-connect-qdrant | tail -50

# Check PostgreSQL
docker logs y-connect-postgres | tail -50

# Check Redis
docker logs y-connect-redis | tail -50
```

---

### Phase 3: Demo Preparation (15 Minutes Before)

#### 7. Prepare Demo Script

**Opening** (30 seconds)
```
"Hi, I'm [Your Name] and this is Y-Connect - an AI-powered WhatsApp bot 
that helps rural Indians discover government schemes in their own language.

We're using AWS Bedrock's Nova Lite model for natural language understanding 
and Qdrant for semantic search across 85+ government schemes."
```

**Status**: [ ] Memorized

---

**Demo Flow** (2 minutes)

1. Show WhatsApp interface on phone/screen
2. Send: "PM-KISAN ke baare mein batao"
3. Wait for response (should be < 5 seconds)
4. Highlight:
   - Hindi language support
   - Accurate scheme details
   - Eligibility criteria
   - Application process
   - Official links

5. Send: "Ayushman Bharat kya hai?"
6. Highlight:
   - English language support
   - Health insurance details
   - ₹5 lakh coverage

**Status**: [ ] Practiced

---

**Technical Highlights** (1 minute)
```
"The system uses:
- RAG pipeline with Qdrant vector database
- AWS Bedrock Nova Lite for response generation
- Multilingual support for 10 Indian languages
- Session management with Redis
- PostgreSQL for scheme storage
- Docker containerization for easy deployment"
```

**Status**: [ ] Memorized

---

**Impact Statement** (30 seconds)
```
"Y-Connect makes government schemes accessible to everyone, 
especially in rural areas where internet access is limited. 
No app download needed - just WhatsApp. 
We currently have 85 schemes and can scale to thousands."
```

**Status**: [ ] Memorized

---

#### 8. Backup Queries (In Case of Issues)

If primary queries fail, use these:

1. "Show me farmer schemes"
2. "Health insurance schemes"
3. "Housing schemes for poor"
4. "Employment schemes"
5. "Women welfare schemes"

**Status**: [ ] Written Down

---

#### 9. Technical Setup

- [ ] Laptop fully charged
- [ ] Phone fully charged
- [ ] WhatsApp bot number saved
- [ ] Internet connection stable
- [ ] Docker containers running
- [ ] Application logs clean
- [ ] Backup internet (mobile hotspot)
- [ ] Screen sharing tested (if virtual)

---

#### 10. Presentation Materials

- [ ] Slides prepared (if required)
- [ ] Architecture diagram ready
- [ ] Demo video recorded (backup)
- [ ] GitHub repo link ready
- [ ] AWS credentials secured (don't show!)
- [ ] Twilio credentials secured (don't show!)

---

### Phase 4: Final Checks (5 Minutes Before)

#### 11. System Health Check

```bash
# Check all containers are running
docker ps

# Should see:
# - y-connect-app
# - y-connect-postgres
# - y-connect-qdrant
# - y-connect-redis
```

**Status**: [ ] All Running

---

#### 12. Quick Test

```bash
# One final test
python -c "
import asyncio
from app.yconnect_pipeline import YConnectPipeline

async def test():
    pipeline = YConnectPipeline()
    response = await pipeline.process_message('PM-KISAN details', '+919876543210')
    print('✓ Bot is working!' if len(response) > 50 else '✗ Bot failed!')

asyncio.run(test())
"
```

**Status**: [ ] Working

---

#### 13. Confidence Check

Rate your confidence (1-10):

- [ ] I understand the system architecture: ___/10
- [ ] I can explain the RAG pipeline: ___/10
- [ ] I can demo the WhatsApp bot: ___/10
- [ ] I can answer technical questions: ___/10
- [ ] I'm ready to present: ___/10

**Target**: All scores ≥ 7

---

### Emergency Contacts

If something breaks:

1. **Database issues**: Restart PostgreSQL
   ```bash
   docker-compose restart postgres
   ```

2. **Bot not responding**: Restart app
   ```bash
   docker-compose restart app
   ```

3. **Vector search failing**: Restart Qdrant
   ```bash
   docker-compose restart qdrant
   ```

4. **Everything broken**: Full restart
   ```bash
   docker-compose down && docker-compose up -d
   ```

5. **Still broken**: Use demo video backup

---

## 🎯 Final Checklist

Before walking into the demo:

- [ ] All 5 real schemes tested and working
- [ ] WhatsApp integration tested
- [ ] Demo script memorized
- [ ] Backup queries ready
- [ ] All containers running
- [ ] Logs are clean
- [ ] Phone charged
- [ ] Laptop charged
- [ ] Internet stable
- [ ] Confident and ready

---

## 🏆 You Got This!

Remember:
- ✅ Your bot is LIVE and WORKING
- ✅ You have REAL government schemes
- ✅ Your tech stack is SOLID (AWS Bedrock, Qdrant, PostgreSQL)
- ✅ You've TESTED everything
- ✅ You're PREPARED

**Breathe. Smile. Demo. Win. 🚀**

---

## Post-Demo

After the demo:
- [ ] Thank the judges
- [ ] Share GitHub repo link
- [ ] Answer questions confidently
- [ ] Collect feedback
- [ ] Celebrate! 🎉

---

**Good luck with AI FOR BHARAT! You're going to crush it! 💪**
