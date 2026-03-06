#!/usr/bin/env python3
"""Quick bot test"""

import asyncio
from app.yconnect_pipeline import YConnectPipeline

async def test():
    print("Testing Y-Connect Bot...")
    print("=" * 60)
    
    pipeline = YConnectPipeline()
    
    # Test PM-KISAN query
    print("\nQuery: PM-KISAN ke baare mein batao")
    print("-" * 60)
    
    response = await pipeline.process_message(
        'PM-KISAN ke baare mein batao',
        '+919876543210'
    )
    
    print(f"Response ({len(response)} chars):")
    print(response[:500])
    
    # Check if response contains expected keywords
    success = any(keyword in response.lower() for keyword in ['pm-kisan', 'किसान', 'farmer', '6000', '6,000'])
    
    print("\n" + "=" * 60)
    if success:
        print("✓ TEST PASSED - Bot retrieved PM-KISAN scheme!")
    else:
        print("✗ TEST FAILED - Bot did not retrieve PM-KISAN")
    print("=" * 60)
    
    return success

if __name__ == '__main__':
    result = asyncio.run(test())
    exit(0 if result else 1)
