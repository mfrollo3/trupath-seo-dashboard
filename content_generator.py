"""
content_generator.py - LLM-Powered Content Generator for TruPathNJ
Generates complete HTML pages for both City Guides and Topic Guides.
"""

import json
import re
from typing import Dict, Optional, Any
from datetime import datetime
from string import Template

# Try to import LLM clients
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

CITY_SYSTEM_PROMPT = """You are a Private Insurance Benefits Navigator.
TONE: Professional, Objective, Empathetic, Exclusive.
AUDIENCE: Executives, Professionals with PPO plans.
CONSTRAINTS: NEVER mention Medicaid, Free, State-Funded.
GOAL: Explain how to use PPO insurance to get private care away from home."""

TOPIC_SYSTEM_PROMPT = """You are an Expert Medical Content Strategist (E-E-A-T focused).
TONE: Authoritative, Compassionate, Medically Accurate, Clear.
AUDIENCE: Individuals seeking answers about addiction symptoms, timelines, or insurance.
GOAL: Answer the user's specific questions directly. Win the 'Featured Snippet'."""

# =============================================================================
# HTML TEMPLATES (Simplified for Universal Use)
# =============================================================================

HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>${title_tag}</title>
    <meta name="description" content="${meta_description}">
    
    <style>
        /* Base styles that WordPress will inherit or override */
        .tp-container { max-width: 800px; margin: 0 auto; }
        .tp-card { background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #2c5282; margin: 20px 0; }
        .tp-stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .tp-stat-box { background: white; padding: 15px; border: 1px solid #e2e8f0; text-align: center; border-radius: 6px; }
        .tp-stat-val { font-size: 1.5rem; font-weight: bold; color: #2c5282; }
        .tp-cta-box { background: #ebf8ff; padding: 30px; text-align: center; border-radius: 8px; margin-top: 40px; }
        .tp-cta-btn { display: inline-block; background: #2c5282; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; }
        h2 { color: #2d3748; margin-top: 40px; }
        ul, ol { margin-bottom: 20px; }
        li { margin-bottom: 10px; }
    </style>
</head>
<body>

<div class="tp-container">
    <h1>${h1_title}</h1>
    
    ${main_content}
    
    <div class="tp-cta-box">
        <h3>${cta_headline}</h3>
        <p>${cta_text}</p>
        <p style="font-size: 1.25rem; font-weight: bold;">${phone_number}</p>
    </div>
</div>

</body>
</html>""")

# =============================================================================
# PROMPT BUILDERS
# =============================================================================

def build_city_prompt(city: str, state: str, keyword: str, serp_data: Dict, brand: str) -> str:
    """Builds the prompt for a Local City Page."""
    economic = serp_data.get("economic_profile", {})
    commute = serp_data.get("commute_data", {})
    
    prompt = f"""
    Write a "Private PPO Resource Guide" for {city}, {state}.
    Keyword: {keyword}
    Brand: {brand}
    
    DATA TO USE:
    - Employers: {', '.join([e['name'] for e in economic.get('major_employers', [])[:3]])}
    - Commute: {commute.get('drive_time', '1 hour')} to Toms River.
    
    STRUCTURE (Return HTML Only):
    1. <h2>Navigating Private Care in {city}</h2>
       - Hook: Connect local employers to PPO benefits. Mention privacy needs.
    2. <h2>The Clinical Advantage of Distance</h2>
       - Use the commute time ({commute.get('drive_time')}) to explain why leaving {city} helps recovery.
    3. <h2>Understanding Your PPO Coverage</h2>
       - Explain the verification process.
    """
    return prompt

def build_topic_prompt(topic: str, serp_data: Dict, brand: str) -> str:
    """Builds the prompt for a Topic/Informational Page."""
    paa_questions = [q['question'] for q in serp_data.get('paa', [])]
    related_terms = serp_data.get('related_searches', [])
    
    prompt = f"""
    Write a comprehensive "Helpful Content" guide for the topic: "{topic}".
    Brand: {brand}
    
    USER QUESTIONS (You MUST answer these in the text or FAQ):
    {chr(10).join(['- ' + q for q in paa_questions])}
    
    RELATED SUBTOPICS (Use for H2s):
    {', '.join(related_terms[:5])}
    
    STRUCTURE (Return HTML Only):
    1. <h2>Direct Answer</h2>
       - Give a clear, direct answer to the main query immediately (for Featured Snippets).
    2. <h2>Detailed Breakdown</h2>
       - Use the related subtopics to structure deep dive sections.
    3. <h2>Frequently Asked Questions</h2>
       - Answer 3-4 of the User Questions provided above concisely.
    """
    return prompt

# =============================================================================
# GENERATION LOGIC
# =============================================================================

def call_llm(prompt: str, system: str, api_key: str, provider: str) -> str:
    if not api_key:
        return "<p>[Preview Mode: No API Key Provided. Content would appear here.]</p>"
        
    try:
        if provider == "anthropic" and ANTHROPIC_AVAILABLE:
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                system=system,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
            
        elif provider == "openai" and OPENAI_AVAILABLE:
            client = openai.OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ]
            )
            return resp.choices[0].message.content
            
    except Exception as e:
        return f"<p>Error generating content: {str(e)}</p>"
    
    return "<p>LLM Provider not found.</p>"

def generate_page_html(page_data: Dict[str, Any], api_key: str, provider: str = "openai", brand: str = "TruPath", phone_number: str = "555-555-5555") -> str:
    """Master generation function that switches between City and Topic modes."""
    
    page_type = page_data.get("page_type", "Spoke").lower()
    serp_data = page_data.get("serp_data", {})
    
    # 1. Determine Mode
    if page_type == "topic":
        # TOPIC MODE
        topic = page_data.get("keyword")
        prompt = build_topic_prompt(topic, serp_data, brand)
        system_prompt = TOPIC_SYSTEM_PROMPT
        h1 = f"{topic.title()}: A Complete Guide"
        cta_head = "Need Professional Help?"
        cta_text = "Our medical team is available 24/7 to answer your questions."
    else:
        # CITY MODE
        city = page_data.get("city")
        state = page_data.get("state")
        keyword = page_data.get("keyword")
        prompt = build_city_prompt(city, state, keyword, serp_data, brand)
        system_prompt = CITY_SYSTEM_PROMPT
        h1 = page_data.get("titles", {}).get("h1_title", f"Private Rehab in {city}")
        cta_head = f"Private Care for {city} Residents"
        cta_text = "Verify your PPO insurance confidentially."

    # 2. Generate Content
    main_content = call_llm(prompt, system_prompt, api_key, provider)
    
    # 3. Clean Content (Remove markdown code blocks)
    main_content = re.sub(r'```html', '', main_content)
    main_content = re.sub(r'```', '', main_content)
    
    # 4. Assemble HTML
    html = HTML_TEMPLATE.substitute(
        title_tag=h1 + f" | {brand}",
        meta_description=f"Learn more about {h1}. {brand} provides expert resources.",
        h1_title=h1,
        main_content=main_content,
        cta_headline=cta_head,
        cta_text=cta_text,
        phone_number=phone_number
    )
    
    return html
