"""
entity_logic.py - Knowledge Graph Manager for TruPathNJ
Handles Entity SEO via Wikidata/Wikipedia for semantic content optimization.

Updated: Bing-Hybrid Title Strategy
- Google: Semantic entity-rich titles
- Bing: Exact-match keyword-heavy H1s
"""

import requests
import wikipedia
import re
from typing import List, Dict, Optional, Tuple
from functools import lru_cache

# Wikidata SPARQL endpoint
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# Pre-defined entity mappings for addiction treatment domain
# These are curated variants that perform well in search
DOMAIN_ENTITIES = {
    "addiction treatment": {
        "wikidata_id": "Q1141488",
        "variants": [
            "Substance Abuse Treatment",
            "Chemical Dependency Treatment", 
            "Substance Use Disorder Care",
            "Drug Rehabilitation Services",
            "Addiction Recovery Programs"
        ],
        "ppo_variants": [
            "Private Pay Addiction Treatment",
            "PPO Insurance Rehab Programs",
            "Executive Addiction Treatment",
            "Confidential Substance Abuse Care",
            "Premium Recovery Services"
        ],
        # Bing exact-match keywords
        "exact_keywords": ["Addiction Treatment", "Rehab", "Drug Rehab", "Treatment Center"]
    },
    "drug rehab": {
        "wikidata_id": "Q1141488",
        "variants": [
            "Drug Rehabilitation Center",
            "Substance Abuse Facility",
            "Addiction Treatment Center",
            "Recovery Treatment Program",
            "Chemical Dependency Center"
        ],
        "ppo_variants": [
            "Private Drug Rehabilitation",
            "PPO-Covered Rehab Center",
            "Executive Drug Treatment",
            "Confidential Rehab Services",
            "Premium Drug Recovery"
        ],
        "exact_keywords": ["Drug Rehab", "Rehab Center", "Drug Treatment", "Rehabilitation"]
    },
    "alcohol rehab": {
        "wikidata_id": "Q582577",
        "variants": [
            "Alcohol Treatment Center",
            "Alcoholism Recovery Program",
            "Alcohol Detox Facility",
            "Alcohol Dependency Treatment",
            "Alcohol Rehabilitation Services"
        ],
        "ppo_variants": [
            "Private Alcohol Treatment",
            "PPO Alcohol Rehabilitation",
            "Executive Alcohol Recovery",
            "Confidential Alcohol Detox",
            "Premium Alcoholism Treatment"
        ],
        "exact_keywords": ["Alcohol Rehab", "Alcohol Treatment", "Alcoholism Treatment"]
    },
    "detox": {
        "wikidata_id": "Q900805",
        "variants": [
            "Medical Detoxification",
            "Detox Treatment Center",
            "Withdrawal Management",
            "Medically-Supervised Detox",
            "Drug Detoxification Services"
        ],
        "ppo_variants": [
            "Private Medical Detox",
            "PPO-Covered Detoxification",
            "Executive Detox Program",
            "Confidential Withdrawal Treatment",
            "Premium Detox Services"
        ],
        "exact_keywords": ["Detox", "Detox Center", "Medical Detox", "Drug Detox"]
    },
    "inpatient rehab": {
        "wikidata_id": "Q1141488",
        "variants": [
            "Residential Treatment Center",
            "Inpatient Treatment Facility",
            "Live-In Rehabilitation",
            "24-Hour Addiction Care",
            "Residential Recovery Program"
        ],
        "ppo_variants": [
            "Private Residential Treatment",
            "PPO Inpatient Rehabilitation",
            "Executive Residential Care",
            "Confidential Inpatient Program",
            "Premium Live-In Treatment"
        ],
        "exact_keywords": ["Inpatient Rehab", "Residential Treatment", "Inpatient Treatment"]
    },
    "mental health treatment": {
        "wikidata_id": "Q31207",
        "variants": [
            "Behavioral Health Services",
            "Psychiatric Treatment",
            "Mental Health Care",
            "Psychological Treatment",
            "Mental Wellness Programs"
        ],
        "ppo_variants": [
            "Private Mental Health Care",
            "PPO Behavioral Health",
            "Executive Psychiatric Services",
            "Confidential Mental Health Treatment",
            "Premium Psychological Care"
        ],
        "exact_keywords": ["Mental Health Treatment", "Behavioral Health", "Psychiatric Care"]
    }
}

# Bing-optimized H1 templates (exact match keyword patterns)
# These templates ensure the exact phrases Bing needs are present
BING_H1_TEMPLATES = [
    "Private Addiction Treatment in {city} | PPO Coverage Accepted",
    "{city} Private Rehab & PPO Coverage | Confidential Care",
    "Private Drug Rehab in {city} | PPO Insurance Accepted",
    "{city} Addiction Treatment Center | Private Pay & PPO",
    "Confidential Rehab in {city} | Private & PPO Coverage",
    "Private Inpatient Rehab Near {city} | PPO Accepted",
    "{city} Private Addiction Treatment | PPO Insurance Welcome",
    "Drug & Alcohol Rehab in {city} | Private PPO Facility",
]

# Google-optimized semantic title templates
GOOGLE_SEO_TEMPLATES = [
    "{brand} Provides {service_variant} for {city} Residents",
    "{service_variant} Near {city} | {brand}",
    "Comprehensive {service_variant} Serving {city} | {brand}",
    "{brand}: Trusted {service_variant} for {city} Area",
    "Evidence-Based {service_variant} | Serving {city} | {brand}",
]

# Action verbs for title construction
TITLE_VERBS = ["Provides", "Offers", "Delivers", "Specializes in", "Features"]

# Brand positioning phrases
BRAND_MODIFIERS = ["Leading", "Trusted", "Premier", "Compassionate", "Evidence-Based"]


@lru_cache(maxsize=100)
def query_wikidata_aliases(entity_id: str) -> List[str]:
    """
    Query Wikidata SPARQL endpoint for entity aliases.
    Returns list of alternative labels for the entity.
    """
    query = f"""
    SELECT ?altLabel WHERE {{
        wd:{entity_id} skos:altLabel ?altLabel .
        FILTER(LANG(?altLabel) = "en")
    }}
    LIMIT 20
    """
    
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "TruPathNJ-SEO-Bot/1.0"
    }
    
    try:
        response = requests.get(
            WIKIDATA_ENDPOINT,
            params={"query": query, "format": "json"},
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        aliases = [
            binding["altLabel"]["value"] 
            for binding in data.get("results", {}).get("bindings", [])
        ]
        return aliases
    
    except Exception as e:
        print(f"Wikidata query error: {e}")
        return []


@lru_cache(maxsize=100)
def search_wikidata_entity(keyword: str) -> Optional[Dict]:
    """
    Search Wikidata for an entity matching the keyword.
    Returns entity ID and basic info.
    """
    search_url = "https://www.wikidata.org/w/api.php"
    
    params = {
        "action": "wbsearchentities",
        "search": keyword,
        "language": "en",
        "format": "json",
        "limit": 5
    }
    
    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("search", [])
        if results:
            top_result = results[0]
            return {
                "id": top_result.get("id"),
                "label": top_result.get("label"),
                "description": top_result.get("description"),
                "url": f"https://www.wikidata.org/wiki/{top_result.get('id')}"
            }
        return None
    
    except Exception as e:
        print(f"Wikidata search error: {e}")
        return None


def get_wikipedia_summary(keyword: str) -> Optional[Dict]:
    """
    Get Wikipedia page summary and extract related terms.
    """
    try:
        search_results = wikipedia.search(keyword, results=3)
        
        if not search_results:
            return None
        
        for result in search_results:
            try:
                page = wikipedia.page(result, auto_suggest=False)
                summary = page.summary[:500]
                
                return {
                    "title": page.title,
                    "url": page.url,
                    "summary": summary,
                    "categories": page.categories[:5] if page.categories else []
                }
            except (wikipedia.DisambiguationError, wikipedia.PageError):
                continue
        
        return None
    
    except Exception as e:
        print(f"Wikipedia error: {e}")
        return None


def get_entity_variants(keyword: str, include_ppo: bool = True) -> Dict:
    """
    Get semantic variants for a keyword using Wikidata and curated mappings.
    
    Args:
        keyword: The base keyword (e.g., "addiction treatment")
        include_ppo: Whether to include PPO-specific variants
    
    Returns:
        Dictionary with variants, wikidata info, exact keywords, and metadata
    """
    keyword_lower = keyword.lower().strip()
    
    result = {
        "original_keyword": keyword,
        "variants": [],
        "ppo_variants": [],
        "exact_keywords": [],  # NEW: For Bing exact match
        "wikidata_id": None,
        "wikidata_url": None,
        "wikipedia_url": None,
        "source": "unknown"
    }
    
    # Check curated domain entities first (highest quality)
    for domain_key, domain_data in DOMAIN_ENTITIES.items():
        if domain_key in keyword_lower or keyword_lower in domain_key:
            result["variants"] = domain_data["variants"][:5]
            result["ppo_variants"] = domain_data["ppo_variants"][:5] if include_ppo else []
            result["exact_keywords"] = domain_data.get("exact_keywords", [])
            result["wikidata_id"] = domain_data["wikidata_id"]
            result["wikidata_url"] = f"https://www.wikidata.org/wiki/{domain_data['wikidata_id']}"
            result["source"] = "curated_domain"
            
            wiki_info = get_wikipedia_summary(keyword)
            if wiki_info:
                result["wikipedia_url"] = wiki_info["url"]
            
            return result
    
    # Fall back to Wikidata search
    wikidata_entity = search_wikidata_entity(keyword)
    
    if wikidata_entity:
        result["wikidata_id"] = wikidata_entity["id"]
        result["wikidata_url"] = wikidata_entity["url"]
        result["source"] = "wikidata_search"
        
        aliases = query_wikidata_aliases(wikidata_entity["id"])
        
        clean_aliases = []
        for alias in aliases:
            if 3 <= len(alias) <= 50:
                clean_alias = alias.title()
                if clean_alias not in clean_aliases:
                    clean_aliases.append(clean_alias)
        
        result["variants"] = clean_aliases[:5]
        # Default exact keywords for non-curated terms
        result["exact_keywords"] = [keyword.title(), f"{keyword.title()} Center", f"{keyword.title()} Treatment"]
    
    wiki_info = get_wikipedia_summary(keyword)
    if wiki_info:
        result["wikipedia_url"] = wiki_info["url"]
        
        if not result["variants"] and wiki_info.get("categories"):
            for cat in wiki_info["categories"]:
                cat_clean = cat.replace("Category:", "").strip()
                if len(cat_clean) <= 40 and keyword_lower not in cat_clean.lower():
                    if cat_clean not in result["variants"]:
                        result["variants"].append(cat_clean)
                        if len(result["variants"]) >= 5:
                            break
    
    # Generate PPO variants from base variants
    if include_ppo and result["variants"]:
        ppo_prefixes = ["Private", "PPO-Covered", "Executive", "Confidential", "Premium"]
        for i, variant in enumerate(result["variants"][:5]):
            prefix = ppo_prefixes[i % len(ppo_prefixes)]
            result["ppo_variants"].append(f"{prefix} {variant}")
    
    return result


def construct_semantic_title(
    brand: str,
    city: str,
    service_variant: str,
    include_ppo: bool = True,
    style: str = "standard",
    keyword: str = "addiction treatment"
) -> Dict:
    """
    Construct DUAL titles optimized for both Google (semantic) and Bing (exact match).
    
    Bing-Hybrid Strategy:
    - h1_title: Contains exact phrases like "Private Addiction Treatment in {City}"
                Combined with semantic entities like "PPO Coverage"
    - seo_title: Fancy semantic version for Google with entity-rich language
    
    Args:
        brand: Brand name (e.g., "TruPath Recovery")
        city: City name (e.g., "Newark")
        service_variant: Service type (e.g., "Substance Abuse Treatment")
        include_ppo: Include PPO/Private Pay language
        style: "standard", "question", or "action"
        keyword: Base keyword for exact match lookup
    
    Returns:
        Dictionary with h1_title (Bing), seo_title (Google), and supporting elements
    """
    import random
    
    # Clean inputs
    brand = brand.strip()
    city = city.strip()
    service_variant = service_variant.strip()
    
    # Get entity data for exact keywords
    entity_data = get_entity_variants(keyword)
    exact_keywords = entity_data.get("exact_keywords", ["Addiction Treatment", "Rehab"])
    primary_exact = exact_keywords[0] if exact_keywords else "Addiction Treatment"
    
    titles = {}
    
    # ===========================================
    # BING H1: Exact Match + Semantic Hybrid
    # ===========================================
    # Must contain: "Private Addiction Treatment in {City}" or "{City} Private Rehab & PPO Coverage"
    
    bing_templates = [
        f"Private Addiction Treatment in {city} | PPO Coverage Accepted",
        f"{city} Private Rehab & PPO Coverage | Confidential Care",
        f"Private {primary_exact} in {city} | PPO Insurance Accepted",
        f"{city} Private {primary_exact} Center | PPO & Private Pay",
        f"Confidential {primary_exact} in {city} | PPO Coverage Welcome",
        f"Private Inpatient Rehab Near {city} | PPO Accepted",
        f"{city} Drug & Alcohol Rehab | Private PPO Treatment",
        f"Private Pay Rehab in {city} | PPO Insurance Coverage",
    ]
    
    # Select based on style
    if style == "standard":
        titles["h1_title"] = f"Private Addiction Treatment in {city} | PPO Coverage Accepted"
    elif style == "question":
        titles["h1_title"] = f"Looking for Private Rehab in {city}? PPO Coverage Accepted"
    elif style == "action":
        titles["h1_title"] = f"{city} Private Rehab & PPO Coverage | Start Recovery Today"
    else:
        titles["h1_title"] = random.choice(bing_templates)
    
    # ===========================================
    # GOOGLE SEO TITLE: Semantic Entity-Rich
    # ===========================================
    verb = random.choice(TITLE_VERBS)
    modifier = random.choice(BRAND_MODIFIERS)
    
    if style == "standard":
        if include_ppo:
            titles["seo_title"] = f"{brand} {verb} {service_variant} with PPO Coverage for {city} Residents"
        else:
            titles["seo_title"] = f"{brand} {verb} {service_variant} for {city} Residents"
    
    elif style == "question":
        if include_ppo:
            titles["seo_title"] = f"Seeking {service_variant} Near {city}? {brand} Accepts PPO Insurance"
        else:
            titles["seo_title"] = f"Seeking {service_variant} Near {city}? | {brand}"
    
    elif style == "action":
        if include_ppo:
            titles["seo_title"] = f"Get {modifier} {service_variant} with PPO Coverage | Serving {city} | {brand}"
        else:
            titles["seo_title"] = f"Get {modifier} {service_variant} | Serving {city} | {brand}"
    
    # ===========================================
    # SUPPORTING ELEMENTS
    # ===========================================
    
    # Title tag (60 chars max for SERP display)
    if include_ppo:
        titles["title_tag"] = f"Private {primary_exact} in {city} | PPO Accepted | {brand}"[:60]
    else:
        titles["title_tag"] = f"{primary_exact} in {city} | {brand}"[:60]
    
    # Meta description (155 chars max)
    titles["meta_description"] = (
        f"Find private {primary_exact.lower()} in {city}. "
        f"{'PPO insurance accepted. ' if include_ppo else ''}"
        f"{brand} offers confidential, evidence-based care. Call today."
    )[:155]
    
    # Open Graph title (for social sharing)
    titles["og_title"] = f"Private {primary_exact} Near {city} | {brand}"
    
    # Schema.org headline
    titles["schema_headline"] = titles["h1_title"]
    
    # Schema.org description
    titles["schema_description"] = (
        f"{brand} provides private {service_variant.lower()} services for residents of {city} "
        f"and surrounding areas. {'PPO insurance accepted. ' if include_ppo else ''}"
        f"Confidential assessment available 24/7."
    )
    
    # ===========================================
    # BING-SPECIFIC OPTIMIZATIONS
    # ===========================================
    titles["bing_optimized"] = {
        "title": titles["h1_title"],
        "exact_phrases": [
            f"Private Addiction Treatment in {city}",
            f"{city} Private Rehab",
            f"PPO Coverage {city}",
            f"Private {primary_exact} {city}",
        ],
        "target_keywords": exact_keywords,
        "description": (
            f"Private {primary_exact.lower()} in {city}. "
            f"PPO insurance & private pay accepted. "
            f"Confidential care from {brand}."
        )
    }
    
    # ===========================================
    # GOOGLE-SPECIFIC OPTIMIZATIONS
    # ===========================================
    titles["google_optimized"] = {
        "title": titles["seo_title"],
        "semantic_entities": [service_variant] + entity_data.get("variants", [])[:3],
        "entity_keywords": entity_data.get("ppo_variants", [])[:3],
        "wikidata_id": entity_data.get("wikidata_id"),
        "description": (
            f"{brand} offers comprehensive {service_variant.lower()} for {city} residents. "
            f"{'PPO coverage welcome. ' if include_ppo else ''}"
            f"Evidence-based programs with proven outcomes."
        )
    }
    
    # Canonical keyword variations (for internal linking)
    titles["keyword_variations"] = {
        "primary": f"Private {primary_exact} in {city}",
        "secondary": f"{city} {primary_exact} Center",
        "long_tail": f"Private PPO {primary_exact} near {city}",
        "semantic": f"{service_variant} for {city} residents",
    }
    
    return titles


def construct_bing_hybrid_titles(
    brand: str,
    city: str,
    keyword: str = "addiction treatment",
    variations: int = 3
) -> List[Dict]:
    """
    Generate multiple Bing-Hybrid title variations for A/B testing.
    
    Each variation includes both h1_title (Bing) and seo_title (Google).
    """
    entity_data = get_entity_variants(keyword, include_ppo=True)
    
    styles = ["standard", "question", "action"]
    results = []
    
    # Use different service variants for each variation
    all_variants = entity_data["ppo_variants"] + entity_data["variants"]
    
    for i in range(min(variations, len(styles))):
        variant = all_variants[i] if i < len(all_variants) else "Addiction Treatment"
        style = styles[i]
        
        title_data = construct_semantic_title(
            brand=brand,
            city=city,
            service_variant=variant,
            include_ppo=True,
            style=style,
            keyword=keyword
        )
        
        results.append({
            "variation_id": i + 1,
            "style": style,
            "service_variant": variant,
            "h1_title": title_data["h1_title"],
            "seo_title": title_data["seo_title"],
            "title_tag": title_data["title_tag"],
            "meta_description": title_data["meta_description"],
            "bing_exact_phrases": title_data["bing_optimized"]["exact_phrases"],
            "google_entities": title_data["google_optimized"]["semantic_entities"],
        })
    
    return results


def generate_content_variations(
    keyword: str,
    city: str,
    brand: str = "TruPath Recovery",
    num_variations: int = 3
) -> List[Dict]:
    """
    Generate multiple content variations for A/B testing.
    Combines entity variants with Bing-Hybrid title construction.
    """
    entity_data = get_entity_variants(keyword, include_ppo=True)
    variations = []
    
    styles = ["standard", "question", "action"]
    all_variants = entity_data["variants"] + entity_data["ppo_variants"]
    
    for i in range(min(num_variations, len(all_variants))):
        variant = all_variants[i]
        style = styles[i % len(styles)]
        
        title_data = construct_semantic_title(
            brand=brand,
            city=city,
            service_variant=variant,
            include_ppo=("Private" in variant or "PPO" in variant),
            style=style,
            keyword=keyword
        )
        
        variations.append({
            "variation_id": i + 1,
            "service_variant": variant,
            "style": style,
            "h1_title": title_data["h1_title"],
            "seo_title": title_data["seo_title"],
            "titles": title_data,
            "entity_data": {
                "wikidata_id": entity_data["wikidata_id"],
                "wikidata_url": entity_data["wikidata_url"],
                "wikipedia_url": entity_data["wikipedia_url"],
                "exact_keywords": entity_data["exact_keywords"]
            }
        })
    
    return variations


def get_local_entity_context(city: str, state: str) -> Dict:
    """
    Get entity context for a specific city (for local SEO).
    """
    result = {
        "city": city,
        "state": state,
        "wikipedia_url": None,
        "wikidata_id": None,
        "county": None,
        "region": None,
        "nearby_cities": []
    }
    
    search_term = f"{city}, {state}"
    
    try:
        page = wikipedia.page(search_term, auto_suggest=True)
        result["wikipedia_url"] = page.url
        
        summary = page.summary
        county_match = re.search(r'(\w+)\s+County', summary)
        if county_match:
            result["county"] = county_match.group(0)
    
    except Exception as e:
        print(f"Error getting city context for {city}: {e}")
    
    wikidata_entity = search_wikidata_entity(search_term)
    if wikidata_entity:
        result["wikidata_id"] = wikidata_entity["id"]
    
    return result


def validate_bing_h1(h1: str, city: str) -> Dict:
    """
    Validate that an H1 title meets Bing exact-match requirements.
    
    Returns validation result with suggestions if needed.
    """
    result = {
        "valid": False,
        "has_city": False,
        "has_exact_phrase": False,
        "has_ppo_language": False,
        "issues": [],
        "suggestions": []
    }
    
    h1_lower = h1.lower()
    city_lower = city.lower()
    
    # Check for city name
    if city_lower in h1_lower:
        result["has_city"] = True
    else:
        result["issues"].append(f"Missing city name: {city}")
        result["suggestions"].append(f"Add '{city}' to the H1")
    
    # Check for exact match phrases
    exact_phrases = [
        "private addiction treatment",
        "private rehab",
        "drug rehab",
        "addiction treatment",
        "ppo coverage",
        "private pay"
    ]
    
    for phrase in exact_phrases:
        if phrase in h1_lower:
            result["has_exact_phrase"] = True
            break
    
    if not result["has_exact_phrase"]:
        result["issues"].append("Missing exact-match keyword phrase")
        result["suggestions"].append("Include 'Private Addiction Treatment' or 'Private Rehab'")
    
    # Check for PPO/Private language
    ppo_terms = ["ppo", "private pay", "private", "insurance"]
    for term in ppo_terms:
        if term in h1_lower:
            result["has_ppo_language"] = True
            break
    
    if not result["has_ppo_language"]:
        result["issues"].append("Missing PPO/Private Pay language")
        result["suggestions"].append("Add 'PPO Coverage' or 'Private Pay'")
    
    # Overall validation
    result["valid"] = all([
        result["has_city"],
        result["has_exact_phrase"],
        result["has_ppo_language"]
    ])
    
    return result


# Quick test function
def test_entity_logic():
    """Test the updated entity logic functions."""
    print("=" * 60)
    print("Testing Bing-Hybrid Title Construction")
    print("=" * 60)
    
    print("\n1. Testing get_entity_variants...")
    variants = get_entity_variants("addiction treatment")
    print(f"   Variants: {variants['variants'][:3]}")
    print(f"   PPO Variants: {variants['ppo_variants'][:3]}")
    print(f"   Exact Keywords (Bing): {variants['exact_keywords']}")
    print(f"   Source: {variants['source']}")
    
    print("\n2. Testing construct_semantic_title (Bing-Hybrid)...")
    titles = construct_semantic_title(
        brand="TruPath Recovery",
        city="Newark",
        service_variant="Substance Abuse Treatment",
        keyword="addiction treatment"
    )
    print(f"   H1 (Bing):  {titles['h1_title']}")
    print(f"   SEO (Google): {titles['seo_title']}")
    print(f"   Title Tag: {titles['title_tag']}")
    
    print("\n3. Testing Bing H1 Validation...")
    validation = validate_bing_h1(titles['h1_title'], "Newark")
    print(f"   Valid: {validation['valid']}")
    print(f"   Has City: {validation['has_city']}")
    print(f"   Has Exact Phrase: {validation['has_exact_phrase']}")
    print(f"   Has PPO Language: {validation['has_ppo_language']}")
    
    print("\n4. Testing construct_bing_hybrid_titles...")
    hybrid_titles = construct_bing_hybrid_titles(
        brand="TruPath Recovery",
        city="Jersey City",
        variations=3
    )
    for t in hybrid_titles:
        print(f"\n   Variation {t['variation_id']} ({t['style']}):")
        print(f"     H1: {t['h1_title']}")
        print(f"     SEO: {t['seo_title']}")
    
    print("\n" + "=" * 60)
    print("All tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_entity_logic()
