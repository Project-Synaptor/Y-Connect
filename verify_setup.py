#!/usr/bin/env python3
"""Verification script for Y-Connect WhatsApp Bot setup"""

import sys


def verify_imports():
    """Verify all required packages can be imported"""
    print("Verifying package imports...")
    
    packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pydantic", "Pydantic"),
        ("pydantic_settings", "Pydantic Settings"),
        ("httpx", "HTTPX"),
        ("psycopg2", "PostgreSQL Driver"),
        ("redis", "Redis"),
        ("pytest", "Pytest"),
        ("hypothesis", "Hypothesis"),
        ("langdetect", "Language Detection"),
        ("dotenv", "Python Dotenv"),
        ("pythonjsonlogger", "JSON Logger"),
    ]
    
    failed = []
    for package, name in packages:
        try:
            __import__(package)
            print(f"  ✓ {name}")
        except ImportError as e:
            print(f"  ✗ {name}: {e}")
            failed.append(name)
    
    return len(failed) == 0


def verify_app_modules():
    """Verify application modules can be imported"""
    print("\nVerifying application modules...")
    
    modules = [
        ("app.config", "Configuration"),
        ("app.logging_config", "Logging Configuration"),
        ("app.main", "Main Application"),
    ]
    
    failed = []
    for module, name in modules:
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed.append(name)
    
    return len(failed) == 0


def verify_config():
    """Verify configuration loads correctly"""
    print("\nVerifying configuration...")
    
    try:
        from app.config import get_settings
        settings = get_settings()
        print(f"  ✓ Settings loaded")
        print(f"    - App Name: {settings.app_name}")
        print(f"    - Environment: {settings.app_env}")
        print(f"    - Log Level: {settings.log_level}")
        return True
    except Exception as e:
        print(f"  ✗ Configuration failed: {e}")
        return False


def verify_fastapi():
    """Verify FastAPI application"""
    print("\nVerifying FastAPI application...")
    
    try:
        from app.main import app
        print(f"  ✓ FastAPI app created")
        print(f"    - Title: {app.title}")
        print(f"    - Version: {app.version}")
        
        # Check routes
        routes = [route.path for route in app.routes]
        print(f"    - Routes: {', '.join(routes)}")
        return True
    except Exception as e:
        print(f"  ✗ FastAPI app failed: {e}")
        return False


def main():
    """Run all verification checks"""
    print("=" * 60)
    print("Y-Connect WhatsApp Bot - Setup Verification")
    print("=" * 60)
    
    checks = [
        verify_imports(),
        verify_app_modules(),
        verify_config(),
        verify_fastapi(),
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✓ All verification checks passed!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Update .env file with your actual API keys")
        print("2. Set up PostgreSQL and Redis databases")
        print("3. Run the application: python app/main.py")
        print("4. Run tests: pytest")
        return 0
    else:
        print("✗ Some verification checks failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
