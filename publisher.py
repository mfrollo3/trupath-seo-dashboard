"""
publisher.py - The "Driver"
Runs 24/7. Checks for 'Content Ready' pages and drips them to WordPress.
"""
import time
import base64
import requests
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BlockingScheduler
import database as db  # Your existing database module

# Configure Logging (So you can see what happened later)
logging.basicConfig(filename='drip_log.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def post_to_wordpress(page, campaign):
    """Push a single page to WordPress via REST API."""
    
    url = f"{campaign['wp_url'].rstrip('/')}/wp-json/wp/v2/pages"
    
    # Auth String (Username:AppPassword)
    credentials = f"{campaign['wp_username']}:{campaign['wp_app_password']}"
    token = base64.b64encode(credentials.encode())
    headers = {'Authorization': f'Basic {token.decode("utf-8")}'}

    # Prepare Data
    post_data = {
        'title': page['keyword'].title(), # Or parse from HTML
        'content': page['html_content'],
        'status': 'publish',
        'slug': page['keyword'].replace(" ", "-").lower()
    }

    # Handle Hierarchy (Parent Page)
    if page['page_type'] == 'Spoke' and page['parent_hub_id']:
        # Logic to find the WP ID of the parent hub would go here
        # For simplicity, we assume parent is already posted or we post as top-level first
        pass 

    try:
        response = requests.post(url, headers=headers, json=post_data)
        if response.status_code == 201:
            logging.info(f"✅ Published: {page['keyword']} to {campaign['wp_url']}")
            return True, response.json().get('link')
        else:
            logging.error(f"❌ Failed ({response.status_code}): {response.text}")
            return False, None
    except Exception as e:
        logging.error(f"❌ Connection Error: {str(e)}")
        return False, None

def run_drip_cycle():
    """Main loop: Check all campaigns and publish if quota allows."""
    logging.info("⏳ Starting Drip Cycle...")
    
    campaigns = db.get_active_campaigns() # You need to add this getter to database.py
    
    for camp in campaigns:
        # 1. Check "Safety Limit" (Have we published too much today?)
        today_count = db.get_published_count_today(camp['id']) # Add this to db
        limit = camp['drip_rate_per_day']
        
        if today_count >= limit:
            logging.info(f"🛑 Limit reached for {camp['campaign_name']} ({today_count}/{limit}). Skipping.")
            continue

        # 2. Get next "Ready" page
        next_page = db.get_next_ready_page(camp['id']) # Add this to db
        
        if next_page:
            success, live_url = post_to_wordpress(next_page, camp)
            if success:
                # Update DB
                db.update_page_status(next_page['id'], 'Published')
                db.update_live_url(next_page['id'], live_url)
                
                # Sleep briefly to be gentle on server
                time.sleep(10) 
        else:
            logging.info(f"💤 No content ready for {camp['campaign_name']}")

# --- The Scheduler ---
if __name__ == "__main__":
    scheduler = BlockingScheduler()
    
    # Run the drip cycle every hour
    scheduler.add_job(run_drip_cycle, 'interval', hours=1)
    
    print("🤖 Drip Publisher Bot Started. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
