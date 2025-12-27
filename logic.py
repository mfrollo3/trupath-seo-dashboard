"""
logic.py - Private Pay Data Engine for TruPathNJ
Handles strategic SERP data collection for PPO-focused content generation.
Avoids competitor keywords, focuses on economic/demographic signals.
"""

import json
import re
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from serpapi import GoogleSearch
    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False
    print("Warning: serpapi not installed. Run: pip install google-search-results")


@dataclass
class EmployerData:
    """Major employer information for PPO pitch."""
    name: str
    industry: str = ""
    estimated_employees: str = ""
    likely_ppo: bool = True  # Large employers typically offer PPO


@dataclass  
class EconomicProfile:
    """Economic profile for a city."""
    city: str
    state: str
    median_income: Optional[str] = None
    income_bracket: str = "middle"  # low, middle, upper-middle, high
    major_employers: List[EmployerData] = None
    employment_sectors: List[str] = None
    
    def __post_init__(self):
        if self.major_employers is None:
            self.major_employers = []
        if self.employment_sectors is None:
            self.employment_sectors = []


@dataclass
class CommuteData:
    """Commute/distance data for geographic targeting."""
    from_city: str
    to_city: str
    drive_time: Optional[str] = None
    distance: Optional[str] = None
    route_description: str = ""


@dataclass
class LocalProvider:
    """Local mental health provider for aftercare network."""
    name: str
    specialty: str = ""
    address: str = ""
    phone: str = ""


@dataclass
class PrivatePayData:
    """Complete private pay data package for a city."""
    city: str
    state: str
    fetched_at: str
    economic_profile: EconomicProfile = None
    commute_data: CommuteData = None
    local_providers: List[LocalProvider] = None
    raw_serp_results: Dict = None
    
    def __post_init__(self):
        if self.local_providers is None:
            self.local_providers = []
        if self.raw_serp_results is None:
            self.raw_serp_results = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage."""
        return {
            "city": self.city,
            "state": self.state,
            "fetched_at": self.fetched_at,
            "economic_profile": asdict(self.economic_profile) if self.economic_profile else None,
            "commute_data": asdict(self.commute_data) if self.commute_data else None,
            "local_providers": [asdict(p) for p in self.local_providers],
            "raw_serp_results": self.raw_serp_results
        }
    
    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict(), indent=2)


# Income bracket thresholds (based on US median ~$75k)
INCOME_BRACKETS = {
    "low": (0, 50000),
    "middle": (50000, 85000),
    "upper-middle": (85000, 150000),
    "high": (150000, float('inf'))
}

# Industries likely to offer PPO insurance
PPO_LIKELY_INDUSTRIES = [
    "pharmaceutical", "finance", "banking", "insurance", "technology",
    "healthcare", "legal", "consulting", "engineering", "aerospace",
    "telecommunications", "energy", "manufacturing", "government"
]

# Target facility location (for commute calculations)
FACILITY_LOCATION = "Toms River, NJ"


def _parse_income(text: str) -> Optional[int]:
    """Extract numeric income value from text."""
    # Look for patterns like "$75,000" or "75000" or "$75K"
    patterns = [
        r'\$?([\d,]+)\s*(?:per year|annually|/year)?',
        r'\$?([\d]+)[kK]',
        r'median.*?\$?([\d,]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.replace(',', ''))
        if match:
            value = match.group(1).replace(',', '')
            if 'k' in text.lower() or 'K' in text:
                return int(float(value) * 1000)
            return int(value)
    return None


def _determine_income_bracket(income: int) -> str:
    """Determine income bracket from numeric value."""
    for bracket, (low, high) in INCOME_BRACKETS.items():
        if low <= income < high:
            return bracket
    return "middle"


def _extract_employers(organic_results: List[Dict]) -> List[EmployerData]:
    """Extract employer names from SERP organic results."""
    employers = []
    seen_names = set()
    
    # Common employer keywords to look for
    employer_patterns = [
        r'([A-Z][A-Za-z\s&]+(?:Inc|Corp|LLC|Company|Co\.|Hospital|University|College|Bank|Insurance))',
        r'(?:employer|company|corporation|organization):\s*([A-Za-z\s&]+)',
    ]
    
    for result in organic_results[:10]:
        snippet = result.get('snippet', '')
        title = result.get('title', '')
        combined = f"{title} {snippet}"
        
        # Look for company names
        for pattern in employer_patterns:
            matches = re.findall(pattern, combined)
            for match in matches:
                name = match.strip()
                if len(name) > 3 and name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    
                    # Determine if likely PPO based on industry keywords
                    likely_ppo = any(
                        ind in combined.lower() 
                        for ind in PPO_LIKELY_INDUSTRIES
                    )
                    
                    employers.append(EmployerData(
                        name=name,
                        likely_ppo=likely_ppo
                    ))
        
        # Also check for list items in snippets
        list_items = re.findall(r'(?:^|\d\.\s*|•\s*)([A-Z][A-Za-z\s&]+)', snippet)
        for item in list_items:
            item = item.strip()
            if len(item) > 3 and item.lower() not in seen_names:
                seen_names.add(item.lower())
                employers.append(EmployerData(name=item))
    
    return employers[:10]  # Return top 10


def _extract_drive_time(organic_results: List[Dict]) -> Optional[str]:
    """Extract drive time from SERP results."""
    patterns = [
        r'(\d+)\s*(?:hour|hr)s?\s*(?:and\s*)?(\d+)?\s*(?:minute|min)s?',
        r'(\d+)\s*(?:minute|min)s?\s*(?:drive)?',
        r'(\d+\.?\d*)\s*(?:hour|hr)s?',
    ]
    
    for result in organic_results[:5]:
        snippet = result.get('snippet', '')
        
        for pattern in patterns:
            match = re.search(pattern, snippet, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2 and groups[1]:
                    return f"{groups[0]} hr {groups[1]} min"
                elif 'hour' in pattern.lower() or 'hr' in pattern.lower():
                    return f"{groups[0]} hours"
                else:
                    return f"{groups[0]} minutes"
    
    return None


def _extract_local_providers(organic_results: List[Dict], local_results: List[Dict] = None) -> List[LocalProvider]:
    """Extract local mental health providers from SERP results."""
    providers = []
    seen_names = set()
    
    # Process local pack results first (higher quality)
    if local_results:
        for result in local_results[:5]:
            name = result.get('title', '').strip()
            if name and name.lower() not in seen_names:
                seen_names.add(name.lower())
                providers.append(LocalProvider(
                    name=name,
                    address=result.get('address', ''),
                    phone=result.get('phone', ''),
                    specialty="Mental Health Counseling"
                ))
    
    # Also check organic results
    for result in organic_results[:10]:
        title = result.get('title', '').strip()
        
        # Look for provider indicators
        if any(term in title.lower() for term in ['counseling', 'therapy', 'psycholog', 'mental health', 'behavioral']):
            if title and title.lower() not in seen_names:
                seen_names.add(title.lower())
                providers.append(LocalProvider(
                    name=title,
                    specialty="Mental Health Services"
                ))
    
    return providers[:8]  # Return top 8


def fetch_serp_data(query: str, api_key: str, location: str = None) -> Dict:
    """
    Execute a single SERP query via SerpAPI.
    Returns raw results dictionary.
    """
    if not SERPAPI_AVAILABLE:
        return {"error": "SerpAPI not installed"}
    
    if not api_key:
        return {"error": "No API key provided"}
    
    params = {
        "q": query,
        "api_key": api_key,
        "engine": "google",
        "num": 10,
        "gl": "us",
        "hl": "en"
    }
    
    if location:
        params["location"] = location
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        return results
    except Exception as e:
        return {"error": str(e)}


def fetch_private_pay_data(
    city: str, 
    state: str, 
    api_key: str,
    facility_location: str = FACILITY_LOCATION,
    delay_between_searches: float = 1.0
) -> PrivatePayData:
    """
    Fetch comprehensive private pay data for a city.
    
    Constraint: Does NOT search for "Rehabs in [City]" to avoid competitors.
    
    Searches performed:
    1. Economics: "Major employers in [City] [State]" (For PPO benefits pitch)
    2. Income: "Median household income [City] [State]" (For tone adjustment)
    3. Commute: "Drive time from [City] [State] to [Facility]" (Bridge argument)
    4. Local: "Private mental health counselors [City]" (Aftercare network)
    
    Args:
        city: Target city name
        state: State abbreviation
        api_key: SerpAPI key
        facility_location: Treatment facility location for commute calc
        delay_between_searches: Delay between API calls (rate limiting)
    
    Returns:
        PrivatePayData object with all collected data
    """
    location_str = f"{city}, {state}"
    
    # Initialize result
    result = PrivatePayData(
        city=city,
        state=state,
        fetched_at=datetime.now().isoformat(),
        economic_profile=EconomicProfile(city=city, state=state),
        commute_data=CommuteData(from_city=location_str, to_city=facility_location),
        local_providers=[],
        raw_serp_results={}
    )
    
    # Search 1: Major Employers (PPO benefits pitch)
    employer_query = f"Major employers in {city} {state}"
    employer_results = fetch_serp_data(employer_query, api_key, location_str)
    result.raw_serp_results["employers"] = employer_results
    
    if "error" not in employer_results:
        organic = employer_results.get("organic_results", [])
        employers = _extract_employers(organic)
        result.economic_profile.major_employers = employers
        
        # Extract industry sectors
        sectors = set()
        for emp in employers:
            if emp.industry:
                sectors.add(emp.industry)
        result.economic_profile.employment_sectors = list(sectors)
    
    time.sleep(delay_between_searches)
    
    # Search 2: Median Income (Tone adjustment)
    income_query = f"Median household income {city} {state}"
    income_results = fetch_serp_data(income_query, api_key)
    result.raw_serp_results["income"] = income_results
    
    if "error" not in income_results:
        # Check knowledge graph first
        kg = income_results.get("knowledge_graph", {})
        if kg:
            income_text = kg.get("description", "") or kg.get("snippet", "")
            income = _parse_income(income_text)
            if income:
                result.economic_profile.median_income = f"${income:,}"
                result.economic_profile.income_bracket = _determine_income_bracket(income)
        
        # Fall back to organic results
        if not result.economic_profile.median_income:
            organic = income_results.get("organic_results", [])
            for r in organic[:3]:
                snippet = r.get("snippet", "")
                income = _parse_income(snippet)
                if income and 20000 < income < 500000:  # Sanity check
                    result.economic_profile.median_income = f"${income:,}"
                    result.economic_profile.income_bracket = _determine_income_bracket(income)
                    break
    
    time.sleep(delay_between_searches)
    
    # Search 3: Drive Time (Bridge argument)
    commute_query = f"Drive time from {city} {state} to {facility_location}"
    commute_results = fetch_serp_data(commute_query, api_key)
    result.raw_serp_results["commute"] = commute_results
    
    if "error" not in commute_results:
        organic = commute_results.get("organic_results", [])
        drive_time = _extract_drive_time(organic)
        if drive_time:
            result.commute_data.drive_time = drive_time
        
        # Check for distance in knowledge graph
        kg = commute_results.get("knowledge_graph", {})
        if kg:
            distance = kg.get("distance", "")
            if distance:
                result.commute_data.distance = distance
    
    time.sleep(delay_between_searches)
    
    # Search 4: Local Mental Health Counselors (Aftercare network)
    local_query = f"Private mental health counselors {city} {state}"
    local_results = fetch_serp_data(local_query, api_key, location_str)
    result.raw_serp_results["local_providers"] = local_results
    
    if "error" not in local_results:
        organic = local_results.get("organic_results", [])
        local_pack = local_results.get("local_results", {}).get("places", [])
        providers = _extract_local_providers(organic, local_pack)
        result.local_providers = providers
    
    return result


def fetch_batch_private_pay_data(
    cities: List[Dict[str, str]],
    api_key: str,
    progress_callback=None,
    log_callback=None
) -> List[PrivatePayData]:
    """
    Fetch private pay data for multiple cities.
    
    Args:
        cities: List of dicts with 'city' and 'state' keys
        api_key: SerpAPI key
        progress_callback: Function to call with progress (0-1)
        log_callback: Function to call with log messages
    
    Returns:
        List of PrivatePayData objects
    """
    results = []
    total = len(cities)
    
    for i, city_data in enumerate(cities):
        city = city_data.get('city', '')
        state = city_data.get('state', '')
        
        if log_callback:
            log_callback(f"Fetching data for {city}, {state}...")
        
        try:
            data = fetch_private_pay_data(city, state, api_key)
            results.append(data)
            
            # Log findings
            if log_callback:
                if data.economic_profile.major_employers:
                    top_employer = data.economic_profile.major_employers[0].name
                    log_callback(f"  ✓ Found Employer: {top_employer}")
                if data.economic_profile.median_income:
                    log_callback(f"  ✓ Median Income: {data.economic_profile.median_income}")
                if data.commute_data.drive_time:
                    log_callback(f"  ✓ Drive Time to Facility: {data.commute_data.drive_time}")
                if data.local_providers:
                    log_callback(f"  ✓ Found {len(data.local_providers)} local providers")
        
        except Exception as e:
            if log_callback:
                log_callback(f"  ✗ Error: {str(e)}")
            results.append(PrivatePayData(
                city=city,
                state=state,
                fetched_at=datetime.now().isoformat()
            ))
        
        if progress_callback:
            progress_callback((i + 1) / total)
        
        # Rate limiting between cities
        if i < total - 1:
            time.sleep(2)
    
    return results


def generate_ppo_pitch_points(data: PrivatePayData) -> List[str]:
    """
    Generate PPO-focused pitch points from collected data.
    Used for content generation.
    """
    points = []
    
    # Employer-based pitch
    if data.economic_profile and data.economic_profile.major_employers:
        ppo_employers = [e for e in data.economic_profile.major_employers if e.likely_ppo]
        if ppo_employers:
            emp_names = ", ".join([e.name for e in ppo_employers[:3]])
            points.append(
                f"Many {data.city} residents work for major employers like {emp_names}, "
                f"which typically offer PPO insurance plans that cover private treatment."
            )
    
    # Income-based pitch
    if data.economic_profile and data.economic_profile.income_bracket:
        bracket = data.economic_profile.income_bracket
        if bracket in ["upper-middle", "high"]:
            points.append(
                f"With a {bracket.replace('-', ' ')} income profile, {data.city} families "
                f"often have access to premium PPO plans that provide extensive treatment coverage."
            )
        elif bracket == "middle":
            points.append(
                f"Many {data.city} families have employer-sponsored PPO insurance "
                f"that may cover more of treatment costs than they realize."
            )
    
    # Commute-based pitch (the "bridge" argument)
    if data.commute_data and data.commute_data.drive_time:
        points.append(
            f"Our facility is just {data.commute_data.drive_time} from {data.city}, "
            f"close enough for family visits while providing the distance needed for focused recovery."
        )
    
    # Aftercare network pitch
    if data.local_providers:
        points.append(
            f"We coordinate with {len(data.local_providers)} local mental health providers "
            f"in {data.city} to ensure seamless aftercare support."
        )
    
    return points


def test_logic():
    """Test function (requires API key)."""
    print("Logic module loaded successfully.")
    print(f"SerpAPI available: {SERPAPI_AVAILABLE}")
    print("\nTo test with real data, call:")
    print("  data = fetch_private_pay_data('Newark', 'NJ', 'YOUR_API_KEY')")


if __name__ == "__main__":
    test_logic()
