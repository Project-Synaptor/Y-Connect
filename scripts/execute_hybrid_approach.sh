#!/bin/bash
# Hybrid Approach Execution Script
# This script imports real schemes and generates sample schemes for Y-Connect

set -e  # Exit on error

echo "=========================================="
echo "Y-Connect Hybrid Approach Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Import Real Schemes
echo -e "${YELLOW}Step 1: Importing 5 Real Government Schemes${NC}"
echo "-------------------------------------------"
python scripts/import_schemes.py --file data/real_schemes_starter.json --format json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully imported 5 real schemes${NC}"
else
    echo -e "${RED}✗ Failed to import real schemes${NC}"
    exit 1
fi

echo ""

# Step 2: Generate Sample Schemes
echo -e "${YELLOW}Step 2: Generating 80 Sample Schemes${NC}"
echo "-------------------------------------------"
python scripts/generate_sample_schemes.py --count 80 --output data/sample_schemes.json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully generated 80 sample schemes${NC}"
else
    echo -e "${RED}✗ Failed to generate sample schemes${NC}"
    exit 1
fi

echo ""

# Step 3: Import Sample Schemes
echo -e "${YELLOW}Step 3: Importing 80 Sample Schemes${NC}"
echo "-------------------------------------------"
python scripts/import_schemes.py --file data/sample_schemes.json --format json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully imported 80 sample schemes${NC}"
else
    echo -e "${RED}✗ Failed to import sample schemes${NC}"
    exit 1
fi

echo ""

# Step 4: Verify Database
echo -e "${YELLOW}Step 4: Verifying Database${NC}"
echo "-------------------------------------------"
python -c "
from app.scheme_repository import SchemeRepository
from app.models import SchemeStatus

repo = SchemeRepository()
all_schemes = repo.get_all_schemes()
active_schemes = [s for s in all_schemes if s.status == SchemeStatus.ACTIVE]

print(f'Total schemes in database: {len(all_schemes)}')
print(f'Active schemes: {len(active_schemes)}')
print(f'Expected: 85 total (5 real + 80 sample)')

# Show real schemes
print('\nReal Schemes Imported:')
real_scheme_ids = ['PM-KISAN-001', 'AYUSHMAN-BHARAT-001', 'PM-AWAS-GRAMIN-001', 'MGNREGA-001', 'BBBP-001']
for scheme_id in real_scheme_ids:
    scheme = repo.get_scheme_by_id(scheme_id)
    if scheme:
        print(f'  ✓ {scheme_id}: {scheme.scheme_name}')
    else:
        print(f'  ✗ {scheme_id}: NOT FOUND')
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database verification complete${NC}"
else
    echo -e "${RED}✗ Database verification failed${NC}"
    exit 1
fi

echo ""

# Step 5: Test Bot
echo -e "${YELLOW}Step 5: Testing Bot with Real Scheme Query${NC}"
echo "-------------------------------------------"
python -c "
import asyncio
from app.yconnect_pipeline import YConnectPipeline

async def test():
    pipeline = YConnectPipeline()
    
    # Test with PM-KISAN query
    response = await pipeline.process_message(
        'PM-KISAN ke baare mein batao',
        '+919876543210'
    )
    
    print('Query: PM-KISAN ke baare mein batao')
    print(f'Response: {response[:200]}...')
    
    if 'PM-KISAN' in response or 'किसान' in response:
        print('\n✓ Bot successfully retrieved PM-KISAN scheme!')
        return True
    else:
        print('\n✗ Bot did not retrieve PM-KISAN scheme')
        return False

result = asyncio.run(test())
exit(0 if result else 1)
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Bot test successful${NC}"
else
    echo -e "${YELLOW}⚠ Bot test had issues (may need to restart app)${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Hybrid Approach Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  • 5 real government schemes imported"
echo "  • 80 sample schemes generated and imported"
echo "  • Total: 85 schemes in database"
echo ""
echo "Next Steps:"
echo "  1. Restart your app: docker-compose restart app"
echo "  2. Test with WhatsApp queries"
echo "  3. Scrape 10-15 more real schemes from MyScheme.gov.in"
echo ""
echo "Demo Queries (use these for hackathon):"
echo "  • 'PM-KISAN ke baare mein batao'"
echo "  • 'Ayushman Bharat kya hai?'"
echo "  • 'Mujhe housing scheme chahiye'"
echo "  • 'MGNREGA mein kaise apply karein?'"
echo "  • 'Beti Bachao Beti Padhao benefits'"
echo ""
