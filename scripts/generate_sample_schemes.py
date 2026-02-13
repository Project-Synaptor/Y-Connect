#!/usr/bin/env python3
"""
Sample Scheme Data Generator for Y-Connect WhatsApp Bot

This script generates sample government schemes for testing purposes.
Creates 100+ schemes across all categories, languages, states, and statuses.

Usage:
    python scripts/generate_sample_schemes.py --output data/sample_schemes.json --count 100
"""

import argparse
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
from pathlib import Path

# Scheme categories
CATEGORIES = [
    "agriculture", "education", "health", "housing", "women",
    "senior_citizens", "employment", "financial_inclusion",
    "social_welfare", "skill_development"
]

# Indian states and union territories
STATES = [
    "ALL", "AP", "AR", "AS", "BR", "CG", "GA", "GJ", "HR", "HP",
    "JH", "KA", "KL", "MP", "MH", "MN", "ML", "MZ", "NL", "OD",
    "PB", "RJ", "SK", "TN", "TS", "TR", "UP", "UK", "WB",
    "AN", "CH", "DH", "DD", "DL", "JK", "LA", "LD", "PY"
]

# Authorities
AUTHORITIES = ["central", "state"]

# Statuses
STATUSES = ["active", "expired", "upcoming"]

# Supported languages
LANGUAGES = ["hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]

# Sample scheme templates by category
SCHEME_TEMPLATES = {
    "agriculture": {
        "names": [
            "Pradhan Mantri Kisan Samman Nidhi",
            "Kisan Credit Card Scheme",
            "Soil Health Card Scheme",
            "Pradhan Mantri Fasal Bima Yojana",
            "National Agriculture Market",
            "Paramparagat Krishi Vikas Yojana",
            "Rashtriya Krishi Vikas Yojana",
            "Micro Irrigation Fund",
            "Agriculture Infrastructure Fund",
            "Kisan Rail Scheme"
        ],
        "description_template": "This scheme provides {benefit} to farmers for {purpose}. It aims to improve agricultural productivity and farmer income.",
        "benefits_template": "Financial assistance of ₹{amount} per year, subsidized {item}, access to {service}.",
        "eligibility": {
            "occupation": "farmer",
            "land_holding": "any",
            "age_min": 18
        }
    },
    "education": {
        "names": [
            "Pradhan Mantri Vidya Lakshmi Scheme",
            "National Scholarship Portal",
            "Mid-Day Meal Scheme",
            "Beti Bachao Beti Padhao",
            "Samagra Shiksha Abhiyan",
            "National Means cum Merit Scholarship",
            "Post Matric Scholarship for SC Students",
            "Pre Matric Scholarship for Minorities",
            "Central Sector Scheme of Scholarships",
            "INSPIRE Scholarship"
        ],
        "description_template": "This scheme provides {benefit} to students for {purpose}. It aims to promote education and reduce dropout rates.",
        "benefits_template": "Scholarship of ₹{amount} per year, free textbooks, {service} support.",
        "eligibility": {
            "occupation": "student",
            "age_min": 6,
            "age_max": 25
        }
    },
    "health": {
        "names": [
            "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana",
            "Pradhan Mantri Suraksha Bima Yojana",
            "Janani Suraksha Yojana",
            "Rashtriya Swasthya Bima Yojana",
            "National Health Mission",
            "Pradhan Mantri Matru Vandana Yojana",
            "Mission Indradhanush",
            "Ayushman Bharat Health and Wellness Centres",
            "National Mental Health Programme",
            "Pradhan Mantri Bhartiya Janaushadhi Pariyojana"
        ],
        "description_template": "This scheme provides {benefit} for {purpose}. It aims to improve healthcare access and reduce medical expenses.",
        "benefits_template": "Health insurance coverage of ₹{amount}, free {service}, cashless treatment.",
        "eligibility": {
            "income_max": 500000,
            "age_min": 0
        }
    },
    "housing": {
        "names": [
            "Pradhan Mantri Awas Yojana - Gramin",
            "Pradhan Mantri Awas Yojana - Urban",
            "Credit Linked Subsidy Scheme",
            "Affordable Housing in Partnership",
            "Beneficiary Led Construction",
            "In-situ Slum Redevelopment",
            "Rajiv Awas Yojana",
            "Housing for All Mission",
            "Deendayal Antyodaya Yojana",
            "Smart Cities Mission Housing"
        ],
        "description_template": "This scheme provides {benefit} for {purpose}. It aims to provide affordable housing to all citizens.",
        "benefits_template": "Financial assistance of ₹{amount}, interest subsidy on home loans, {service}.",
        "eligibility": {
            "income_max": 1800000,
            "age_min": 18,
            "housing_status": "homeless or inadequate housing"
        }
    },
    "women": {
        "names": [
            "Beti Bachao Beti Padhao",
            "Pradhan Mantri Matru Vandana Yojana",
            "Sukanya Samriddhi Yojana",
            "Mahila Shakti Kendra",
            "Support to Training and Employment Programme",
            "Ujjwala Yojana",
            "National Creche Scheme",
            "Working Women Hostel",
            "Mahila E-Haat",
            "One Stop Centre Scheme"
        ],
        "description_template": "This scheme provides {benefit} to women for {purpose}. It aims to empower women and ensure their welfare.",
        "benefits_template": "Financial assistance of ₹{amount}, skill training, {service} support.",
        "eligibility": {
            "gender": "female",
            "age_min": 18
        }
    },
    "senior_citizens": {
        "names": [
            "Indira Gandhi National Old Age Pension Scheme",
            "Pradhan Mantri Vaya Vandana Yojana",
            "National Programme for Health Care of Elderly",
            "Senior Citizen Savings Scheme",
            "Integrated Programme for Older Persons",
            "Rashtriya Vayoshri Yojana",
            "Atal Vayo Abhyuday Yojana",
            "Maintenance and Welfare of Parents Act",
            "Senior Citizen Rail Concession",
            "Varishtha Pension Bima Yojana"
        ],
        "description_template": "This scheme provides {benefit} to senior citizens for {purpose}. It aims to ensure financial security and healthcare for elderly.",
        "benefits_template": "Monthly pension of ₹{amount}, healthcare benefits, {service}.",
        "eligibility": {
            "age_min": 60
        }
    },
    "employment": {
        "names": [
            "Mahatma Gandhi National Rural Employment Guarantee Act",
            "Pradhan Mantri Rojgar Protsahan Yojana",
            "Deen Dayal Upadhyaya Grameen Kaushalya Yojana",
            "National Career Service",
            "Pradhan Mantri Mudra Yojana",
            "Stand Up India Scheme",
            "Start-up India",
            "Atmanirbhar Bharat Rozgar Yojana",
            "Prime Minister's Employment Generation Programme",
            "National Urban Livelihoods Mission"
        ],
        "description_template": "This scheme provides {benefit} for {purpose}. It aims to generate employment and promote entrepreneurship.",
        "benefits_template": "Wage employment of ₹{amount} per day, skill training, {service}.",
        "eligibility": {
            "age_min": 18,
            "age_max": 60
        }
    },
    "financial_inclusion": {
        "names": [
            "Pradhan Mantri Jan Dhan Yojana",
            "Atal Pension Yojana",
            "Pradhan Mantri Jeevan Jyoti Bima Yojana",
            "Pradhan Mantri Suraksha Bima Yojana",
            "Stand Up India",
            "Pradhan Mantri Mudra Yojana",
            "Credit Guarantee Fund Scheme",
            "National Pension System",
            "Sukanya Samriddhi Account",
            "Senior Citizen Savings Scheme"
        ],
        "description_template": "This scheme provides {benefit} for {purpose}. It aims to promote financial inclusion and security.",
        "benefits_template": "Bank account with ₹{amount} insurance, pension benefits, {service}.",
        "eligibility": {
            "age_min": 18
        }
    },
    "social_welfare": {
        "names": [
            "National Social Assistance Programme",
            "Integrated Child Development Services",
            "National Child Labour Project",
            "Scheme for Adolescent Girls",
            "Integrated Programme for Street Children",
            "Ujjwala - Comprehensive Scheme",
            "Swadhar Greh",
            "Central Adoption Resource Authority",
            "Scheme for Welfare of Working Children",
            "Juvenile Justice Programme"
        ],
        "description_template": "This scheme provides {benefit} for {purpose}. It aims to ensure social welfare and protection of vulnerable groups.",
        "benefits_template": "Financial assistance of ₹{amount}, rehabilitation services, {service}.",
        "eligibility": {
            "age_min": 0
        }
    },
    "skill_development": {
        "names": [
            "Pradhan Mantri Kaushal Vikas Yojana",
            "National Skill Development Mission",
            "Deen Dayal Upadhyaya Grameen Kaushalya Yojana",
            "Craftsmen Training Scheme",
            "National Apprenticeship Promotion Scheme",
            "Skill India Mission",
            "Recognition of Prior Learning",
            "Jan Shikshan Sansthan",
            "Upgrading Skills and Training in Traditional Arts",
            "Seekho aur Kamao"
        ],
        "description_template": "This scheme provides {benefit} for {purpose}. It aims to enhance employability through skill development.",
        "benefits_template": "Free skill training, stipend of ₹{amount} per month, {service}.",
        "eligibility": {
            "age_min": 15,
            "age_max": 45
        }
    }
}

# Translation templates (simplified - in production would use actual translations)
LANGUAGE_NAMES = {
    "hi": "हिंदी",
    "ta": "தமிழ்",
    "te": "తెలుగు",
    "bn": "বাংলা",
    "mr": "मराठी",
    "gu": "ગુજરાતી",
    "kn": "ಕನ್ನಡ",
    "ml": "മലയാളം",
    "pa": "ਪੰਜਾਬੀ"
}


def generate_scheme_id(category: str, index: int) -> str:
    """Generate unique scheme ID"""
    category_code = category[:3].upper()
    return f"{category_code}-{index:04d}"


def generate_translations(text: str, languages: List[str]) -> Dict[str, str]:
    """
    Generate placeholder translations
    Note: In production, use actual translation service
    """
    translations = {}
    for lang in languages:
        # Placeholder: just add language indicator
        translations[lang] = f"[{LANGUAGE_NAMES[lang]}] {text}"
    return translations


def generate_scheme(
    category: str,
    index: int,
    authority: str,
    states: List[str],
    status: str
) -> Dict[str, Any]:
    """Generate a single scheme"""
    template = SCHEME_TEMPLATES[category]
    
    # Select random name from template
    base_name = random.choice(template["names"])
    scheme_name = f"{base_name} ({states[0] if states[0] != 'ALL' else 'National'})"
    
    # Generate amounts and items
    amounts = {
        "agriculture": random.choice([6000, 12000, 24000, 50000]),
        "education": random.choice([1000, 2000, 5000, 10000, 20000]),
        "health": random.choice([100000, 500000, 1000000]),
        "housing": random.choice([120000, 250000, 500000]),
        "women": random.choice([5000, 10000, 15000, 50000]),
        "senior_citizens": random.choice([200, 500, 1000, 2000]),
        "employment": random.choice([182, 250, 300]),
        "financial_inclusion": random.choice([100000, 200000, 500000]),
        "social_welfare": random.choice([300, 500, 1000, 2000]),
        "skill_development": random.choice([1500, 3000, 5000])
    }
    
    benefits_list = {
        "agriculture": ["seeds", "fertilizers", "equipment", "irrigation"],
        "education": ["tuition fee waiver", "hostel facility", "digital learning"],
        "health": ["medicines", "diagnostic tests", "ambulance service"],
        "housing": ["construction materials", "technical assistance", "land"],
        "women": ["vocational training", "childcare", "legal aid"],
        "senior_citizens": ["healthcare", "travel concession", "daycare"],
        "employment": ["job placement", "entrepreneurship support", "tools"],
        "financial_inclusion": ["insurance", "credit facility", "financial literacy"],
        "social_welfare": ["counseling", "shelter", "education support"],
        "skill_development": ["certification", "placement assistance", "tools"]
    }
    
    services = {
        "agriculture": "agricultural extension services",
        "education": "career counseling",
        "health": "telemedicine consultation",
        "housing": "architectural planning",
        "women": "self-help group formation",
        "senior_citizens": "geriatric care",
        "employment": "job matching",
        "financial_inclusion": "banking services",
        "social_welfare": "social worker support",
        "skill_development": "industry mentorship"
    }
    
    # Generate description and benefits
    description = template["description_template"].format(
        benefit="financial and technical support",
        purpose="improving quality of life"
    )
    
    benefits = template["benefits_template"].format(
        amount=amounts[category],
        item=random.choice(benefits_list[category]),
        service=services[category]
    )
    
    application_process = f"""
1. Visit the official website or nearest office
2. Fill the application form with required details
3. Submit documents: Aadhaar card, income certificate, bank account details
4. Application will be verified within 30 days
5. Benefits will be credited directly to bank account
    """.strip()
    
    # Generate dates based on status
    if status == "active":
        start_date = datetime.now() - timedelta(days=random.randint(30, 365))
        end_date = datetime.now() + timedelta(days=random.randint(180, 730))
    elif status == "expired":
        start_date = datetime.now() - timedelta(days=random.randint(365, 1095))
        end_date = datetime.now() - timedelta(days=random.randint(1, 180))
    else:  # upcoming
        start_date = datetime.now() + timedelta(days=random.randint(30, 180))
        end_date = start_date + timedelta(days=random.randint(365, 1095))
    
    scheme = {
        "scheme_id": generate_scheme_id(category, index),
        "scheme_name": scheme_name,
        "scheme_name_translations": generate_translations(scheme_name, LANGUAGES),
        "description": description,
        "description_translations": generate_translations(description, LANGUAGES),
        "category": category,
        "authority": authority,
        "applicable_states": states,
        "eligibility_criteria": template["eligibility"],
        "benefits": benefits,
        "benefits_translations": generate_translations(benefits, LANGUAGES),
        "application_process": application_process,
        "application_process_translations": generate_translations(application_process, LANGUAGES),
        "official_url": f"https://www.india.gov.in/schemes/{generate_scheme_id(category, index).lower()}",
        "helpline_numbers": [f"1800-{random.randint(100, 999)}-{random.randint(1000, 9999)}"],
        "status": status,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }
    
    return scheme


def generate_sample_schemes(count: int = 100) -> List[Dict[str, Any]]:
    """Generate sample schemes"""
    schemes = []
    schemes_per_category = count // len(CATEGORIES)
    
    for category in CATEGORIES:
        for i in range(schemes_per_category):
            # Vary authority, states, and status
            authority = random.choice(AUTHORITIES)
            
            if authority == "central":
                states = ["ALL"]
            else:
                # State schemes - pick 1-3 states
                num_states = random.randint(1, 3)
                states = random.sample([s for s in STATES if s != "ALL"], num_states)
            
            # Status distribution: 70% active, 20% expired, 10% upcoming
            status_choice = random.random()
            if status_choice < 0.7:
                status = "active"
            elif status_choice < 0.9:
                status = "expired"
            else:
                status = "upcoming"
            
            scheme = generate_scheme(category, i + 1, authority, states, status)
            schemes.append(scheme)
    
    # Add a few more to reach exact count
    remaining = count - len(schemes)
    for i in range(remaining):
        category = random.choice(CATEGORIES)
        authority = random.choice(AUTHORITIES)
        states = ["ALL"] if authority == "central" else random.sample(
            [s for s in STATES if s != "ALL"], random.randint(1, 3)
        )
        status = random.choice(STATUSES)
        
        scheme = generate_scheme(category, schemes_per_category + i + 1, authority, states, status)
        schemes.append(scheme)
    
    return schemes


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate sample government schemes for testing'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/sample_schemes.json',
        help='Output file path (default: data/sample_schemes.json)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=100,
        help='Number of schemes to generate (default: 100)'
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {args.count} sample schemes...")
    schemes = generate_sample_schemes(args.count)
    
    # Write to file
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(schemes, f, indent=2, ensure_ascii=False)
    
    print(f"\nGenerated {len(schemes)} schemes")
    print(f"Output written to: {args.output}")
    
    # Print statistics
    print("\nStatistics:")
    print(f"  Categories: {len(set(s['category'] for s in schemes))}")
    print(f"  Central schemes: {sum(1 for s in schemes if s['authority'] == 'central')}")
    print(f"  State schemes: {sum(1 for s in schemes if s['authority'] == 'state')}")
    print(f"  Active: {sum(1 for s in schemes if s['status'] == 'active')}")
    print(f"  Expired: {sum(1 for s in schemes if s['status'] == 'expired')}")
    print(f"  Upcoming: {sum(1 for s in schemes if s['status'] == 'upcoming')}")
    
    print(f"\nTo import these schemes, run:")
    print(f"  python scripts/import_schemes.py --file {args.output} --format json")


if __name__ == '__main__':
    main()
