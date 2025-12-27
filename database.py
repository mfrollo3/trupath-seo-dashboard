"""
database.py - Database layer for TruPathNJ Platform
"""
import sqlite3
import json
import wikipedia
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent / "trupath.db"

@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Campaign Table (Stores WP Creds)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_name TEXT,
                wp_url TEXT,
                wp_username TEXT,
                wp_app_password TEXT,
                drip_rate_per_day INTEGER DEFAULT 5,
                status TEXT DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Pages Table (Updated with Campaign ID)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                city TEXT,
                state TEXT,
                keyword TEXT,
                page_type TEXT CHECK(page_type IN ('Hub', 'Spoke', 'Topic')),
                parent_city TEXT,
                parent_hub_id INTEGER,
                status TEXT DEFAULT 'Pending',
                serp_data TEXT,
                html_content TEXT,
                live_url TEXT,
                published_at TIMESTAMP,
                wiki_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
        """)
        conn.commit()

# --- Campaign Functions ---
def add_campaign(name, url, user, password, rate):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO campaigns (campaign_name, wp_url, wp_username, wp_app_password, drip_rate_per_day)
            VALUES (?, ?, ?, ?, ?)
        """, (name, url, user, password, rate))
        conn.commit()
        return cursor.lastrowid

def get_active_campaigns():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE status = 'Active'")
        return [dict(row) for row in cursor.fetchall()]

def get_published_count_today(campaign_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) as count FROM pages 
            WHERE campaign_id = ? AND status = 'Published' 
            AND date(published_at) = ?
        """, (campaign_id, today))
        return cursor.fetchone()['count']

def get_next_ready_page(campaign_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM pages 
            WHERE campaign_id = ? AND status = 'Content Ready' 
            ORDER BY created_at ASC LIMIT 1
        """, (campaign_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

# --- Page Functions (Legacy Support) ---
def bulk_insert_pages(pages_data: List[Dict[str, Any]], campaign_id: int = None) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        count = 0
        for p in pages_data:
            cursor.execute("""
                INSERT INTO pages (campaign_id, city, state, keyword, page_type, parent_city, wiki_url, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
            """, (campaign_id, p.get('city'), p.get('state'), p.get('keyword'), 
                  p.get('page_type', 'Spoke'), p.get('parent_city'), p.get('wiki_url')))
            count += 1
        conn.commit()
        return count

# ... (Keep existing fetch/update functions: get_pages_by_status, update_serp_data, etc.) ...
# Copy/Paste your existing CRUD functions here if needed, or ask me to fill them.
# Critical: Ensure update_page_status handles 'Published' correctly.
def update_page_status(page_id, status):
    with get_connection() as conn:
        if status == 'Published':
            conn.execute("UPDATE pages SET status=?, published_at=CURRENT_TIMESTAMP WHERE id=?", (status, page_id))
        else:
            conn.execute("UPDATE pages SET status=? WHERE id=?", (status, page_id))
        conn.commit()

def update_live_url(page_id, url):
    with get_connection() as conn:
        conn.execute("UPDATE pages SET live_url=? WHERE id=?", (url, page_id))
        conn.commit()
        
def get_pages_by_status(status): # Re-adding essential function
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pages WHERE status=?", (status,))
        return [dict(row) for row in cursor.fetchall()]

def update_serp_data(page_id, data):
    with get_connection() as conn:
        conn.execute("UPDATE pages SET serp_data=? WHERE id=?", (json.dumps(data), page_id))
        conn.commit()

def update_html_content(page_id, html):
    with get_connection() as conn:
        conn.execute("UPDATE pages SET html_content=? WHERE id=?", (html, page_id))
        conn.commit()
        
def get_page_by_id(page_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pages WHERE id=?", (page_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
        
def fetch_wiki_url(city, state=None): # Keep existing helper
    if not city: return None
    try:
        return wikipedia.page(f"{city} {state}" if state else city, auto_suggest=True).url
    except: return None
