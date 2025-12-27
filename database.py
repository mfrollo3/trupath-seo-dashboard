"""
database.py - Database layer for TruPathNJ Local SEO Content Dashboard
Handles SQLite operations for the Hub & Spoke content structure.
"""

import sqlite3
import json
import wikipedia
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "trupath.db"


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize the database with the pages table schema."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                state TEXT,
                keyword TEXT,
                page_type TEXT CHECK(page_type IN ('Hub', 'Spoke')) NOT NULL,
                parent_hub_id INTEGER,
                wiki_url TEXT,
                status TEXT DEFAULT 'Pending',
                serp_data TEXT,
                html_content TEXT,
                live_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_hub_id) REFERENCES pages(id) ON DELETE SET NULL
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_city ON pages(city)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_type ON pages(page_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_parent ON pages(parent_hub_id)")
        
        conn.commit()


def fetch_wiki_url(city: str, state: str = None) -> Optional[str]:
    """
    Fetch the canonical Wikipedia URL for a city.
    Uses disambiguation to find the correct city page.
    """
    search_term = f"{city}, {state}" if state else city
    
    try:
        # First try exact match
        page = wikipedia.page(search_term, auto_suggest=False)
        return page.url
    except wikipedia.DisambiguationError as e:
        # If disambiguation, try to find the city option
        for option in e.options:
            if city.lower() in option.lower():
                try:
                    page = wikipedia.page(option, auto_suggest=False)
                    return page.url
                except:
                    continue
        return None
    except wikipedia.PageError:
        # Try with auto_suggest enabled
        try:
            page = wikipedia.page(search_term, auto_suggest=True)
            return page.url
        except:
            return None
    except Exception as e:
        print(f"Error fetching Wikipedia URL for {search_term}: {e}")
        return None


def insert_page(
    city: str,
    state: str,
    page_type: str,
    parent_city: str = None,
    keyword: str = None,
    wiki_url: str = None
) -> int:
    """
    Insert a new page into the database.
    Returns the ID of the inserted page.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Find parent_hub_id if parent_city is provided
        parent_hub_id = None
        if parent_city and page_type == 'Spoke':
            cursor.execute(
                "SELECT id FROM pages WHERE city = ? AND page_type = 'Hub' LIMIT 1",
                (parent_city,)
            )
            result = cursor.fetchone()
            if result:
                parent_hub_id = result['id']
        
        cursor.execute("""
            INSERT INTO pages (city, state, keyword, page_type, parent_hub_id, wiki_url, status)
            VALUES (?, ?, ?, ?, ?, ?, 'Pending')
        """, (city, state, keyword, page_type, parent_hub_id, wiki_url))
        
        conn.commit()
        return cursor.lastrowid


def bulk_insert_pages(pages_data: List[Dict[str, Any]]) -> int:
    """
    Bulk insert pages from CSV data.
    First pass: Insert all Hub pages.
    Second pass: Insert Spoke pages with parent references.
    Returns count of inserted pages.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        inserted_count = 0
        
        # Separate hubs and spokes
        hubs = [p for p in pages_data if p.get('page_type', '').upper() == 'HUB']
        spokes = [p for p in pages_data if p.get('page_type', '').upper() == 'SPOKE']
        
        # First pass: Insert hubs
        for page in hubs:
            cursor.execute("""
                INSERT INTO pages (city, state, keyword, page_type, wiki_url, status)
                VALUES (?, ?, ?, 'Hub', ?, 'Pending')
            """, (
                page.get('city'),
                page.get('state'),
                page.get('keyword'),
                page.get('wiki_url')
            ))
            inserted_count += 1
        
        conn.commit()
        
        # Second pass: Insert spokes with parent references
        for page in spokes:
            parent_hub_id = None
            parent_city = page.get('parent_city')
            
            if parent_city:
                cursor.execute(
                    "SELECT id FROM pages WHERE city = ? AND page_type = 'Hub' LIMIT 1",
                    (parent_city,)
                )
                result = cursor.fetchone()
                if result:
                    parent_hub_id = result['id']
            
            cursor.execute("""
                INSERT INTO pages (city, state, keyword, page_type, parent_hub_id, wiki_url, status)
                VALUES (?, ?, ?, 'Spoke', ?, ?, 'Pending')
            """, (
                page.get('city'),
                page.get('state'),
                page.get('keyword'),
                parent_hub_id,
                page.get('wiki_url')
            ))
            inserted_count += 1
        
        conn.commit()
        return inserted_count


def update_wiki_url(page_id: int, wiki_url: str):
    """Update the Wikipedia URL for a specific page."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pages 
            SET wiki_url = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (wiki_url, page_id))
        conn.commit()


def update_page_status(page_id: int, status: str):
    """Update the status of a page."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pages 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (status, page_id))
        conn.commit()


def update_serp_data(page_id: int, serp_data: dict):
    """Update SERP data for a page (stored as JSON)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pages 
            SET serp_data = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (json.dumps(serp_data), page_id))
        conn.commit()


def update_html_content(page_id: int, html_content: str):
    """Update the generated HTML content for a page."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pages 
            SET html_content = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (html_content, page_id))
        conn.commit()


def update_live_url(page_id: int, live_url: str):
    """Update the live URL after deployment."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pages 
            SET live_url = ?, status = 'Published', updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (live_url, page_id))
        conn.commit()


def get_all_pages() -> List[Dict]:
    """Retrieve all pages from the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.id, p.city, p.state, p.keyword, p.page_type, 
                p.parent_hub_id, ph.city as parent_city,
                p.wiki_url, p.status, p.serp_data, 
                p.html_content, p.live_url, p.created_at, p.updated_at
            FROM pages p
            LEFT JOIN pages ph ON p.parent_hub_id = ph.id
            ORDER BY p.page_type DESC, p.city ASC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_pages_by_status(status: str) -> List[Dict]:
    """Retrieve pages filtered by status."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.id, p.city, p.state, p.keyword, p.page_type, 
                p.parent_hub_id, ph.city as parent_city,
                p.wiki_url, p.status, p.created_at
            FROM pages p
            LEFT JOIN pages ph ON p.parent_hub_id = ph.id
            WHERE p.status = ?
            ORDER BY p.page_type DESC, p.city ASC
        """, (status,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_hub_pages() -> List[Dict]:
    """Retrieve all Hub pages."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, city, state, wiki_url, status
            FROM pages
            WHERE page_type = 'Hub'
            ORDER BY city ASC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_spokes_for_hub(hub_id: int) -> List[Dict]:
    """Retrieve all Spoke pages for a specific Hub."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, city, state, keyword, wiki_url, status
            FROM pages
            WHERE parent_hub_id = ?
            ORDER BY city ASC
        """, (hub_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_page_by_id(page_id: int) -> Optional[Dict]:
    """Retrieve a single page by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_status_counts() -> Dict[str, int]:
    """Get count of pages by status."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM pages
            GROUP BY status
        """)
        rows = cursor.fetchall()
        return {row['status']: row['count'] for row in rows}


def get_page_type_counts() -> Dict[str, int]:
    """Get count of pages by type."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT page_type, COUNT(*) as count
            FROM pages
            GROUP BY page_type
        """)
        rows = cursor.fetchall()
        return {row['page_type']: row['count'] for row in rows}


def delete_page(page_id: int):
    """Delete a page by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pages WHERE id = ?", (page_id,))
        conn.commit()


def clear_all_pages():
    """Clear all pages from the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pages")
        conn.commit()


def page_exists(city: str, page_type: str) -> bool:
    """Check if a page already exists for a city and type combination."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM pages WHERE city = ? AND page_type = ? LIMIT 1",
            (city, page_type)
        )
        return cursor.fetchone() is not None


# Initialize database on module import
init_database()
