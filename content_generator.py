"""
content_generator.py - LLM-Powered Content Generator for TruPathNJ
Generates complete HTML pages for Private PPO Resource Guides.

Strategy:
- Role: Private Insurance Benefits Navigator (NOT doctor, NOT salesperson)
- Tone: Professional, Objective, Empathetic, Exclusive
- Target: Executives, Professionals, Parents with PPO plans
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
# SYSTEM PROMPT - The Core of Our Content Strategy
# =============================================================================

SYSTEM_PROMPT = """You are a Private Insurance Benefits Navigator specializing in behavioral health coverage for New Jersey residents. 

CRITICAL IDENTITY RULES:
- You are NOT a doctor, therapist, or medical professional
- You are NOT a salesperson or marketer
- You ARE a knowledgeable guide helping professionals navigate private insurance options
- You speak as an objective third-party resource, not as a treatment facility

TONE & VOICE:
- Professional: Write like a McKinsey consultant, not a billboard
- Objective: Present information factually, let benefits speak for themselves
- Empathetic: Acknowledge the difficulty of seeking help while maintaining dignity
- Exclusive: Subtly convey that this is for people with quality coverage options

TARGET AUDIENCE:
- Corporate executives concerned about confidentiality
- Professionals (lawyers, doctors, finance) protecting their licenses
- Parents with employer-sponsored PPO plans seeking quality care for family
- High-net-worth individuals valuing privacy and discretion

FORBIDDEN WORDS & PHRASES (NEVER USE):
- "Free" or "no cost" or "affordable"
- "Medicaid" or "Medicare" or "state-funded"
- "Charity care" or "sliding scale"
- "Welcome to our rehab" or "our facility welcomes you"
- "Call now!" or aggressive sales language
- "Addiction" in isolation (use "substance use challenges" or "recovery needs")
- "Addict" or "alcoholic" as nouns

PREFERRED LANGUAGE:
- Instead of "Welcome to our rehab" → "Navigating private care options"
- Instead of "Call now" → "Confidential consultation available"
- Instead of "Addict" → "Individuals facing substance use challenges"
- Instead of "Treatment" alone → "Evidence-based clinical programs"
- Instead of "Cheap/Affordable" → "Covered by most PPO plans"

THE BRIDGE ARGUMENT (CRITICAL):
When discussing why someone might seek treatment outside their home city, frame it as a CLINICAL ADVANTAGE:
- "Distance creates safety" - removes triggers and enables focus
- "Geographic separation supports recovery" - away from enabling relationships
- "Privacy through location" - less likely to encounter colleagues or neighbors
- Use the commute time data to show it's close enough for family visits but far enough for focused healing

CONTENT STRUCTURE REQUIREMENTS:
1. Lead with empathy and understanding, not sales
2. Establish credibility through data and specifics (employer info, income context)
3. Explain PPO benefits in practical terms
4. Use the Bridge argument naturally
5. End with a soft, dignified call to action

FORMATTING RULES:
- Write in clean, professional prose
- Use short paragraphs (2-3 sentences max)
- Include specific data points when provided
- Create scannable content with clear section breaks
- Maintain a reading level appropriate for educated professionals"""


# =============================================================================
# HTML TEMPLATES
# =============================================================================

HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="${meta_description}">
    <meta name="robots" content="index, follow">
    
    <!-- Open Graph -->
    <meta property="og:title" content="${og_title}">
    <meta property="og:description" content="${meta_description}">
    <meta property="og:type" content="website">
    <meta property="og:locale" content="en_US">
    
    <title>${title_tag}</title>
    
    <!-- Schema.org Markup -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "MedicalWebPage",
        "name": "${schema_headline}",
        "description": "${schema_description}",
        "about": {
            "@type": "MedicalCondition",
            "name": "Substance Use Disorder",
            "sameAs": "${wikidata_url}"
        },
        "audience": {
            "@type": "PeopleAudience",
            "audienceType": "Individuals with PPO Insurance Coverage"
        },
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": ["h1", ".local-hook", ".private-path"]
        },
        "mainEntity": {
            "@type": "LocalBusiness",
            "name": "${brand}",
            "areaServed": {
                "@type": "City",
                "name": "${city}",
                "sameAs": "${city_wiki_url}"
            }
        }
    }
    </script>
    
    <!-- VideoObject Schema Placeholder -->
    <script type="application/ld+json" id="video-schema">
    {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": "Understanding Private PPO Treatment Options in ${city}",
        "description": "A guide to navigating private insurance coverage for behavioral health treatment near ${city}.",
        "thumbnailUrl": "",
        "uploadDate": "${current_date}",
        "contentUrl": "",
        "embedUrl": ""
    }
    </script>
    
    <style>
        :root {
            --primary-color: #1a365d;
            --secondary-color: #2c5282;
            --accent-color: #4299e1;
            --bg-light: #f7fafc;
            --text-dark: #1a202c;
            --text-muted: #4a5568;
            --border-color: #e2e8f0;
            --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Georgia', 'Times New Roman', serif;
            line-height: 1.7;
            color: var(--text-dark);
            background-color: #ffffff;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 0 24px;
        }
        
        /* Header */
        header {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white;
            padding: 48px 0;
            text-align: center;
        }
        
        h1 {
            font-size: 2.25rem;
            font-weight: 600;
            line-height: 1.3;
            margin-bottom: 16px;
            font-family: 'Helvetica Neue', Arial, sans-serif;
        }
        
        .subtitle {
            font-size: 1.1rem;
            opacity: 0.9;
            font-style: italic;
        }
        
        /* Sections */
        section {
            padding: 48px 0;
            border-bottom: 1px solid var(--border-color);
        }
        
        section:last-of-type {
            border-bottom: none;
        }
        
        h2 {
            font-size: 1.5rem;
            color: var(--primary-color);
            margin-bottom: 24px;
            font-family: 'Helvetica Neue', Arial, sans-serif;
        }
        
        p {
            margin-bottom: 16px;
            color: var(--text-dark);
        }
        
        /* Local Hook Section */
        .local-hook {
            background-color: var(--bg-light);
        }
        
        .local-hook-content {
            padding: 32px;
            border-left: 4px solid var(--accent-color);
            background: white;
            box-shadow: var(--card-shadow);
        }
        
        /* Data Cards */
        .data-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 24px;
            margin: 32px 0;
        }
        
        .data-card {
            background: white;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 24px;
            text-align: center;
            box-shadow: var(--card-shadow);
        }
        
        .data-card-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--primary-color);
            font-family: 'Helvetica Neue', Arial, sans-serif;
        }
        
        .data-card-label {
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-top: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Private Path Section */
        .private-path {
            background: white;
        }
        
        .step-list {
            list-style: none;
            counter-reset: steps;
        }
        
        .step-list li {
            counter-increment: steps;
            padding: 16px 0 16px 60px;
            position: relative;
            border-bottom: 1px solid var(--border-color);
        }
        
        .step-list li:last-child {
            border-bottom: none;
        }
        
        .step-list li::before {
            content: counter(steps);
            position: absolute;
            left: 0;
            top: 16px;
            width: 40px;
            height: 40px;
            background: var(--primary-color);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-family: 'Helvetica Neue', Arial, sans-serif;
        }
        
        /* Video Section */
        .video-section {
            background-color: var(--bg-light);
        }
        
        #video-embed {
            background: var(--primary-color);
            color: white;
            padding: 80px 24px;
            text-align: center;
            border-radius: 8px;
        }
        
        #video-embed p {
            color: rgba(255,255,255,0.8);
        }
        
        /* Employer Mention */
        .employer-highlight {
            background: linear-gradient(135deg, #ebf8ff 0%, #e6fffa 100%);
            padding: 24px;
            border-radius: 8px;
            margin: 24px 0;
            border-left: 4px solid var(--accent-color);
        }
        
        /* CTA Bar */
        .cta-bar {
            position: sticky;
            bottom: 0;
            background: var(--primary-color);
            color: white;
            padding: 16px 0;
            text-align: center;
            box-shadow: 0 -4px 12px rgba(0,0,0,0.15);
            z-index: 100;
        }
        
        .cta-bar p {
            color: white;
            margin: 0;
            font-family: 'Helvetica Neue', Arial, sans-serif;
        }
        
        .cta-phone {
            font-size: 1.25rem;
            font-weight: 600;
            letter-spacing: 1px;
        }
        
        .cta-note {
            font-size: 0.875rem;
            opacity: 0.85;
            margin-top: 4px;
        }
        
        /* Footer */
        footer {
            background: var(--text-dark);
            color: white;
            padding: 48px 0;
            margin-top: 48px;
        }
        
        footer p {
            color: rgba(255,255,255,0.7);
            font-size: 0.875rem;
            text-align: center;
        }
        
        /* Responsive */
        @media (max-width: 640px) {
            h1 { font-size: 1.75rem; }
            .data-cards { grid-template-columns: 1fr; }
            section { padding: 32px 0; }
        }
    </style>
</head>
<body>

<header>
    <div class="container">
        <h1>${h1_title}</h1>
        <p class="subtitle">${subtitle}</p>
    </div>
</header>

<main>
    <!-- Section 1: Local Hook -->
    <section class="local-hook">
        <div class="container">
            <div class="local-hook-content">
                ${local_hook_content}
            </div>
        </div>
    </section>
    
    <!-- Section 2: Data Cards -->
    <section class="data-section">
        <div class="container">
            <h2>Understanding ${city}'s Demographics</h2>
            <div class="data-cards">
                ${data_cards_html}
            </div>
            ${data_commentary}
        </div>
    </section>
    
    <!-- Section 3: The Private Path -->
    <section class="private-path">
        <div class="container">
            <h2>The Private Insurance Path</h2>
            ${private_path_content}
        </div>
    </section>
    
    <!-- Section 4: Video Slot -->
    <section class="video-section">
        <div class="container">
            <h2>Understanding Your Options</h2>
            <div id="video-embed">
                <p>Video content coming soon</p>
                <p style="font-size: 0.875rem; margin-top: 8px;">A confidential guide to PPO coverage for ${city} residents</p>
            </div>
        </div>
    </section>
    
    <!-- The Bridge Argument Section -->
    <section class="bridge-section">
        <div class="container">
            <h2>Why Location Matters for Recovery</h2>
            ${bridge_content}
        </div>
    </section>
</main>

<!-- CTA Bar -->
<div class="cta-bar">
    <div class="container">
        <p class="cta-phone">Confidential PPO Verification: ${phone_number}</p>
        <p class="cta-note">Private consultation • Insurance verification • No obligation</p>
    </div>
</div>

<footer>
    <div class="container">
        <p>&copy; ${current_year} ${brand}. Private Insurance Navigation Resources.</p>
        <p style="margin-top: 8px;">This page provides general information about private insurance options and does not constitute medical advice.</p>
    </div>
</footer>

</body>
</html>""")


# =============================================================================
# CONTENT GENERATION PROMPTS
# =============================================================================

def build_content_prompt(
    city: str,
    state: str,
    keyword: str,
    serp_data: Dict,
    titles: Dict,
    entity_variants: list,
    brand: str
) -> str:
    """Build the user prompt for content generation."""
    
    # Extract data safely
    economic = serp_data.get("economic_profile", {}) or {}
    commute = serp_data.get("commute_data", {}) or {}
    employers = economic.get("major_employers", []) or []
    local_providers = serp_data.get("local_providers", []) or []
    pitch_points = serp_data.get("pitch_points", []) or []
    
    # Format employer list
    employer_names = []
    for emp in employers[:5]:
        if isinstance(emp, dict):
            employer_names.append(emp.get("name", ""))
        else:
            employer_names.append(str(emp))
    employer_list = ", ".join([e for e in employer_names if e])
    
    # Format local providers
    provider_names = []
    for prov in local_providers[:3]:
        if isinstance(prov, dict):
            provider_names.append(prov.get("name", ""))
        else:
            provider_names.append(str(prov))
    provider_list = ", ".join([p for p in provider_names if p])
    
    prompt = f"""Generate content for a Private PPO Resource Guide page for {city}, {state}.

TARGET KEYWORD: {keyword}
BRAND: {brand}

=== DATA TO INCORPORATE ===

ECONOMIC PROFILE:
- Median Household Income: {economic.get('median_income', 'Not available')}
- Income Bracket: {economic.get('income_bracket', 'middle')}
- Major Employers: {employer_list if employer_list else 'Various local employers'}

COMMUTE DATA:
- Drive Time to Facility: {commute.get('drive_time', 'Approximately 1 hour')}
- Distance: {commute.get('distance', 'Within driving distance')}
- Facility Location: {commute.get('to_city', 'Toms River, NJ')}

LOCAL AFTERCARE PROVIDERS:
{provider_list if provider_list else 'Multiple qualified providers in the area'}

ENTITY VARIANTS TO USE:
{', '.join(entity_variants[:5]) if entity_variants else 'Substance Abuse Treatment, Addiction Recovery, Behavioral Health'}

PITCH POINTS TO INCORPORATE:
{chr(10).join('- ' + p for p in pitch_points) if pitch_points else '- Many residents have employer-sponsored PPO coverage'}

=== CONTENT SECTIONS TO WRITE ===

Please write the following sections in clean HTML (no markdown, just HTML tags):

1. LOCAL HOOK (2-3 paragraphs)
Write content that connects with {city} residents specifically.
- Reference the major employers if available (e.g., "Professionals at [Employer] understand...")
- Acknowledge the unique privacy concerns of professionals in this area
- Use empathetic, understanding language
- Wrap in <p> tags only

2. DATA COMMENTARY (1-2 paragraphs)
Write a brief analysis of what the demographic data means for residents seeking care.
- Reference the income bracket naturally
- Explain how this relates to insurance options
- Wrap in <p> tags only

3. PRIVATE PATH CONTENT (list of 4-5 steps)
Explain the process of using PPO insurance for treatment.
- Each step should be 1-2 sentences
- Format as: <ol class="step-list"><li>Step content...</li></ol>
- Include: verification, assessment, admission, treatment, aftercare

4. BRIDGE ARGUMENT (2-3 paragraphs)
Explain why seeking treatment OUTSIDE {city} is actually beneficial.
- Use the commute time data ({commute.get('drive_time', 'about an hour')})
- Frame distance as a clinical advantage
- Mention proximity for family visits
- Discuss privacy benefits of geographic separation
- Wrap in <p> tags only

=== OUTPUT FORMAT ===

Return ONLY the HTML content sections, clearly labeled:

[LOCAL_HOOK]
<p>Content here...</p>

[DATA_COMMENTARY]
<p>Content here...</p>

[PRIVATE_PATH]
<ol class="step-list">...</ol>

[BRIDGE_CONTENT]
<p>Content here...</p>

Remember: NO forbidden words. Professional tone. Empathetic but not salesy."""

    return prompt


# =============================================================================
# LLM API CALLS
# =============================================================================

def call_anthropic(prompt: str, system: str, api_key: str) -> Optional[str]:
    """Call Anthropic Claude API."""
    if not ANTHROPIC_AVAILABLE:
        return None
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
    
    except Exception as e:
        print(f"Anthropic API error: {e}")
        return None


def call_openai(prompt: str, system: str, api_key: str) -> Optional[str]:
    """Call OpenAI API."""
    if not OPENAI_AVAILABLE:
        return None
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return None


def call_llm(prompt: str, system: str, api_key: str, provider: str = "openai") -> Optional[str]:
    """Call the appropriate LLM based on provider."""
    if provider == "anthropic":
        return call_anthropic(prompt, system, api_key)
    else:
        return call_openai(prompt, system, api_key)


# =============================================================================
# CONTENT PARSING
# =============================================================================

def parse_llm_response(response: str) -> Dict[str, str]:
    """Parse the LLM response into content sections."""
    sections = {
        "local_hook": "",
        "data_commentary": "",
        "private_path": "",
        "bridge_content": ""
    }
    
    # Define section markers
    markers = {
        "[LOCAL_HOOK]": "local_hook",
        "[DATA_COMMENTARY]": "data_commentary", 
        "[PRIVATE_PATH]": "private_path",
        "[BRIDGE_CONTENT]": "bridge_content"
    }
    
    # Try to extract each section
    for marker, key in markers.items():
        pattern = rf'\{re.escape(marker)}\s*(.*?)(?=\[|$)'
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            # Remove any markdown backticks if present
            content = re.sub(r'```html?\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            sections[key] = content
    
    # If markers weren't found, try to extract based on content patterns
    if not any(sections.values()):
        # Fallback: split by common section indicators
        parts = re.split(r'\n(?=<[ph]|<ol)', response)
        if len(parts) >= 4:
            sections["local_hook"] = parts[0].strip()
            sections["data_commentary"] = parts[1].strip() if len(parts) > 1 else ""
            sections["private_path"] = parts[2].strip() if len(parts) > 2 else ""
            sections["bridge_content"] = parts[3].strip() if len(parts) > 3 else ""
    
    return sections


# =============================================================================
# DATA CARD GENERATION
# =============================================================================

def generate_data_cards(serp_data: Dict, city: str) -> str:
    """Generate HTML for data cards from SERP data."""
    economic = serp_data.get("economic_profile", {}) or {}
    commute = serp_data.get("commute_data", {}) or {}
    
    cards = []
    
    # Income card
    income = economic.get("median_income", "N/A")
    if income and income != "N/A":
        cards.append(f"""
            <div class="data-card">
                <div class="data-card-value">{income}</div>
                <div class="data-card-label">Median Household Income</div>
            </div>
        """)
    
    # Income bracket card
    bracket = economic.get("income_bracket", "").replace("-", " ").title()
    if bracket:
        cards.append(f"""
            <div class="data-card">
                <div class="data-card-value">{bracket}</div>
                <div class="data-card-label">Income Classification</div>
            </div>
        """)
    
    # Drive time card
    drive_time = commute.get("drive_time", "")
    if drive_time:
        cards.append(f"""
            <div class="data-card">
                <div class="data-card-value">{drive_time}</div>
                <div class="data-card-label">Drive to Facility</div>
            </div>
        """)
    
    # Employers card
    employers = economic.get("major_employers", [])
    if employers:
        count = len(employers)
        cards.append(f"""
            <div class="data-card">
                <div class="data-card-value">{count}+</div>
                <div class="data-card-label">Major Local Employers</div>
            </div>
        """)
    
    # Default cards if no data
    if not cards:
        cards = [
            f"""
            <div class="data-card">
                <div class="data-card-value">PPO</div>
                <div class="data-card-label">Insurance Type Accepted</div>
            </div>
            """,
            f"""
            <div class="data-card">
                <div class="data-card-value">24/7</div>
                <div class="data-card-label">Confidential Support</div>
            </div>
            """,
            f"""
            <div class="data-card">
                <div class="data-card-value">Private</div>
                <div class="data-card-label">Treatment Setting</div>
            </div>
            """
        ]
    
    return "\n".join(cards)


# =============================================================================
# FALLBACK CONTENT
# =============================================================================

def generate_fallback_content(city: str, state: str, serp_data: Dict, brand: str) -> Dict[str, str]:
    """Generate fallback content if LLM fails."""
    
    economic = serp_data.get("economic_profile", {}) or {}
    commute = serp_data.get("commute_data", {}) or {}
    employers = economic.get("major_employers", [])
    
    # Get employer names
    employer_names = []
    for emp in employers[:3]:
        if isinstance(emp, dict):
            employer_names.append(emp.get("name", ""))
        else:
            employer_names.append(str(emp))
    employer_list = ", ".join([e for e in employer_names if e]) or "local corporations"
    
    drive_time = commute.get("drive_time", "approximately one hour")
    income_bracket = economic.get("income_bracket", "middle").replace("-", " ")
    
    return {
        "local_hook": f"""
            <p>For professionals and families in {city}, navigating private behavioral health coverage requires 
            specialized knowledge. Many residents employed by {employer_list} and other area organizations 
            have access to PPO insurance plans that provide substantial coverage for evidence-based treatment programs.</p>
            
            <p>Understanding these benefits—and knowing how to access them confidentially—is essential for those 
            seeking quality care. This guide provides {city} residents with the information needed to make informed 
            decisions about private treatment options.</p>
            
            <p>Privacy concerns are paramount for working professionals. Employer-sponsored PPO plans typically 
            offer protections that allow individuals to seek treatment without workplace disclosure, a critical 
            consideration for those in sensitive positions.</p>
        """,
        
        "data_commentary": f"""
            <p>{city}'s {income_bracket} income demographic indicates that many residents have access to 
            employer-sponsored health insurance with PPO options. These plans typically provide the most 
            comprehensive coverage for private behavioral health treatment.</p>
            
            <p>Understanding your specific plan benefits is the first step. Most PPO plans cover a significant 
            portion of treatment costs at qualified facilities, often including both inpatient and outpatient 
            services.</p>
        """,
        
        "private_path": """
            <ol class="step-list">
                <li><strong>Confidential Insurance Verification</strong> — A private review of your PPO benefits 
                to understand coverage levels, deductibles, and any pre-authorization requirements. This 
                conversation remains completely confidential.</li>
                
                <li><strong>Clinical Assessment</strong> — A licensed professional evaluates treatment needs 
                and recommends an appropriate level of care. This assessment is typically covered by PPO insurance.</li>
                
                <li><strong>Seamless Admission</strong> — Once benefits are verified and clinical needs assessed, 
                admission can often occur within 24-48 hours. All paperwork is handled discreetly.</li>
                
                <li><strong>Evidence-Based Treatment</strong> — Individualized programming delivered by 
                credentialed professionals. PPO coverage typically continues throughout the recommended 
                treatment duration.</li>
                
                <li><strong>Coordinated Aftercare</strong> — Before discharge, connections are established 
                with local providers for ongoing support. Many PPO plans cover continued outpatient services.</li>
            </ol>
        """,
        
        "bridge_content": f"""
            <p>Clinical research consistently demonstrates that geographic separation from one's home environment 
            significantly improves treatment outcomes. For {city} residents, seeking care at a facility 
            {drive_time} away provides the ideal balance: close enough for family involvement, yet distant 
            enough to create the focused healing environment recovery requires.</p>
            
            <p>Distance creates safety in multiple ways. It removes individuals from the triggers, relationships, 
            and environments associated with past substance use. It provides privacy from colleagues and 
            acquaintances who might otherwise become aware of treatment. And it allows families to visit 
            while maintaining the structured environment essential for early recovery.</p>
            
            <p>Many {city} professionals specifically seek treatment outside their immediate community for 
            these reasons. The drive time of {drive_time} is manageable for family visits while providing 
            the separation that supports successful outcomes.</p>
        """
    }


# =============================================================================
# MAIN GENERATION FUNCTION
# =============================================================================

def generate_page_html(
    page_data: Dict[str, Any],
    api_key: str,
    provider: str = "openai",
    brand: str = "TruPath Recovery",
    phone_number: str = "(888) 555-0123"
) -> str:
    """
    Generate complete HTML page for a Private PPO Resource Guide.
    
    Args:
        page_data: Dictionary containing:
            - city: City name
            - state: State abbreviation
            - keyword: Target keyword
            - serp_data: Data from logic.py (JSON string or dict)
            - titles: Title data from entity_logic.py
            - wiki_url: Wikipedia URL for the city
        api_key: OpenAI or Anthropic API key
        provider: "openai" or "anthropic"
        brand: Brand name
        phone_number: Phone for CTA bar
    
    Returns:
        Complete HTML string
    """
    # Extract basic info
    city = page_data.get("city", "")
    state = page_data.get("state", "NJ")
    keyword = page_data.get("keyword", "addiction treatment")
    
    # Parse serp_data if it's a string
    serp_data = page_data.get("serp_data", {})
    if isinstance(serp_data, str):
        try:
            serp_data = json.loads(serp_data)
        except json.JSONDecodeError:
            serp_data = {}
    
    # Get titles or generate defaults
    titles = page_data.get("titles", {})
    if not titles:
        from entity_logic import construct_semantic_title
        titles = construct_semantic_title(
            brand=brand,
            city=city,
            service_variant="Addiction Treatment",
            keyword=keyword
        )
    
    # Get entity variants
    entity_variants = serp_data.get("entity_variants", [])
    if not entity_variants:
        entity_variants = serp_data.get("ppo_variants", [])
    if not entity_variants:
        entity_variants = ["Substance Abuse Treatment", "Behavioral Health Services", "Recovery Programs"]
    
    # Build the prompt
    prompt = build_content_prompt(
        city=city,
        state=state,
        keyword=keyword,
        serp_data=serp_data,
        titles=titles,
        entity_variants=entity_variants,
        brand=brand
    )
    
    # Call LLM
    llm_response = None
    if api_key:
        llm_response = call_llm(prompt, SYSTEM_PROMPT, api_key, provider)
    
    # Parse response or use fallback
    if llm_response:
        content_sections = parse_llm_response(llm_response)
        # Check if we got valid content
        if not any(content_sections.values()):
            content_sections = generate_fallback_content(city, state, serp_data, brand)
    else:
        content_sections = generate_fallback_content(city, state, serp_data, brand)
    
    # Generate data cards
    data_cards_html = generate_data_cards(serp_data, city)
    
    # Prepare template variables
    template_vars = {
        # Meta
        "title_tag": titles.get("title_tag", f"Private Addiction Treatment in {city} | {brand}"),
        "meta_description": titles.get("meta_description", f"Private PPO addiction treatment options for {city} residents. Confidential care with insurance verification."),
        "og_title": titles.get("og_title", f"Private Treatment Near {city} | {brand}"),
        
        # Schema
        "schema_headline": titles.get("schema_headline", titles.get("h1_title", "")),
        "schema_description": titles.get("schema_description", ""),
        "wikidata_url": serp_data.get("wikidata_url", "https://www.wikidata.org/wiki/Q1141488"),
        "city_wiki_url": page_data.get("wiki_url", f"https://en.wikipedia.org/wiki/{city},_{state}"),
        
        # Header
        "h1_title": titles.get("h1_title", f"Private Addiction Treatment in {city} | PPO Coverage Accepted"),
        "subtitle": f"A confidential resource for {city} professionals seeking private treatment options",
        
        # Content sections
        "local_hook_content": content_sections.get("local_hook", ""),
        "data_cards_html": data_cards_html,
        "data_commentary": content_sections.get("data_commentary", ""),
        "private_path_content": content_sections.get("private_path", ""),
        "bridge_content": content_sections.get("bridge_content", ""),
        
        # Footer/CTA
        "phone_number": phone_number,
        "brand": brand,
        "city": city,
        "current_date": datetime.now().strftime("%Y-%m-%d"),
        "current_year": datetime.now().year
    }
    
    # Render template
    try:
        html = HTML_TEMPLATE.substitute(template_vars)
    except KeyError as e:
        print(f"Template error: missing key {e}")
        # Fill in missing keys with empty strings
        for key in HTML_TEMPLATE.template.split("${")[1:]:
            key = key.split("}")[0]
            if key not in template_vars:
                template_vars[key] = ""
        html = HTML_TEMPLATE.substitute(template_vars)
    
    return html


def generate_html(page_data: Dict[str, Any], api_key: str, provider: str = "openai") -> str:
    """
    Convenience wrapper for generate_page_html.
    
    Args:
        page_data: Page data dictionary
        api_key: API key for LLM
        provider: "openai" or "anthropic"
    
    Returns:
        Complete HTML string
    """
    return generate_page_html(page_data, api_key, provider)


# =============================================================================
# TESTING
# =============================================================================

def test_content_generator():
    """Test the content generator with sample data."""
    
    sample_data = {
        "city": "Newark",
        "state": "NJ",
        "keyword": "addiction treatment",
        "wiki_url": "https://en.wikipedia.org/wiki/Newark,_New_Jersey",
        "serp_data": {
            "economic_profile": {
                "median_income": "$35,000",
                "income_bracket": "middle",
                "major_employers": [
                    {"name": "Prudential Financial", "likely_ppo": True},
                    {"name": "Audible", "likely_ppo": True},
                    {"name": "Panasonic North America", "likely_ppo": True}
                ]
            },
            "commute_data": {
                "drive_time": "1 hr 15 min",
                "to_city": "Toms River, NJ"
            },
            "local_providers": [
                {"name": "Newark Counseling Center"},
                {"name": "Gateway Behavioral Health"}
            ],
            "entity_variants": [
                "Substance Abuse Treatment",
                "Chemical Dependency Treatment",
                "Addiction Recovery Services"
            ],
            "ppo_variants": [
                "Private Pay Addiction Treatment",
                "Executive Recovery Programs"
            ],
            "pitch_points": [
                "Many Newark residents work for Prudential, which offers comprehensive PPO coverage.",
                "The drive to our facility is just over an hour, ideal for family visits."
            ]
        },
        "titles": {
            "h1_title": "Private Addiction Treatment in Newark | PPO Coverage Accepted",
            "seo_title": "TruPath Recovery Provides Substance Abuse Treatment for Newark Residents",
            "title_tag": "Private Addiction Treatment Newark NJ | PPO Accepted",
            "meta_description": "Find private addiction treatment in Newark. PPO insurance accepted. Confidential care.",
            "schema_headline": "Private Addiction Treatment in Newark | PPO Coverage Accepted",
            "schema_description": "TruPath Recovery provides private addiction treatment for Newark residents."
        }
    }
    
    print("=" * 60)
    print("Testing Content Generator (No API Call - Fallback Mode)")
    print("=" * 60)
    
    # Generate without API key to test fallback
    html = generate_page_html(sample_data, api_key="", provider="openai")
    
    print(f"\nGenerated HTML length: {len(html)} characters")
    print("\nFirst 500 characters:")
    print(html[:500])
    print("\n...")
    print("\nLast 500 characters:")
    print(html[-500:])
    
    # Save to file for inspection
    with open("/tmp/test_output.html", "w") as f:
        f.write(html)
    print(f"\nFull HTML saved to: /tmp/test_output.html")
    
    return html


if __name__ == "__main__":
    test_content_generator()
