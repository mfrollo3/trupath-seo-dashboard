"""
app.py - The "Empire" Dashboard
Manages multiple WordPress sites (Campaigns) from one interface.
"""
import streamlit as st
import pandas as pd
import time
import json
from datetime import datetime
import database as db
from logic import fetch_private_pay_data, fetch_topic_data
from content_generator import generate_page_html
from entity_logic import construct_semantic_title, get_entity_variants

# Initialize DB
db.init_database()

st.set_page_config(page_title="TruPath Empire", layout="wide", page_icon="🏰")

# --- SESSION STATE ---
if 'logs' not in st.session_state: st.session_state.logs = []
def log(msg): st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M')}] {msg}")

# --- SIDEBAR: GLOBAL SETTINGS ---
st.sidebar.title("⚙️ Global Keys")
st.session_state.serpapi_key = st.sidebar.text_input("SerpAPI Key", value=st.session_state.serpapi_key if 'serpapi_key' in st.session_state else "", type="password")
st.session_state.openai_key = st.sidebar.text_input("OpenAI Key", value=st.session_state.openai_key if 'openai_key' in st.session_state else "", type="password")

st.sidebar.divider()

# --- SIDEBAR: CAMPAIGN SELECTOR ---
st.sidebar.header("📡 Select Site")
campaigns = db.get_active_campaigns()
campaign_options = {c['campaign_name']: c for c in campaigns}

selected_campaign_name = st.sidebar.selectbox(
    "Active Campaign", 
    options=["(Select Site)"] + list(campaign_options.keys())
)

current_camp = None
if selected_campaign_name != "(Select Site)":
    current_camp = campaign_options[selected_campaign_name]
    st.sidebar.success(f"Managing: {current_camp['wp_url']}")
    st.sidebar.caption(f"Target: {current_camp.get('target_location', 'NJ')}")

# --- MAIN TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["🏰 Site Manager", "📥 Import", "🧠 Factory", "🚀 Output"])

# --- TAB 1: SITE MANAGER (Add New Sites) ---
with tab1:
    st.header("Add New Website")
    with st.form("new_camp"):
        col1, col2 = st.columns(2)
        c_name = col1.text_input("Site Name (e.g., TruPath CA)")
        c_url = col2.text_input("WordPress URL (e.g., https://trupathca.com)")
        
        col3, col4 = st.columns(2)
        c_user = col3.text_input("WP Username")
        c_pass = col4.text_input("WP App Password", type="password")
        
        c_loc = st.text_input("Facility Target Location", value="Toms River, NJ", help="For drive time calc")
        c_rate = st.slider("Drip Rate (Pages/Day)", 1, 50, 5)
        
        if st.form_submit_button("Save New Site"):
            # In a real app, update db.add_campaign to accept target_location
            # For now we use the basic function
            db.add_campaign(c_name, c_url, c_user, c_pass, c_rate) 
            st.success(f"Added {c_name} to the Empire!")
            time.sleep(1)
            st.rerun()

    st.divider()
    st.subheader("Active Sites")
    if campaigns:
        st.dataframe(pd.DataFrame(campaigns)[['campaign_name', 'wp_url', 'drip_rate_per_day']])

# --- TAB 2: IMPORT (Upload to Specific Site) ---
with tab2:
    if current_camp:
        st.header(f"Import Keywords for: {current_camp['campaign_name']}")
        up_file = st.file_uploader("Upload CSV", type=['csv'])
        
        if up_file:
            df = pd.read_csv(up_file)
            st.dataframe(df.head())
            
            if st.button("Import to Queue"):
                data = df.to_dict('records')
                clean_data = []
                for row in data:
                    clean_data.append({
                        'city': row.get('City', ''),
                        'state': row.get('State', ''),
                        'page_type': row.get('Type', 'Spoke'),
                        'keyword': row.get('Keyword', ''),
                        'parent_city': row.get('Parent_City', ''),
                        'wiki_url': None
                    })
                
                # Pass Campaign ID to insert
                count = db.bulk_insert_pages(clean_data, campaign_id=current_camp['id'])
                st.success(f"Queued {count} pages for {current_camp['campaign_name']}")
    else:
        st.info("👈 Please select a Site from the Sidebar first.")

# --- TAB 3: FACTORY (Generate Data) ---
with tab3:
    if current_camp:
        st.header(f"🏭 Content Factory: {current_camp['campaign_name']}")
        
        # Get pending pages for THIS campaign only
        # You need to update get_pages_by_status in db to accept campaign_id
        # For this snippet, we will assume a filter logic:
        all_pending = db.get_pages_by_status('Pending')
        pending = [p for p in all_pending if p.get('campaign_id') == current_camp['id']]
        
        st.metric("Pages Waiting", len(pending))
        
        if st.button("🚀 Fetch Data & Research", disabled=not pending):
            progress = st.progress(0)
            for i, page in enumerate(pending[:5]): # Batch 5
                log(f"Researching: {page['keyword']}")
                
                # TOPIC vs CITY Logic
                if page['page_type'].lower() == 'topic':
                    serp_data = fetch_topic_data(page['keyword'], st.session_state.serpapi_key)
                    combined = serp_data
                else:
                    # Pass the Campaign's Target Location!
                    target = current_camp.get('target_location', 'Toms River, NJ')
                    serp_data = fetch_private_pay_data(
                        page['city'], page['state'], st.session_state.serpapi_key, 
                        facility_location=target 
                    )
                    ent = get_entity_variants(page['keyword'])
                    titles = construct_semantic_title(current_camp['campaign_name'], page['city'], "Rehab", page['keyword'])
                    combined = serp_data.to_dict()
                    combined['titles'] = titles
                    combined['entity_variants'] = ent['variants']

                db.update_serp_data(page['id'], combined)
                db.update_page_status(page['id'], 'Data Ready')
                progress.progress((i+1)/5)
            
            st.success("Batch Research Complete")
            time.sleep(1)
            st.rerun()
            
        st.text_area("Live Logs", "\n".join(st.session_state.logs[-5:]))
    else:
        st.info("👈 Select a Site to run the factory.")

# --- TAB 4: OUTPUT (Write & Publish) ---
with tab4:
    if current_camp:
        st.header(f"📝 Writer: {current_camp['campaign_name']}")
        
        # Filter ready pages for this campaign
        all_ready = db.get_pages_by_status('Data Ready')
        ready = [p for p in all_ready if p.get('campaign_id') == current_camp['id']]
        
        st.info(f"Ready to Write: {len(ready)}")
        
        if st.button("✨ Write Content (LLM)", disabled=not ready):
            prog = st.progress(0)
            for i, page in enumerate(ready[:5]):
                log(f"Writing: {page['keyword']}")
                try: s_data = json.loads(page['serp_data'])
                except: s_data = {}
                
                page_input = {
                    "page_type": page['page_type'], "city": page['city'],
                    "state": page['state'], "keyword": page['keyword'],
                    "serp_data": s_data, "titles": s_data.get('titles', {})
                }
                
                # Use Campaign Name as Brand
                html = generate_page_html(
                    page_input, st.session_state.openai_key, "openai", 
                    brand=current_camp['campaign_name']
                )
                
                db.update_html_content(page['id'], html)
                db.update_page_status(page['id'], 'Content Ready')
                prog.progress((i+1)/5)
            
            st.success("Writing Complete. The Drip Bot will take it from here!")
            
    else:
        st.info("👈 Select a Site.")
