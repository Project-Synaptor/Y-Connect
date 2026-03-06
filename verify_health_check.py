#!/usr/bin/env python3
"""
Verify Health Check Fix
Run this on EC2 after deploying to verify the fix works
"""

import asyncio
import json
from app.health_check import health_checker

async def main():
    print("=" * 60)
    print("Y-Connect Health Check Verification")
    print("=" * 60)
    
    print("\n1. Testing PostgreSQL health check...")
    postgres_result = await health_checker.check_postgres()
    print(f"   Status: {postgres_result.status.value}")
    print(f"   Message: {postgres_result.message}")
    if postgres_result.response_time_ms:
        print(f"   Response time: {postgres_result.response_time_ms:.2f}ms")
    
    print("\n2. Testing Redis health check...")
    redis_result = await health_checker.check_redis()
    print(f"   Status: {redis_result.status.value}")
    print(f"   Message: {redis_result.message}")
    if redis_result.response_time_ms:
        print(f"   Response time: {redis_result.response_time_ms:.2f}ms")
    
    print("\n3. Testing Vector Store health check...")
    vector_result = await health_checker.check_vector_store()
    print(f"   Status: {vector_result.status.value}")
    print(f"   Message: {vector_result.message}")
    if vector_result.response_time_ms:
        print(f"   Response time: {vector_result.response_time_ms:.2f}ms")
    
    print("\n4. Testing complete health check...")
    all_results = await health_checker.check_all()
    
    print("\n" + "=" * 60)
    print("Complete Health Check Results")
    print("=" * 60)
    print(json.dumps(all_results, indent=2))
    
    print("\n" + "=" * 60)
    overall_status = all_results["status"]
    if overall_status == "healthy":
        print("✅ ALL SYSTEMS HEALTHY")
    elif overall_status == "degraded":
        print("⚠️  SOME SYSTEMS DEGRADED")
    else:
        print("❌ SYSTEMS UNHEALTHY")
    print("=" * 60)
    
    return overall_status == "healthy"

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
