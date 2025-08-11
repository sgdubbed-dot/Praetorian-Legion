#!/usr/bin/env python3
"""
Screenshot Preparation Script for Praetorian Legion
Purpose: Prepare backend state for UI screenshots as requested
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://3afd5048-b1fe-4fd7-b71e-338e9cf21c47.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class ScreenshotPrep:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.captured_payloads = {}
        
    def make_request(self, method: str, endpoint: str, data: Dict = None) -> tuple:
        """Make HTTP request and return (success, response, duration)"""
        url = f"{API_BASE}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PATCH':
                response = self.session.patch(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            duration = time.time() - start_time
            
            if response.status_code >= 400:
                return False, response, duration
                
            return True, response, duration
            
        except Exception as e:
            duration = time.time() - start_time
            return False, str(e), duration

    def step_1_trigger_explorator_error(self):
        """Step 1: Trigger Explorator error with 1 minute retry window"""
        print("\n=== Step 1: Triggering Explorator Error ===")
        
        error_data = {"minutes": 1}
        success, response, duration = self.make_request('POST', '/scenarios/agent_error_retry', error_data)
        
        if success:
            try:
                result = response.json()
                agent_payload = result.get('agent', {})
                self.captured_payloads['explorator_error'] = agent_payload
                
                print(f"✅ Explorator error triggered successfully")
                print(f"   Agent Name: {agent_payload.get('agent_name')}")
                print(f"   Status Light: {agent_payload.get('status_light')}")
                print(f"   Error State: {agent_payload.get('error_state')}")
                print(f"   Next Retry At: {agent_payload.get('next_retry_at')}")
                print(f"   Duration: {duration:.2f}s")
                
                return True, agent_payload
                
            except Exception as e:
                print(f"❌ Failed to parse Explorator error response: {e}")
                return False, None
        else:
            print(f"❌ Failed to trigger Explorator error: {response}")
            return False, None

    def step_2_immediate_agents_check(self):
        """Step 2: Immediately GET /api/agents (expect Explorator red)"""
        print("\n=== Step 2: Immediate Agents Check (Expect Explorator Red) ===")
        
        success, response, duration = self.make_request('GET', '/agents')
        
        if success:
            try:
                agents = response.json()
                self.captured_payloads['agents_immediate'] = agents
                
                # Find Explorator
                explorator = next((agent for agent in agents if agent.get('agent_name') == 'Explorator'), None)
                
                print(f"✅ Agents retrieved successfully")
                print(f"   Total Agents: {len(agents)}")
                print(f"   Duration: {duration:.2f}s")
                
                if explorator:
                    print(f"   Explorator Status: {explorator.get('status_light')}")
                    print(f"   Explorator Error State: {explorator.get('error_state')}")
                    print(f"   Explorator Next Retry: {explorator.get('next_retry_at')}")
                    
                    if explorator.get('status_light') == 'red':
                        print("   ✅ Explorator is RED as expected")
                    else:
                        print(f"   ⚠️  Explorator is {explorator.get('status_light')}, expected RED")
                else:
                    print("   ❌ Explorator not found in agents list")
                
                # Show all agent statuses
                print("\n   All Agent Statuses:")
                for agent in agents:
                    print(f"     {agent.get('agent_name')}: {agent.get('status_light')}")
                
                return True, agents
                
            except Exception as e:
                print(f"❌ Failed to parse immediate agents response: {e}")
                return False, None
        else:
            print(f"❌ Failed to get immediate agents: {response}")
            return False, None

    def step_3_wait_and_check_reset(self):
        """Step 3: Wait ~70 seconds and check agents again (expect Explorator yellow/green)"""
        print("\n=== Step 3: Wait ~70 Seconds for Auto-Reset ===")
        
        print("Waiting 70 seconds for Explorator auto-reset...")
        time.sleep(70)
        
        success, response, duration = self.make_request('GET', '/agents')
        
        if success:
            try:
                agents = response.json()
                self.captured_payloads['agents_after_reset'] = agents
                
                # Find Explorator
                explorator = next((agent for agent in agents if agent.get('agent_name') == 'Explorator'), None)
                
                print(f"✅ Agents retrieved after reset")
                print(f"   Total Agents: {len(agents)}")
                print(f"   Duration: {duration:.2f}s")
                
                if explorator:
                    status = explorator.get('status_light')
                    error_state = explorator.get('error_state')
                    next_retry = explorator.get('next_retry_at')
                    
                    print(f"   Explorator Status: {status}")
                    print(f"   Explorator Error State: {error_state}")
                    print(f"   Explorator Next Retry: {next_retry}")
                    
                    if status in ['yellow', 'green'] and not error_state:
                        print(f"   ✅ Explorator auto-reset successful to {status}")
                    else:
                        print(f"   ⚠️  Explorator auto-reset may have issues - status: {status}, error: {error_state}")
                else:
                    print("   ❌ Explorator not found in agents list")
                
                # Show all agent statuses
                print("\n   All Agent Statuses After Reset:")
                for agent in agents:
                    print(f"     {agent.get('agent_name')}: {agent.get('status_light')}")
                
                return True, agents
                
            except Exception as e:
                print(f"❌ Failed to parse post-reset agents response: {e}")
                return False, None
        else:
            print(f"❌ Failed to get post-reset agents: {response}")
            return False, None

    def step_4_create_research_mission(self):
        """Step 4: Create research_only mission and confirm Legatus yellow"""
        print("\n=== Step 4: Create Research-Only Mission (Force Legatus Idle) ===")
        
        # Create research_only mission
        mission_data = {
            "title": "Screenshot Research",
            "objective": "force legatus idle",
            "posture": "research_only",
            "state": "scanning"
        }
        
        success, response, duration = self.make_request('POST', '/missions', mission_data)
        
        if success:
            try:
                mission = response.json()
                mission_id = mission.get('id')
                self.captured_payloads['research_mission'] = mission
                
                print(f"✅ Research mission created successfully")
                print(f"   Mission ID: {mission_id}")
                print(f"   Title: {mission.get('title')}")
                print(f"   Posture: {mission.get('posture')}")
                print(f"   State: {mission.get('state')}")
                print(f"   Duration: {duration:.2f}s")
                
                # Now check agents to confirm Legatus is yellow
                time.sleep(1)  # Small delay for processing
                
                success, response, duration = self.make_request('GET', '/agents')
                
                if success:
                    try:
                        agents = response.json()
                        self.captured_payloads['agents_with_research_mission'] = agents
                        
                        # Find Legatus
                        legatus = next((agent for agent in agents if agent.get('agent_name') == 'Legatus'), None)
                        
                        print(f"\n   Agents check after research mission:")
                        print(f"   Duration: {duration:.2f}s")
                        
                        if legatus:
                            status = legatus.get('status_light')
                            print(f"   Legatus Status: {status}")
                            
                            if status == 'yellow':
                                print("   ✅ Legatus is YELLOW as expected (forced idle by research_only)")
                            else:
                                print(f"   ⚠️  Legatus is {status}, expected YELLOW")
                        else:
                            print("   ❌ Legatus not found in agents list")
                        
                        # Show all agent statuses
                        print("\n   All Agent Statuses with Research Mission:")
                        for agent in agents:
                            print(f"     {agent.get('agent_name')}: {agent.get('status_light')}")
                        
                        return True, mission_id
                        
                    except Exception as e:
                        print(f"❌ Failed to parse agents after research mission: {e}")
                        return False, mission_id
                else:
                    print(f"❌ Failed to get agents after research mission: {response}")
                    return False, mission_id
                
            except Exception as e:
                print(f"❌ Failed to parse research mission response: {e}")
                return False, None
        else:
            print(f"❌ Failed to create research mission: {response}")
            return False, None

    def step_5_fetch_explorator_events(self):
        """Step 5: Fetch recent Explorator events"""
        print("\n=== Step 5: Fetch Recent Explorator Events ===")
        
        success, response, duration = self.make_request('GET', '/events?agent_name=Explorator&limit=10')
        
        if success:
            try:
                events = response.json()
                self.captured_payloads['explorator_events'] = events
                
                print(f"✅ Explorator events retrieved successfully")
                print(f"   Total Events: {len(events)}")
                print(f"   Duration: {duration:.2f}s")
                
                # Show recent events
                print("\n   Recent Explorator Events:")
                for i, event in enumerate(events[:5]):  # Show top 5
                    print(f"     {i+1}. {event.get('event_name')} at {event.get('timestamp')}")
                    if event.get('payload'):
                        payload_summary = {k: v for k, v in event.get('payload', {}).items() if k in ['agent_name', 'status_light', 'error_state']}
                        if payload_summary:
                            print(f"        Payload: {payload_summary}")
                
                return True, events
                
            except Exception as e:
                print(f"❌ Failed to parse Explorator events response: {e}")
                return False, None
        else:
            print(f"❌ Failed to get Explorator events: {response}")
            return False, None

    def run_screenshot_prep(self):
        """Run all screenshot preparation steps"""
        print("=" * 80)
        print("SCREENSHOT PREPARATION FOR PRAETORIAN LEGION UI")
        print("=" * 80)
        print(f"Backend URL: {API_BASE}")
        
        start_time = time.time()
        results = {}
        
        # Step 1: Trigger Explorator error
        success, payload = self.step_1_trigger_explorator_error()
        results['step_1'] = {'success': success, 'payload': payload}
        
        if not success:
            print("\n❌ Step 1 failed - cannot continue")
            return results
        
        # Step 2: Immediate agents check
        success, payload = self.step_2_immediate_agents_check()
        results['step_2'] = {'success': success, 'payload': payload}
        
        # Step 3: Wait and check reset
        success, payload = self.step_3_wait_and_check_reset()
        results['step_3'] = {'success': success, 'payload': payload}
        
        # Step 4: Create research mission
        success, mission_id = self.step_4_create_research_mission()
        results['step_4'] = {'success': success, 'mission_id': mission_id}
        
        # Step 5: Fetch Explorator events
        success, payload = self.step_5_fetch_explorator_events()
        results['step_5'] = {'success': success, 'payload': payload}
        
        total_duration = time.time() - start_time
        
        # Final Summary
        print("\n" + "=" * 80)
        print("SCREENSHOT PREPARATION SUMMARY")
        print("=" * 80)
        
        successful_steps = sum(1 for step_result in results.values() if step_result['success'])
        total_steps = len(results)
        
        print(f"Total Steps: {total_steps}")
        print(f"Successful: {successful_steps}")
        print(f"Failed: {total_steps - successful_steps}")
        print(f"Total Duration: {total_duration:.2f}s")
        
        print("\nStep Results:")
        step_names = [
            "Trigger Explorator Error",
            "Immediate Agents Check (Red)",
            "Wait & Check Reset (Yellow/Green)",
            "Create Research Mission (Legatus Yellow)",
            "Fetch Explorator Events"
        ]
        
        for i, (step_key, step_result) in enumerate(results.items()):
            status = "✅ SUCCESS" if step_result['success'] else "❌ FAILED"
            print(f"  {step_names[i]}: {status}")
        
        # Show captured payloads for reference
        print("\n" + "=" * 80)
        print("CAPTURED PAYLOADS FOR REPORT")
        print("=" * 80)
        
        for key, payload in self.captured_payloads.items():
            print(f"\n{key.upper()}:")
            if isinstance(payload, dict):
                print(json.dumps(payload, indent=2)[:500] + ("..." if len(json.dumps(payload, indent=2)) > 500 else ""))
            elif isinstance(payload, list):
                print(f"List with {len(payload)} items")
                if payload:
                    print(json.dumps(payload[0], indent=2)[:300] + ("..." if len(json.dumps(payload[0], indent=2)) > 300 else ""))
        
        return results

if __name__ == "__main__":
    prep = ScreenshotPrep()
    results = prep.run_screenshot_prep()