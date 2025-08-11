#!/usr/bin/env python3
"""
Explorator Error Scenario Test for UI Screenshot
Specific test to trigger Explorator error state as requested
"""

import requests
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://3afd5048-b1fe-4fd7-b71e-338e9cf21c47.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def trigger_explorator_error_scenario():
    """
    Execute the specific scenario requested:
    1) POST /api/scenarios/agent_error_retry with body {"minutes": 1}
    2) Immediately GET /api/agents and return current agents JSON (expect Explorator red)
    """
    
    print(f"Triggering Explorator Error Scenario - API Base: {API_BASE}")
    print("=" * 60)
    
    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json'})
    
    # Step 1: POST /api/scenarios/agent_error_retry with body {"minutes": 1}
    print("\nStep 1: Triggering Explorator error with 1-minute retry window...")
    
    error_payload = {"minutes": 1}
    
    try:
        start_time = time.time()
        response = session.post(f"{API_BASE}/scenarios/agent_error_retry", json=error_payload)
        duration = time.time() - start_time
        
        print(f"POST /api/scenarios/agent_error_retry")
        print(f"Request Body: {json.dumps(error_payload, indent=2)}")
        print(f"Status Code: {response.status_code}")
        print(f"Duration: {duration:.3f}s")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"Response JSON:")
            print(json.dumps(response_data, indent=2))
            
            # Verify the response structure
            agent_data = response_data.get('agent', {})
            if (agent_data.get('agent_name') == 'Explorator' and 
                agent_data.get('status_light') == 'red' and 
                agent_data.get('error_state') == 'crawl_timeout'):
                print("✅ Explorator error triggered successfully")
            else:
                print("⚠️  Explorator error response unexpected")
                
        else:
            print(f"❌ Error triggering scenario: {response.status_code} - {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Exception during error trigger: {e}")
        return
    
    # Step 2: Immediately GET /api/agents and return current agents JSON
    print("\nStep 2: Getting current agents status (expecting Explorator red)...")
    
    try:
        start_time = time.time()
        response = session.get(f"{API_BASE}/agents")
        duration = time.time() - start_time
        
        print(f"GET /api/agents")
        print(f"Status Code: {response.status_code}")
        print(f"Duration: {duration:.3f}s")
        
        if response.status_code == 200:
            agents_data = response.json()
            print(f"Agents JSON Response:")
            print(json.dumps(agents_data, indent=2))
            
            # Find Explorator and verify it's red
            explorator = next((agent for agent in agents_data if agent.get('agent_name') == 'Explorator'), None)
            
            if explorator:
                status = explorator.get('status_light')
                error_state = explorator.get('error_state')
                next_retry = explorator.get('next_retry_at')
                
                print(f"\n🔍 Explorator Status Analysis:")
                print(f"   Status Light: {status}")
                print(f"   Error State: {error_state}")
                print(f"   Next Retry At: {next_retry}")
                
                if status == 'red':
                    print("✅ Explorator is RED as expected for UI screenshot")
                else:
                    print(f"⚠️  Explorator is {status}, not red as expected")
            else:
                print("❌ Explorator not found in agents response")
                
            # Show all agents status for context
            print(f"\n📊 All Agents Status Summary:")
            for agent in agents_data:
                name = agent.get('agent_name', 'Unknown')
                status = agent.get('status_light', 'Unknown')
                error = agent.get('error_state', 'None')
                print(f"   {name}: {status} (error: {error})")
                
        else:
            print(f"❌ Error getting agents: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception during agents fetch: {e}")
    
    print("\n" + "=" * 60)
    print("Explorator Error Scenario Complete")
    print("UI screenshot can now be taken with Explorator in red error state")
    print("=" * 60)

if __name__ == "__main__":
    trigger_explorator_error_scenario()