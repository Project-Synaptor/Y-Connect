#!/usr/bin/env python3
"""
Test script for AWS Bedrock Nova Lite integration

Run this to verify your setup is working correctly
"""

import asyncio
import os
import sys


async def test_bedrock_direct():
    """Test AWS Bedrock directly"""
    print("=" * 60)
    print("TEST 1: Direct AWS Bedrock Connection")
    print("=" * 60)
    
    try:
        import boto3
        
        # Check credentials
        access_key = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        region = os.getenv('AWS_REGION', 'us-east-1')
        
        if not access_key or not secret_key:
            print("❌ AWS credentials not found in environment")
            print("   Add AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to .env")
            return False
        
        print(f"✓ AWS credentials found")
        print(f"✓ Region: {region}")
        
        # Initialize Bedrock client
        bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        print("✓ Bedrock client initialized")
        
        # Test API call
        print("\nTesting Bedrock API call...")
        response = bedrock_client.converse(
            modelId='us.amazon.nova-lite-v1:0',
            system=[{"text": "You are a helpful assistant."}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "Say 'Hello from AWS Bedrock Nova Lite!'"}]
                }
            ],
            inferenceConfig={
                "maxTokens": 100,
                "temperature": 0.5
            }
        )
        
        result = response['output']['message']['content'][0]['text']
        print(f"✓ Bedrock response: {result}")
        print("\n✅ AWS Bedrock is working correctly!\n")
        return True
    
    except ImportError:
        print("❌ boto3 not installed")
        print("   Run: pip install boto3")
        return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check AWS credentials in .env")
        print("2. Enable Nova Lite in AWS Bedrock Console")
        print("3. Verify IAM permissions for Bedrock")
        return False


async def test_rag_pipeline():
    """Test complete RAG pipeline"""
    print("=" * 60)
    print("TEST 2: Complete RAG Pipeline")
    print("=" * 60)
    
    try:
        from app.yconnect_pipeline import process_whatsapp_message
        
        print("✓ Pipeline imported successfully")
        
        # Test with simple message
        print("\nProcessing test message...")
        print("Input: 'Show me farmer schemes'")
        
        response = await process_whatsapp_message(
            user_message="Show me farmer schemes",
            phone_number="+919876543210"
        )
        
        print(f"\n✓ Response generated ({len(response)} chars):")
        print("-" * 60)
        print(response[:500] + "..." if len(response) > 500 else response)
        print("-" * 60)
        print("\n✅ RAG Pipeline is working correctly!\n")
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nNote: This test requires:")
        print("1. PostgreSQL running with scheme data")
        print("2. Redis running")
        print("3. Qdrant running with embeddings")
        print("\nRun: docker-compose up -d")
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Y-CONNECT AWS BEDROCK INTEGRATION TEST")
    print("=" * 60 + "\n")
    
    # Test 1: Direct Bedrock
    bedrock_ok = await test_bedrock_direct()
    
    if not bedrock_ok:
        print("\n⚠️  Fix Bedrock connection before testing pipeline")
        sys.exit(1)
    
    # Test 2: RAG Pipeline
    await asyncio.sleep(1)
    pipeline_ok = await test_rag_pipeline()
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"AWS Bedrock:   {'✅ PASS' if bedrock_ok else '❌ FAIL'}")
    print(f"RAG Pipeline:  {'✅ PASS' if pipeline_ok else '⚠️  SKIP (needs data)'}")
    print("=" * 60)
    
    if bedrock_ok:
        print("\n🎉 Your AWS Bedrock integration is ready!")
        print("\nNext steps:")
        print("1. Generate sample schemes: python scripts/generate_sample_schemes.py")
        print("2. Import schemes: python scripts/import_schemes.py --file data/sample_schemes.json")
        print("3. Test full pipeline again")
        print("4. Integrate with your webhook!")
    
    sys.exit(0 if bedrock_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
