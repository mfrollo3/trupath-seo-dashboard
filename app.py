"""
app.py - TruPathNJ Local SEO Content Dashboard
Streamlit application for managing Hub & Spoke content architecture.
Phase 2: Added Intelligence Layer with entity logic and SERP data fetching.
"""

import streamlit as st
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import json
from typing import List, Dict
from datetime import datetime

import database as db
from entity_logic import get_entity_variants, construct_semantic_title, generate_content_variations
from logic import (
    fetch_private_pay_data, 
    fetch_batch_private_pay_data,
    generate_ppo_pitch_points,
    PrivatePayData,
    SERPAPI_AVAILABLE
)
from content_generator import generate_page_html, generate_html

# Page configuration
st.set_page_config(
    page_title="TruPathNJ SEO Dashboard",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for API keys
if 'serpapi_key' not in st.session_state:
    st.session_state.serpapi_key = ""
if 'openai_key' not in st.session_state:
    st.session_state.openai_key = ""
if 'anthropic_key' not in st.session_state:
    st.session_state.anthropic_key = ""
if 'llm_provider' not in st.session_state:
    st.session_state.llm_provider = "openai"
if 'brand_name' not in st.session_state:
    st.session_state.brand_name = "TruPath Recovery"
if 'facility_location' not in st.session_state:
    st.session_state.facility_location = "Toms River, NJ"
if 'phone_number' not in st.session_state:
    st.session_state.phone_number = "(888) 555-0123"
if 'fetch_log' not in st.session_state:
    st.session_state.fetch_log = []
if 'content_log' not in st.session_state:
    st.session_state.content_log = []

# Custom CSS
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
    .log-container {
        background-color: #1e1e1e;
        color: #00ff00;
        font-family: 'Courier New', monospace;
        padding: 15px;
        border-radius: 5px;
        max-height: 400px;
        overflow-y: auto;
        font-size: 12px;
    }
    .log-entry {
        margin: 2px 0;
    }
    .log-success { color: #00ff00; }
    .log-error { color: #ff4444; }
    .log-info { color: #00aaff; }
    .metric-highlight {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .data-preview {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)


def fetch_wiki_urls_batch(pages_data: List[Dict], progress_callback=None) -> List[Dict]:
    """Fetch Wikipedia URLs for a batch of pages using thread pool."""
    total = len(pages_data)
    completed = 0
    
    def fetch_single(page: Dict) -> Dict:
        city = page.get('city', '')
        state = page.get('state', '')
        if city:
            wiki_url = db.fetch_wiki_url(city, state)
            page['wiki_url'] = wiki_url
        return page
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_single, page): page for page in pages_data}
        
        for future in as_completed(futures):
            completed += 1
            if progress_callback:
                progress_callback(completed / total)
    
    return pages_data


def render_settings_sidebar():
    """Render the settings sidebar with API keys and configuration."""
    st.sidebar.title("🗺️ TruPathNJ")
    st.sidebar.caption("Local SEO Content Dashboard")
    
    st.sidebar.divider()
    
    # API Settings
    st.sidebar.subheader("⚙️ Settings")
    
    with st.sidebar.expander("🔑 API Keys", expanded=False):
        serpapi_key = st.text_input(
            "SerpAPI Key",
            value=st.session_state.serpapi_key,
            type="password",
            help="Required for SERP data fetching"
        )
        if serpapi_key != st.session_state.serpapi_key:
            st.session_state.serpapi_key = serpapi_key
        
        openai_key = st.text_input(
            "OpenAI API Key",
            value=st.session_state.openai_key,
            type="password",
            help="For content generation with GPT-4"
        )
        if openai_key != st.session_state.openai_key:
            st.session_state.openai_key = openai_key
        
        anthropic_key = st.text_input(
            "Anthropic API Key",
            value=st.session_state.anthropic_key,
            type="password",
            help="For content generation with Claude"
        )
        if anthropic_key != st.session_state.anthropic_key:
            st.session_state.anthropic_key = anthropic_key
        
        llm_provider = st.selectbox(
            "LLM Provider",
            options=["openai", "anthropic"],
            index=0 if st.session_state.llm_provider == "openai" else 1,
            help="Select which LLM to use for content generation"
        )
        if llm_provider != st.session_state.llm_provider:
            st.session_state.llm_provider = llm_provider
        
        # Status indicators
        if st.session_state.serpapi_key:
            st.success("✓ SerpAPI configured")
        else:
            st.warning("⚠ SerpAPI key required")
        
        if st.session_state.openai_key or st.session_state.anthropic_key:
            st.success(f"✓ {llm_provider.title()} configured")
        else:
            st.warning("⚠ LLM key required for content generation")
    
    with st.sidebar.expander("🏢 Brand Settings", expanded=False):
        brand_name = st.text_input(
            "Brand Name",
            value=st.session_state.brand_name,
            help="Used in title generation"
        )
        if brand_name != st.session_state.brand_name:
            st.session_state.brand_name = brand_name
        
        facility_location = st.text_input(
            "Facility Location",
            value=st.session_state.facility_location,
            help="For commute calculations"
        )
        if facility_location != st.session_state.facility_location:
            st.session_state.facility_location = facility_location
        
        phone_number = st.text_input(
            "CTA Phone Number",
            value=st.session_state.phone_number,
            help="Displayed in CTA bar on generated pages"
        )
        if phone_number != st.session_state.phone_number:
            st.session_state.phone_number = phone_number
    
    st.sidebar.divider()
    
    # Quick stats
    pages = db.get_all_pages()
    if pages:
        status_counts = db.get_status_counts()
        
        st.sidebar.subheader("📊 Quick Stats")
        st.sidebar.metric("Total Pages", len(pages))
        
        # Progress bar for completion
        data_ready = status_counts.get('Data Ready', 0) + status_counts.get('Content Ready', 0) + status_counts.get('Published', 0)
        total = len(pages) if pages else 1
        progress = data_ready / total
        st.sidebar.progress(progress, text=f"{int(progress*100)}% Data Fetched")
    
    st.sidebar.divider()
    
    # Quick actions
    st.sidebar.subheader("⚡ Quick Actions")
    
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
    
    if st.sidebar.button("🗑️ Clear All Pages", use_container_width=True, type="secondary"):
        if st.sidebar.checkbox("Confirm deletion"):
            db.clear_all_pages()
            st.sidebar.success("All pages cleared!")
            st.rerun()
    
    st.sidebar.divider()
    st.sidebar.caption(f"Database: {db.DB_PATH.name}")
    st.sidebar.caption(f"SerpAPI: {'✓' if SERPAPI_AVAILABLE else '✗'}")


def render_campaign_setup():
    """Render the Campaign Setup tab."""
    st.header("📁 Campaign Setup")
    st.markdown("Upload a CSV file to initialize your Hub & Spoke content structure.")
    
    with st.expander("📋 CSV Format Requirements", expanded=False):
        st.markdown("""
        Your CSV file should have the following columns:
        
        | Column | Required | Description |
        |--------|----------|-------------|
        | `City` | ✅ Yes | Name of the city |
        | `State` | ✅ Yes | State abbreviation (e.g., NJ, PA) |
        | `Type` | ✅ Yes | Either `Hub` or `Spoke` |
        | `Parent_City` | For Spokes | The Hub city this Spoke connects to |
        | `Keyword` | Optional | Target keyword for this page |
        """)
        
        st.markdown("**Example CSV:**")
        example_df = pd.DataFrame({
            'City': ['Newark', 'Jersey City', 'Hoboken', 'Elizabeth'],
            'State': ['NJ', 'NJ', 'NJ', 'NJ'],
            'Type': ['Hub', 'Hub', 'Spoke', 'Spoke'],
            'Parent_City': ['', '', 'Jersey City', 'Newark'],
            'Keyword': ['drug rehab newark nj', 'addiction treatment jersey city', 'rehab hoboken nj', 'detox elizabeth nj']
        })
        st.dataframe(example_df, use_container_width=True)
    
    st.divider()
    
    uploaded_file = st.file_uploader(
        "Upload Campaign CSV",
        type=['csv'],
        help="Upload a CSV file with City, State, Type, and Parent_City columns"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = df.columns.str.strip().str.title().str.replace(' ', '_')
            
            required_cols = ['City', 'State', 'Type']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
                return
            
            df['City'] = df['City'].str.strip()
            df['State'] = df['State'].str.strip().str.upper()
            df['Type'] = df['Type'].str.strip().str.title()
            
            if 'Parent_City' not in df.columns:
                df['Parent_City'] = ''
            else:
                df['Parent_City'] = df['Parent_City'].fillna('').str.strip()
            
            if 'Keyword' not in df.columns:
                df['Keyword'] = ''
            else:
                df['Keyword'] = df['Keyword'].fillna('').str.strip()
            
            invalid_types = df[~df['Type'].isin(['Hub', 'Spoke'])]
            if len(invalid_types) > 0:
                st.error(f"❌ Invalid Type values found. Must be 'Hub' or 'Spoke'.")
                st.dataframe(invalid_types)
                return
            
            st.subheader("📊 Data Preview")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Pages", len(df))
            with col2:
                st.metric("Hub Pages", len(df[df['Type'] == 'Hub']))
            with col3:
                st.metric("Spoke Pages", len(df[df['Type'] == 'Spoke']))
            
            st.dataframe(df, use_container_width=True, height=300)
            
            st.subheader("⚙️ Import Options")
            
            col1, col2 = st.columns(2)
            with col1:
                fetch_wiki = st.checkbox(
                    "Fetch Wikipedia URLs",
                    value=True,
                    help="Automatically fetch Wikipedia URLs for entity linking"
                )
            with col2:
                clear_existing = st.checkbox(
                    "Clear existing pages before import",
                    value=False,
                    help="Warning: This will delete all existing pages!"
                )
            
            if st.button("🚀 Import Campaign Data", type="primary", use_container_width=True):
                if clear_existing:
                    db.clear_all_pages()
                    st.info("🗑️ Cleared existing pages")
                
                pages_data = df.to_dict('records')
                pages_data = [
                    {
                        'city': p['City'],
                        'state': p['State'],
                        'page_type': p['Type'],
                        'parent_city': p.get('Parent_City', ''),
                        'keyword': p.get('Keyword', ''),
                        'wiki_url': None
                    }
                    for p in pages_data
                ]
                
                if fetch_wiki:
                    st.info("🔍 Fetching Wikipedia URLs...")
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    def update_progress(progress):
                        progress_bar.progress(progress)
                        status_text.text(f"Fetching Wikipedia data: {int(progress * 100)}%")
                    
                    pages_data = fetch_wiki_urls_batch(pages_data, update_progress)
                    wiki_count = sum(1 for p in pages_data if p.get('wiki_url'))
                    status_text.text(f"✅ Found Wikipedia URLs for {wiki_count}/{len(pages_data)} cities")
                
                try:
                    inserted = db.bulk_insert_pages(pages_data)
                    st.success(f"✅ Successfully imported {inserted} pages!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error importing data: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Error reading CSV file: {str(e)}")


def render_status_tab():
    """Render the Status tab with build queue."""
    st.header("📊 Build Queue Status")
    
    pages = db.get_all_pages()
    
    if not pages:
        st.info("📭 No pages in the database yet. Upload a CSV in the Campaign Setup tab.")
        return
    
    status_counts = db.get_status_counts()
    type_counts = db.get_page_type_counts()
    
    st.subheader("📈 Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Pages", len(pages))
    with col2:
        st.metric("Hubs", type_counts.get('Hub', 0))
    with col3:
        st.metric("Spokes", type_counts.get('Spoke', 0))
    with col4:
        st.metric("Pending", status_counts.get('Pending', 0))
    with col5:
        st.metric("Data Ready", status_counts.get('Data Ready', 0))
    
    st.divider()
    
    st.subheader("🔍 Filter & View")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            options=['All', 'Pending', 'Data Ready', 'Content Ready', 'Published'],
            index=0
        )
    with col2:
        type_filter = st.selectbox(
            "Filter by Type",
            options=['All', 'Hub', 'Spoke'],
            index=0
        )
    with col3:
        search_term = st.text_input("Search by City", placeholder="Enter city name...")
    
    df = pd.DataFrame(pages)
    
    if status_filter != 'All':
        df = df[df['status'] == status_filter]
    if type_filter != 'All':
        df = df[df['page_type'] == type_filter]
    if search_term:
        df = df[df['city'].str.contains(search_term, case=False, na=False)]
    
    # Check for SERP data
    df['has_serp_data'] = df['serp_data'].apply(lambda x: '✅' if x else '❌')
    
    display_cols = ['id', 'city', 'state', 'page_type', 'parent_city', 'wiki_url', 'has_serp_data', 'status']
    display_df = df[[col for col in display_cols if col in df.columns]].copy()
    
    display_df.columns = ['ID', 'City', 'State', 'Type', 'Parent Hub', 'Wikipedia URL', 'SERP Data', 'Status']
    
    if 'Wikipedia URL' in display_df.columns:
        display_df['Wikipedia URL'] = display_df['Wikipedia URL'].apply(lambda x: '✅' if x else '❌')
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        column_config={
            'ID': st.column_config.NumberColumn('ID', width='small'),
            'City': st.column_config.TextColumn('City', width='medium'),
            'State': st.column_config.TextColumn('State', width='small'),
            'Type': st.column_config.TextColumn('Type', width='small'),
            'Parent Hub': st.column_config.TextColumn('Parent Hub', width='medium'),
            'Wikipedia URL': st.column_config.TextColumn('Wiki', width='small'),
            'SERP Data': st.column_config.TextColumn('SERP', width='small'),
            'Status': st.column_config.TextColumn('Status', width='small')
        }
    )
    
    st.caption(f"Showing {len(display_df)} of {len(pages)} total pages")


def render_generator_tab():
    """Render the Generator tab for data fetching and entity processing."""
    st.header("🧠 Intelligence Generator")
    st.markdown("Fetch SERP data and generate entity variants for pending pages.")
    
    # Check API key
    if not st.session_state.serpapi_key:
        st.warning("⚠️ Please configure your SerpAPI key in the Settings sidebar to fetch SERP data.")
        st.info("You can still test entity logic without an API key.")
    
    # Get pending pages
    pending_pages = db.get_pages_by_status('Pending')
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 Pending Pages Queue")
        
        if not pending_pages:
            st.success("🎉 No pending pages! All pages have been processed.")
        else:
            st.info(f"Found {len(pending_pages)} pages awaiting data fetch.")
            
            pending_df = pd.DataFrame(pending_pages)
            display_cols = ['id', 'city', 'state', 'page_type', 'keyword']
            pending_display = pending_df[[col for col in display_cols if col in pending_df.columns]].copy()
            pending_display.columns = ['ID', 'City', 'State', 'Type', 'Keyword']
            
            st.dataframe(
                pending_display.head(20),
                use_container_width=True,
                height=300
            )
            
            if len(pending_pages) > 20:
                st.caption(f"Showing first 20 of {len(pending_pages)} pending pages")
    
    with col2:
        st.subheader("⚙️ Fetch Settings")
        
        batch_size = st.slider(
            "Batch Size",
            min_value=1,
            max_value=20,
            value=10,
            help="Number of pages to process per batch"
        )
        
        include_entity = st.checkbox(
            "Fetch Entity Variants",
            value=True,
            help="Get semantic variants from Wikidata"
        )
        
        include_serp = st.checkbox(
            "Fetch SERP Data",
            value=True,
            help="Requires SerpAPI key"
        )
        
        if include_serp and not st.session_state.serpapi_key:
            st.warning("SerpAPI key required")
            include_serp = False
    
    st.divider()
    
    # Fetch button and progress
    col1, col2 = st.columns([1, 1])
    
    with col1:
        fetch_button = st.button(
            f"🚀 Fetch Data for Next {min(batch_size, len(pending_pages))} Pages",
            type="primary",
            use_container_width=True,
            disabled=not pending_pages
        )
    
    with col2:
        clear_log = st.button("🗑️ Clear Log", use_container_width=True, key="clear_gen_log")
        if clear_log:
            st.session_state.fetch_log = []
            st.rerun()
    
    if fetch_button and pending_pages:
        batch = pending_pages[:batch_size]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_container = st.empty()
        
        def add_log(message: str, level: str = "info"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.session_state.fetch_log.append({
                "time": timestamp,
                "message": message,
                "level": level
            })
        
        def update_log_display():
            log_html = '<div class="log-container">'
            for entry in st.session_state.fetch_log[-50:]:  # Show last 50 entries
                css_class = f"log-{entry['level']}"
                log_html += f'<div class="log-entry {css_class}">[{entry["time"]}] {entry["message"]}</div>'
            log_html += '</div>'
            log_container.markdown(log_html, unsafe_allow_html=True)
        
        add_log(f"Starting batch processing for {len(batch)} pages...", "info")
        update_log_display()
        
        for i, page in enumerate(batch):
            city = page['city']
            state = page['state']
            keyword = page.get('keyword', 'addiction treatment')
            page_id = page['id']
            
            status_text.text(f"Processing {i+1}/{len(batch)}: {city}, {state}")
            add_log(f"Processing: {city}, {state}", "info")
            
            combined_data = {
                "city": city,
                "state": state,
                "fetched_at": datetime.now().isoformat()
            }
            
            # Fetch entity variants
            if include_entity:
                try:
                    entity_data = get_entity_variants(keyword or "addiction treatment")
                    combined_data["entity_variants"] = entity_data["variants"]
                    combined_data["ppo_variants"] = entity_data["ppo_variants"]
                    combined_data["wikidata_id"] = entity_data["wikidata_id"]
                    
                    # Generate title variations
                    titles = construct_semantic_title(
                        brand=st.session_state.brand_name,
                        city=city,
                        service_variant=entity_data["variants"][0] if entity_data["variants"] else "Addiction Treatment"
                    )
                    combined_data["titles"] = titles
                    
                    add_log(f"  ✓ Entity variants: {len(entity_data['variants'])} found", "success")
                    if entity_data["variants"]:
                        add_log(f"    → {entity_data['variants'][0]}", "info")
                except Exception as e:
                    add_log(f"  ✗ Entity error: {str(e)}", "error")
            
            # Fetch SERP data
            if include_serp and st.session_state.serpapi_key:
                try:
                    serp_data = fetch_private_pay_data(
                        city=city,
                        state=state,
                        api_key=st.session_state.serpapi_key,
                        facility_location=st.session_state.facility_location
                    )
                    
                    # Merge SERP data
                    serp_dict = serp_data.to_dict()
                    combined_data["economic_profile"] = serp_dict.get("economic_profile")
                    combined_data["commute_data"] = serp_dict.get("commute_data")
                    combined_data["local_providers"] = serp_dict.get("local_providers")
                    
                    # Generate pitch points
                    pitch_points = generate_ppo_pitch_points(serp_data)
                    combined_data["pitch_points"] = pitch_points
                    
                    # Log findings
                    if serp_data.economic_profile and serp_data.economic_profile.major_employers:
                        top_emp = serp_data.economic_profile.major_employers[0].name
                        add_log(f"  ✓ Found Employer: {top_emp}", "success")
                    
                    if serp_data.economic_profile and serp_data.economic_profile.median_income:
                        add_log(f"  ✓ Median Income: {serp_data.economic_profile.median_income}", "success")
                    
                    if serp_data.commute_data and serp_data.commute_data.drive_time:
                        add_log(f"  ✓ Drive Time: {serp_data.commute_data.drive_time}", "success")
                    
                    if serp_data.local_providers:
                        add_log(f"  ✓ Local Providers: {len(serp_data.local_providers)} found", "success")
                
                except Exception as e:
                    add_log(f"  ✗ SERP error: {str(e)}", "error")
            
            # Save to database
            try:
                db.update_serp_data(page_id, combined_data)
                db.update_page_status(page_id, "Data Ready")
                add_log(f"  ✓ Saved to database", "success")
            except Exception as e:
                add_log(f"  ✗ Database error: {str(e)}", "error")
            
            progress_bar.progress((i + 1) / len(batch))
            update_log_display()
            
            # Rate limiting between pages
            if i < len(batch) - 1 and include_serp:
                time.sleep(2)
        
        status_text.text("✅ Batch processing complete!")
        add_log(f"Batch complete: {len(batch)} pages processed", "success")
        update_log_display()
        
        time.sleep(1)
        st.rerun()
    
    # Display existing log
    if st.session_state.fetch_log:
        st.subheader("📜 Activity Log")
        log_html = '<div class="log-container">'
        for entry in st.session_state.fetch_log[-50:]:
            css_class = f"log-{entry['level']}"
            log_html += f'<div class="log-entry {css_class}">[{entry["time"]}] {entry["message"]}</div>'
        log_html += '</div>'
        st.markdown(log_html, unsafe_allow_html=True)
    
    st.divider()
    
    # Data Preview Section
    st.subheader("🔬 Data Preview")
    
    data_ready_pages = db.get_pages_by_status('Data Ready')
    
    if data_ready_pages:
        selected_city = st.selectbox(
            "Select a page to preview data:",
            options=[f"{p['city']}, {p['state']}" for p in data_ready_pages],
            index=0
        )
        
        if selected_city:
            city_name = selected_city.split(',')[0].strip()
            page_data = next((p for p in data_ready_pages if p['city'] == city_name), None)
            
            if page_data and page_data.get('serp_data'):
                try:
                    serp_data = json.loads(page_data['serp_data']) if isinstance(page_data['serp_data'], str) else page_data['serp_data']
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**🏢 Economic Profile**")
                        eco = serp_data.get('economic_profile', {})
                        if eco:
                            st.markdown(f"- **Median Income:** {eco.get('median_income', 'N/A')}")
                            st.markdown(f"- **Income Bracket:** {eco.get('income_bracket', 'N/A')}")
                            
                            employers = eco.get('major_employers', [])
                            if employers:
                                st.markdown("- **Major Employers:**")
                                for emp in employers[:5]:
                                    name = emp.get('name', emp) if isinstance(emp, dict) else emp
                                    st.markdown(f"  - {name}")
                    
                    with col2:
                        st.markdown("**🚗 Commute Data**")
                        commute = serp_data.get('commute_data', {})
                        if commute:
                            st.markdown(f"- **Drive Time:** {commute.get('drive_time', 'N/A')}")
                            st.markdown(f"- **To:** {commute.get('to_city', 'N/A')}")
                        
                        st.markdown("**🧠 Entity Variants**")
                        variants = serp_data.get('entity_variants', [])
                        if variants:
                            for v in variants[:3]:
                                st.markdown(f"- {v}")
                    
                    # Pitch Points
                    pitch_points = serp_data.get('pitch_points', [])
                    if pitch_points:
                        st.markdown("**💡 Generated Pitch Points**")
                        for point in pitch_points:
                            st.info(point)
                    
                    # Titles
                    titles = serp_data.get('titles', {})
                    if titles:
                        st.markdown("**📝 Generated Titles**")
                        st.code(titles.get('h1', 'N/A'), language=None)
                        st.caption(f"Title Tag: {titles.get('title_tag', 'N/A')}")
                
                except Exception as e:
                    st.error(f"Error parsing data: {str(e)}")
    else:
        st.info("No pages with data ready yet. Process some pending pages first.")
    
    # Entity Logic Tester
    st.divider()
    st.subheader("🧪 Entity Logic Tester")
    
    test_keyword = st.text_input(
        "Test Keyword",
        value="addiction treatment",
        help="Enter a keyword to see entity variants"
    )
    
    if st.button("🔍 Test Entity Logic"):
        with st.spinner("Fetching entity data..."):
            entity_result = get_entity_variants(test_keyword)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Standard Variants:**")
                for v in entity_result.get('variants', []):
                    st.markdown(f"- {v}")
            
            with col2:
                st.markdown("**PPO Variants:**")
                for v in entity_result.get('ppo_variants', []):
                    st.markdown(f"- {v}")
            
            st.markdown(f"**Source:** {entity_result.get('source', 'unknown')}")
            if entity_result.get('wikidata_url'):
                st.markdown(f"**Wikidata:** [{entity_result['wikidata_id']}]({entity_result['wikidata_url']})")


def render_content_tab():
    """Render the Content Generation tab."""
    st.header("📝 Content Generator")
    st.markdown("Generate complete HTML pages using LLM with the Private Insurance Benefits Navigator persona.")
    
    # Check for API key
    api_key = st.session_state.openai_key if st.session_state.llm_provider == "openai" else st.session_state.anthropic_key
    if not api_key:
        st.warning(f"⚠️ Please configure your {st.session_state.llm_provider.title()} API key in Settings to generate content.")
        st.info("You can still preview the HTML structure with fallback content.")
    
    # Get pages with data ready
    data_ready_pages = db.get_pages_by_status('Data Ready')
    content_ready_pages = db.get_pages_by_status('Content Ready')
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 Pages Ready for Content Generation")
        
        if not data_ready_pages:
            st.info("No pages with data ready. Fetch SERP data in the Generator tab first.")
        else:
            st.success(f"Found {len(data_ready_pages)} pages ready for content generation.")
            
            ready_df = pd.DataFrame(data_ready_pages)
            display_cols = ['id', 'city', 'state', 'page_type', 'keyword']
            ready_display = ready_df[[col for col in display_cols if col in ready_df.columns]].copy()
            ready_display.columns = ['ID', 'City', 'State', 'Type', 'Keyword']
            
            st.dataframe(
                ready_display.head(20),
                use_container_width=True,
                height=300
            )
    
    with col2:
        st.subheader("⚙️ Generation Settings")
        
        batch_size = st.slider(
            "Batch Size",
            min_value=1,
            max_value=10,
            value=5,
            help="Number of pages to generate per batch"
        )
        
        use_llm = st.checkbox(
            "Use LLM for Content",
            value=bool(api_key),
            disabled=not api_key,
            help="If unchecked, uses template-based fallback"
        )
        
        st.markdown(f"**Provider:** {st.session_state.llm_provider.title()}")
        st.markdown(f"**Brand:** {st.session_state.brand_name}")
        st.markdown(f"**Phone:** {st.session_state.phone_number}")
    
    st.divider()
    
    # Generation controls
    col1, col2 = st.columns([1, 1])
    
    with col1:
        generate_button = st.button(
            f"🚀 Generate Content for Next {min(batch_size, len(data_ready_pages))} Pages",
            type="primary",
            use_container_width=True,
            disabled=not data_ready_pages
        )
    
    with col2:
        clear_log = st.button("🗑️ Clear Log", use_container_width=True, key="clear_content_log")
        if clear_log:
            st.session_state.content_log = []
            st.rerun()
    
    # Generation process
    if generate_button and data_ready_pages:
        batch = data_ready_pages[:batch_size]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def add_log(message: str, level: str = "info"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.session_state.content_log.append({
                "time": timestamp,
                "message": message,
                "level": level
            })
        
        add_log(f"Starting content generation for {len(batch)} pages...", "info")
        
        for i, page in enumerate(batch):
            city = page['city']
            state = page['state']
            page_id = page['id']
            keyword = page.get('keyword', 'addiction treatment')
            
            status_text.text(f"Generating content for {i+1}/{len(batch)}: {city}, {state}")
            add_log(f"Processing: {city}, {state}", "info")
            
            try:
                # Parse serp_data
                serp_data = page.get('serp_data', {})
                if isinstance(serp_data, str):
                    try:
                        serp_data = json.loads(serp_data)
                    except:
                        serp_data = {}
                
                # Get titles from serp_data or generate
                titles = serp_data.get('titles', {})
                if not titles:
                    titles = construct_semantic_title(
                        brand=st.session_state.brand_name,
                        city=city,
                        service_variant="Addiction Treatment",
                        keyword=keyword
                    )
                
                # Prepare page data for generator
                page_data = {
                    "city": city,
                    "state": state,
                    "keyword": keyword,
                    "serp_data": serp_data,
                    "titles": titles,
                    "wiki_url": page.get('wiki_url', '')
                }
                
                # Generate HTML
                gen_api_key = api_key if use_llm else ""
                html_content = generate_page_html(
                    page_data=page_data,
                    api_key=gen_api_key,
                    provider=st.session_state.llm_provider,
                    brand=st.session_state.brand_name,
                    phone_number=st.session_state.phone_number
                )
                
                # Save to database
                db.update_html_content(page_id, html_content)
                db.update_page_status(page_id, "Content Ready")
                
                add_log(f"  ✓ Generated {len(html_content):,} characters of HTML", "success")
                add_log(f"  ✓ Status updated to 'Content Ready'", "success")
            
            except Exception as e:
                add_log(f"  ✗ Error: {str(e)}", "error")
            
            progress_bar.progress((i + 1) / len(batch))
        
        status_text.text("✅ Content generation complete!")
        add_log(f"Batch complete: {len(batch)} pages processed", "success")
        
        time.sleep(1)
        st.rerun()
    
    # Display log
    if st.session_state.content_log:
        st.subheader("📜 Generation Log")
        log_html = '<div class="log-container">'
        for entry in st.session_state.content_log[-30:]:
            css_class = f"log-{entry['level']}"
            log_html += f'<div class="log-entry {css_class}">[{entry["time"]}] {entry["message"]}</div>'
        log_html += '</div>'
        st.markdown(log_html, unsafe_allow_html=True)
    
    st.divider()
    
    # Preview Section
    st.subheader("👁️ Content Preview")
    
    all_content_pages = content_ready_pages + data_ready_pages
    
    if all_content_pages:
        # Filter to only show pages with content
        pages_with_content = [p for p in all_content_pages if p.get('html_content')]
        
        if pages_with_content:
            selected_page = st.selectbox(
                "Select a page to preview:",
                options=[f"{p['city']}, {p['state']} (ID: {p['id']})" for p in pages_with_content],
                index=0
            )
            
            if selected_page:
                page_id = int(selected_page.split("ID: ")[1].rstrip(")"))
                page_data = next((p for p in pages_with_content if p['id'] == page_id), None)
                
                if page_data and page_data.get('html_content'):
                    html_content = page_data['html_content']
                    
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.markdown("**📊 Page Stats**")
                        st.markdown(f"- **HTML Size:** {len(html_content):,} characters")
                        st.markdown(f"- **Status:** {page_data.get('status', 'Unknown')}")
                        st.markdown(f"- **City:** {page_data.get('city')}, {page_data.get('state')}")
                    
                    with col2:
                        st.markdown("**📥 Actions**")
                        
                        # Download button
                        filename = f"{page_data['city'].lower().replace(' ', '-')}-{page_data['state'].lower()}.html"
                        st.download_button(
                            label="💾 Download HTML",
                            data=html_content,
                            file_name=filename,
                            mime="text/html"
                        )
                    
                    # Preview tabs
                    preview_tab1, preview_tab2 = st.tabs(["🖼️ Rendered Preview", "📄 Source Code"])
                    
                    with preview_tab1:
                        st.components.v1.html(html_content, height=800, scrolling=True)
                    
                    with preview_tab2:
                        st.code(html_content[:10000] + ("\n... [truncated]" if len(html_content) > 10000 else ""), language="html")
        else:
            st.info("No pages with generated content yet. Generate content above.")
    else:
        st.info("No pages ready for preview. Complete data fetching and content generation first.")
    
    st.divider()
    
    # Single Page Generator
    st.subheader("🧪 Single Page Generator")
    st.markdown("Test content generation for a single page.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        test_city = st.text_input("City", value="Newark", key="test_city")
        test_state = st.text_input("State", value="NJ", key="test_state")
    
    with col2:
        test_keyword = st.text_input("Keyword", value="addiction treatment", key="test_kw")
    
    if st.button("🔬 Generate Test Page"):
        with st.spinner("Generating content..."):
            # Create minimal test data
            test_titles = construct_semantic_title(
                brand=st.session_state.brand_name,
                city=test_city,
                service_variant="Addiction Treatment",
                keyword=test_keyword
            )
            
            test_data = {
                "city": test_city,
                "state": test_state,
                "keyword": test_keyword,
                "serp_data": {
                    "economic_profile": {
                        "median_income": "$55,000",
                        "income_bracket": "middle",
                        "major_employers": [{"name": "Sample Corp", "likely_ppo": True}]
                    },
                    "commute_data": {
                        "drive_time": "1 hr 15 min",
                        "to_city": st.session_state.facility_location
                    },
                    "entity_variants": ["Substance Abuse Treatment", "Recovery Services"],
                    "ppo_variants": ["Private Addiction Treatment", "Executive Recovery"]
                },
                "titles": test_titles,
                "wiki_url": f"https://en.wikipedia.org/wiki/{test_city},_{test_state}"
            }
            
            gen_api_key = api_key if use_llm else ""
            html_result = generate_page_html(
                page_data=test_data,
                api_key=gen_api_key,
                provider=st.session_state.llm_provider,
                brand=st.session_state.brand_name,
                phone_number=st.session_state.phone_number
            )
            
            st.success(f"Generated {len(html_result):,} characters of HTML!")
            
            test_tab1, test_tab2 = st.tabs(["🖼️ Preview", "📄 Code"])
            
            with test_tab1:
                st.components.v1.html(html_result, height=600, scrolling=True)
            
            with test_tab2:
                st.code(html_result[:8000] + "\n... [truncated]", language="html")
            
            st.download_button(
                label="💾 Download Test HTML",
                data=html_result,
                file_name=f"test-{test_city.lower()}.html",
                mime="text/html"
            )


def main():
    """Main application entry point."""
    render_settings_sidebar()
    
    st.title("🗺️ TruPathNJ SEO Dashboard")
    st.caption("Hub & Spoke Content Management System • Phase 3: Content Generation")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📁 Campaign Setup", "📊 Status", "🧠 Generator", "📝 Content"])
    
    with tab1:
        render_campaign_setup()
    
    with tab2:
        render_status_tab()
    
    with tab3:
        render_generator_tab()
    
    with tab4:
        render_content_tab()


if __name__ == "__main__":
    main()
