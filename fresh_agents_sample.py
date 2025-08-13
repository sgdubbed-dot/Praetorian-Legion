#!/usr/bin/env python3
"""
Fresh Agents Sample Generator for Report
Provides fresh GET /api/agents JSON after auto-reset with Phoenix timestamps
Confirms Explorator error_state and next_retry_at are null post-reset
"""

import requests
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://progress-pulse-21.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def make_request(method: str, endpoint: str, data: dict = None):
    """Make HTTP request and return response"""
    url = f"{API_BASE}{endpoint}"
    headers = {'Content-Type': 'application/json'}
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
            
        return response.status_code < 400, response
        
    except Exception as e:
        return False, str(e)

def generate_fresh_agents_sample():
    """Generate fresh agents sample after auto-reset"""
    print("=" * 80)
    print("FRESH AGENTS SAMPLE GENERATOR FOR REPORT")
    print("=" * 80)
    print(f"Backend URL: {API_BASE}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Step 1: Trigger Explorator error with 1-minute retry window
    print("Step 1: Triggering Explorator error with 1-minute retry window...")
    error_data = {"minutes": 1}
    success, response = make_request('POST', '/scenarios/agent_error_retry', error_data)
    
    if not success:
        print(f"❌ Failed to trigger Explorator error: {response}")
        return
        
    try:
        result = response.json()
        agent_data = result.get('agent', {})
        print(f"✅ Explorator error triggered successfully")
        print(f"   Status: {agent_data.get('status_light')}")
        print(f"   Error State: {agent_data.get('error_state')}")
        print(f"   Next Retry: {agent_data.get('next_retry_at')}")
        print()
    except Exception as e:
        print(f"❌ Error parsing response: {e}")
        return
    
    # Step 2: Immediate GET /api/agents to show error state
    print("Step 2: Immediate GET /api/agents (showing error state)...")
    success, response = make_request('GET', '/agents')
    
    if not success:
        print(f"❌ Failed to get agents: {response}")
        return
        
    try:
        agents_error_state = response.json()
        print("✅ Agents retrieved in error state:")
        print(json.dumps(agents_error_state, indent=2))
        print()
        
        # Find Explorator
        explorator = next((agent for agent in agents_error_state if agent.get('agent_name') == 'Explorator'), None)
        if explorator:
            print(f"Explorator Status: {explorator.get('status_light')}")
            print(f"Explorator Error State: {explorator.get('error_state')}")
            print(f"Explorator Next Retry: {explorator.get('next_retry_at')}")
        print()
        
    except Exception as e:
        print(f"❌ Error parsing agents response: {e}")
        return
    
    # Step 3: Wait for auto-reset (75 seconds to ensure retry time passes)
    print("Step 3: Waiting 75 seconds for auto-reset...")
    time.sleep(75)
    
    # Step 4: GET /api/agents after auto-reset
    print("Step 4: GET /api/agents after auto-reset (FRESH SAMPLE FOR REPORT)...")
    success, response = make_request('GET', '/agents')
    
    if not success:
        print(f"❌ Failed to get agents after auto-reset: {response}")
        return
        
    try:
        agents_post_reset = response.json()
        print("✅ FRESH AGENTS SAMPLE AFTER AUTO-RESET:")
        print("=" * 60)
        print(json.dumps(agents_post_reset, indent=2))
        print("=" * 60)
        print()
        
        # Verify Explorator auto-reset
        explorator = next((agent for agent in agents_post_reset if agent.get('agent_name') == 'Explorator'), None)
        if explorator:
            status = explorator.get('status_light')
            error_state = explorator.get('error_state')
            next_retry = explorator.get('next_retry_at')
            
            print("EXPLORATOR AUTO-RESET VERIFICATION:")
            print(f"✅ Status Light: {status} (should be green or yellow)")
            print(f"✅ Error State: {error_state} (should be null)")
            print(f"✅ Next Retry At: {next_retry} (should be null)")
            
            if status in ['green', 'yellow'] and error_state is None and next_retry is None:
                print("✅ CONFIRMATION: Explorator error_state and next_retry_at are null post-reset")
            else:
                print("❌ WARNING: Explorator auto-reset may not have completed properly")
        else:
            print("❌ Explorator not found in agents list")
        
        print()
        
        # Verify Phoenix timestamps
        print("PHOENIX TIMESTAMP VERIFICATION:")
        for agent in agents_post_reset:
            agent_name = agent.get('agent_name')
            timestamps = {
                'created_at': agent.get('created_at'),
                'updated_at': agent.get('updated_at'),
                'last_activity': agent.get('last_activity')
            }
            
            print(f"{agent_name}:")
            for ts_name, ts_value in timestamps.items():
                if ts_value:
                    # Check if timestamp contains Phoenix timezone info
                    is_phoenix = '-07:00' in ts_value or '-08:00' in ts_value  # MST/MDT
                    print(f"  {ts_name}: {ts_value} {'✅ Phoenix' if is_phoenix else '❓ Check TZ'}")
                else:
                    print(f"  {ts_name}: null")
        
        print()
        print("=" * 80)
        print("FRESH SAMPLE GENERATION COMPLETE")
        print("Above JSON can be included in the report as requested")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error parsing post-reset agents response: {e}")
        return

if __name__ == "__main__":
    generate_fresh_agents_sample()