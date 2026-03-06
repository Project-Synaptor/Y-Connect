#!/usr/bin/env python3
"""
Hybrid Approach Execution Script
Imports real schemes and generates sample schemes for Y-Connect
"""

import sys
import subprocess
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def print_step(step_num, text):
    """Print step header"""
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {text}")
    print("=" * 60)


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\nRunning: {description}")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(result.stdout)
        print(f"✓ {description} - SUCCESS")
        return True
    else:
        print(result.stderr)
        print(f"✗ {description} - FAILED")
        return False


async def test_bot():
    """Test bot with real scheme query"""
    try:
        from app.yconnect_pipeline import YConnectPipeline
        
        pipeline = YConnectPipeline()
        
        # Test with PM-KISAN query
        response = await pipeline.process_message(
            'PM-KISAN ke baare mein batao',
            '+919876543210'
        )
        
        print('\nQuery: PM-KISAN ke baare mein batao')
        print(f'Response: {response[:200]}...')
        
        if 'PM-KISAN' in response or 'किसान' in response:
            print('\n✓ Bot successfully retrieved PM-KISAN scheme!')
            return True
        else:
            print('\n✗ Bot did not retrieve PM-KISAN scheme')
            return False
    except Exception as e:
        print(f'\n✗ Bot test failed: {e}')
        return False


def verify_database():
    """Verify database has correct schemes"""
    try:
        from app.scheme_repository import SchemeRepository
        from app.models import SchemeStatus
        
        repo = SchemeRepository()
        all_schemes = repo.get_all_schemes()
        active_schemes = [s for s in all_schemes if s.status == SchemeStatus.ACTIVE]
        
        print(f'\nTotal schemes in database: {len(all_schemes)}')
        print(f'Active schemes: {len(active_schemes)}')
        print(f'Expected: 85 total (5 real + 80 sample)')
        
        # Show real schemes
        print('\nReal Schemes Imported:')
        real_scheme_ids = [
            'PM-KISAN-001',
            'AYUSHMAN-BHARAT-001',
            'PM-AWAS-GRAMIN-001',
            'MGNREGA-001',
            'BBBP-001'
        ]
        
        all_found = True
        for scheme_id in real_scheme_ids:
            scheme = repo.get_scheme_by_id(scheme_id)
            if scheme:
                print(f'  ✓ {scheme_id}: {scheme.scheme_name}')
            else:
                print(f'  ✗ {scheme_id}: NOT FOUND')
                all_found = False
        
        return all_found and len(all_schemes) >= 85
    
    except Exception as e:
        print(f'\n✗ Database verification failed: {e}')
        return False


def main():
    """Main execution"""
    print_header("Y-Connect Hybrid Approach Setup")
    
    success = True
    
    # Step 1: Import Real Schemes
    print_step(1, "Importing 5 Real Government Schemes")
    if not run_command(
        ['python', 'scripts/import_schemes.py', '--file', 'data/real_schemes_starter.json', '--format', 'json'],
        "Import real schemes"
    ):
        print("\n✗ Failed to import real schemes")
        return 1
    
    # Step 2: Generate Sample Schemes
    print_step(2, "Generating 80 Sample Schemes")
    if not run_command(
        ['python', 'scripts/generate_sample_schemes.py', '--count', '80', '--output', 'data/sample_schemes.json'],
        "Generate sample schemes"
    ):
        print("\n✗ Failed to generate sample schemes")
        return 1
    
    # Step 3: Import Sample Schemes
    print_step(3, "Importing 80 Sample Schemes")
    if not run_command(
        ['python', 'scripts/import_schemes.py', '--file', 'data/sample_schemes.json', '--format', 'json'],
        "Import sample schemes"
    ):
        print("\n✗ Failed to import sample schemes")
        return 1
    
    # Step 4: Verify Database
    print_step(4, "Verifying Database")
    if not verify_database():
        print("\n⚠ Database verification had issues")
        success = False
    else:
        print("\n✓ Database verification complete")
    
    # Step 5: Test Bot
    print_step(5, "Testing Bot with Real Scheme Query")
    try:
        result = asyncio.run(test_bot())
        if result:
            print("\n✓ Bot test successful")
        else:
            print("\n⚠ Bot test had issues (may need to restart app)")
            success = False
    except Exception as e:
        print(f"\n⚠ Bot test failed: {e}")
        success = False
    
    # Final Summary
    print_header("Hybrid Approach Setup Complete!" if success else "Setup Complete with Warnings")
    
    print("\nSummary:")
    print("  • 5 real government schemes imported")
    print("  • 80 sample schemes generated and imported")
    print("  • Total: 85 schemes in database")
    
    print("\nNext Steps:")
    print("  1. Restart your app: docker-compose restart app")
    print("  2. Test with WhatsApp queries")
    print("  3. Scrape 10-15 more real schemes from MyScheme.gov.in")
    
    print("\nDemo Queries (use these for hackathon):")
    print("  • 'PM-KISAN ke baare mein batao'")
    print("  • 'Ayushman Bharat kya hai?'")
    print("  • 'Mujhe housing scheme chahiye'")
    print("  • 'MGNREGA mein kaise apply karein?'")
    print("  • 'Beti Bachao Beti Padhao benefits'")
    print()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
