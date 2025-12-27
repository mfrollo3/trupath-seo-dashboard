"""
logic.py - Data Scraper for TruPathNJ
Handles SerpAPI connections for both City Data (Employers) and Topic Data (PAA).
"""

import os
from typing import Dict, List, Optional

try:
    import serpapi
    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False

class PrivatePayData:
    def __init__(self):
        self.economic_profile = {}
        self.commute_data = {}
        self.local_providers = []
    
    def to_dict(self):
        return {
            "economic_profile": self.economic_profile,
            "commute_data": self.commute_data,
            "local_providers": self.local_providers
        }

def fetch_private_pay_data(city: str, state: str, api_key: str, facility_location: str = "Toms River, NJ") -> PrivatePayData:
    """
    Scrape 'City Mode' data: Employers, Income, Commute.
    """
    data = PrivatePayData()
    if not api_key or not SERPAPI_AVAILABLE:
        return data

    try:
        client = serpapi.Client(api_key=api_key)
        
        # 1. Economic Data (Employers)
        emp_query = f"largest employers in {city} {state}"
        emp_results = client.search({
            "engine": "google",
            "q": emp_query,
            "gl": "us",
            "hl": "en"
        })
        
        employers = []
        if "organic_results" in emp_results:
            for r in emp_results["organic_results"][:5]:
                employers.append({"name": r.get("title"), "likely_ppo": True})
        
        data.economic_profile = {
            "median_income": "Check Local Data", # Placeholder if scraping fails
            "income_bracket": "middle-upper",
            "major_employers": employers
        }

        # 2. Commute Data
        # Note: SerpApi Maps is expensive/complex, using a rough heuristic fallback or simple search
        commute_query = f"drive time from {city} {state} to {facility_location}"
        commute_results = client.search({"engine": "google", "q": commute_query})
        
        drive_time = "approx. 1 hour"
        if "answer_box" in commute_results:
            drive_time = commute_results["answer_box"].get("snippet", drive_time)
        elif "organic_results" in commute_results:
             drive_time = commute_results["organic_results"][0].get("snippet", drive_time)

        data.commute_data = {
            "drive_time": drive_time,
            "to_city": facility_location,
            "distance": "driving distance"
        }

    except Exception as e:
        print(f"Error fetching city data: {e}")

    return data


def fetch_topic_data(keyword: str, api_key: str) -> Dict:
    """
    Scrape 'Topic Mode' data: People Also Ask & Related Searches.
    """
    if not api_key or not SERPAPI_AVAILABLE:
        return {}

    try:
        client = serpapi.Client(api_key=api_key)
        results = client.search({
            "engine": "google",
            "q": keyword,
            "gl": "us",
            "hl": "en"
        })

        # 1. People Also Ask (The Goldmine)
        paa = []
        if "related_questions" in results:
            for q in results["related_questions"]:
                paa.append({
                    "question": q.get("question"),
                    "snippet": q.get("snippet"),
                    "link": q.get("link")
                })

        # 2. Related Searches (For H2 structure)
        related = []
        if "related_searches" in results:
            for r in results["related_searches"]:
                related.append(r.get("query"))

        return {
            "topic": keyword,
            "paa": paa[:8],
            "related_searches": related[:10],
            "data_type": "topic"
        }

    except Exception as e:
        print(f"Error fetching topic data: {e}")
        return {"error": str(e), "data_type": "topic"}


def generate_ppo_pitch_points(data: PrivatePayData) -> List[str]:
    """Generate bullet points for the sales pitch based on scraped data."""
    points = []
    if data.economic_profile.get("major_employers"):
        emp = data.economic_profile["major_employers"][0]["name"]
        points.append(f"Employees of {emp} may have full PPO coverage.")
    
    if data.commute_data.get("drive_time"):
        points.append(f"Located {data.commute_data['drive_time']} away - ensuring privacy.")
        
    return points
