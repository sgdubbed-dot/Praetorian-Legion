#!/usr/bin/env python3
"""
Backend API Testing for Praetorian Legion
Focus: Agents logic verification as per review request
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
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://301c5be1-4e78-475c-ae49-680426ffd796.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class BackendTester:
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def log_result(self, test_name: str, success: bool, message: str, response_data: Any = None, duration: float = 0):
        """Log test result with details"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'duration_ms': round(duration * 1000, 2),
            'timestamp': datetime.now().isoformat()
        }
        if response_data:
            result['response_data'] = response_data
        self.results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message} ({result['duration_ms']}ms)")
        
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

    def test_health_endpoints(self):
        """Test 1: Lint error elimination - Health endpoints"""
        print("\n=== Testing Health Endpoints ===")
        
        # Test GET /api/health
        success, response, duration = self.make_request('GET', '/health')
        if success:
            try:
                data = response.json()
                if data.get('ok') is True and 'timestamp' in data:
                    self.log_result('health_endpoint', True, 'Health endpoint working correctly', data, duration)
                else:
                    self.log_result('health_endpoint', False, f'Health endpoint returned unexpected data: {data}', data, duration)
            except Exception as e:
                self.log_result('health_endpoint', False, f'Health endpoint JSON parse error: {e}', None, duration)
        else:
            self.log_result('health_endpoint', False, f'Health endpoint failed: {response}', None, duration)
        
        # Test GET /api/
        success, response, duration = self.make_request('GET', '/')
        if success:
            try:
                data = response.json()
                if 'message' in data and 'API ready' in data['message']:
                    self.log_result('root_endpoint', True, 'Root endpoint working correctly', data, duration)
                else:
                    self.log_result('root_endpoint', False, f'Root endpoint returned unexpected data: {data}', data, duration)
            except Exception as e:
                self.log_result('root_endpoint', False, f'Root endpoint JSON parse error: {e}', None, duration)
        else:
            self.log_result('root_endpoint', False, f'Root endpoint failed: {response}', None, duration)

    def test_agents_seeding(self):
        """Test 2: Agents seeding & presence"""
        print("\n=== Testing Agents Seeding & Presence ===")
        
        # First call to GET /api/agents
        success, response, duration = self.make_request('GET', '/agents')
        if success:
            try:
                agents = response.json()
                agent_names = [agent.get('agent_name') for agent in agents]
                expected_agents = ['Praefectus', 'Explorator', 'Legatus']
                
                if all(name in agent_names for name in expected_agents):
                    self.log_result('agents_seeding_first', True, f'All three agents present: {agent_names}', agents, duration)
                else:
                    missing = [name for name in expected_agents if name not in agent_names]
                    self.log_result('agents_seeding_first', False, f'Missing agents: {missing}', agents, duration)
                    
            except Exception as e:
                self.log_result('agents_seeding_first', False, f'Agents endpoint JSON parse error: {e}', None, duration)
        else:
            self.log_result('agents_seeding_first', False, f'Agents endpoint failed: {response}', None, duration)
            return
        
        # Second call to verify idempotency
        time.sleep(1)  # Small delay
        success, response, duration = self.make_request('GET', '/agents')
        if success:
            try:
                agents2 = response.json()
                agent_names2 = [agent.get('agent_name') for agent in agents2]
                expected_agents = ['Praefectus', 'Explorator', 'Legatus']
                
                if all(name in agent_names2 for name in expected_agents):
                    self.log_result('agents_seeding_second', True, f'Idempotency verified - agents persist: {agent_names2}', agents2, duration)
                else:
                    missing = [name for name in expected_agents if name not in agent_names2]
                    self.log_result('agents_seeding_second', False, f'Idempotency failed - missing agents: {missing}', agents2, duration)
                    
            except Exception as e:
                self.log_result('agents_seeding_second', False, f'Second agents call JSON parse error: {e}', None, duration)
        else:
            self.log_result('agents_seeding_second', False, f'Second agents call failed: {response}', None, duration)

    def test_research_only_legatus_logic(self):
        """Test 3: Research-only Legatus logic"""
        print("\n=== Testing Research-only Legatus Logic ===")
        
        # Create a research_only mission
        mission_data = {
            "title": "Test Research Mission",
            "objective": "Test research-only posture logic",
            "posture": "research_only",
            "state": "draft"
        }
        
        success, response, duration = self.make_request('POST', '/missions', mission_data)
        if not success:
            self.log_result('create_research_mission', False, f'Failed to create research mission: {response}', None, duration)
            return
            
        try:
            mission = response.json()
            mission_id = mission.get('id')
            self.log_result('create_research_mission', True, f'Research mission created: {mission_id}', mission, duration)
        except Exception as e:
            self.log_result('create_research_mission', False, f'Mission creation JSON parse error: {e}', None, duration)
            return
        
        # Check agents - Legatus should be yellow
        time.sleep(1)
        success, response, duration = self.make_request('GET', '/agents')
        if success:
            try:
                agents = response.json()
                legatus = next((agent for agent in agents if agent.get('agent_name') == 'Legatus'), None)
                
                if legatus and legatus.get('status_light') == 'yellow':
                    self.log_result('legatus_yellow_research', True, 'Legatus correctly set to yellow for research_only mission', legatus, duration)
                else:
                    self.log_result('legatus_yellow_research', False, f'Legatus not yellow - status: {legatus.get("status_light") if legatus else "not found"}', legatus, duration)
                    
            except Exception as e:
                self.log_result('legatus_yellow_research', False, f'Agents check JSON parse error: {e}', None, duration)
        else:
            self.log_result('legatus_yellow_research', False, f'Agents check failed: {response}', None, duration)
        
        # Change mission state to complete
        success, response, duration = self.make_request('POST', f'/missions/{mission_id}/state', {"state": "complete"})
        if success:
            self.log_result('complete_research_mission', True, 'Research mission marked as complete', None, duration)
        else:
            self.log_result('complete_research_mission', False, f'Failed to complete mission: {response}', None, duration)
            return
        
        # Check agents again - Legatus should move off forced yellow
        time.sleep(1)
        success, response, duration = self.make_request('GET', '/agents')
        if success:
            try:
                agents = response.json()
                legatus = next((agent for agent in agents if agent.get('agent_name') == 'Legatus'), None)
                
                if legatus:
                    # According to the logic, if no active research_only missions, Legatus should be yellow (no approved hotleads) or green (with approved hotleads)
                    status = legatus.get('status_light')
                    if status in ['yellow', 'green']:
                        self.log_result('legatus_post_complete', True, f'Legatus correctly updated after mission complete: {status}', legatus, duration)
                    else:
                        self.log_result('legatus_post_complete', False, f'Legatus unexpected status after mission complete: {status}', legatus, duration)
                else:
                    self.log_result('legatus_post_complete', False, 'Legatus not found after mission complete', None, duration)
                    
            except Exception as e:
                self.log_result('legatus_post_complete', False, f'Post-complete agents check JSON parse error: {e}', None, duration)
        else:
            self.log_result('legatus_post_complete', False, f'Post-complete agents check failed: {response}', None, duration)

    def test_explorator_error_auto_reset(self):
        """Test 4: Explorator error + auto-reset"""
        print("\n=== Testing Explorator Error & Auto-reset ===")
        
        # Call POST /api/scenarios/agent_error_retry with 1 minute
        error_data = {"minutes": 1}
        success, response, duration = self.make_request('POST', '/scenarios/agent_error_retry', error_data)
        
        if not success:
            self.log_result('explorator_error_setup', False, f'Failed to set Explorator error: {response}', None, duration)
            return
            
        try:
            result = response.json()
            agent_data = result.get('agent', {})
            
            # Verify response sets Explorator to red with error_state=crawl_timeout
            if (agent_data.get('agent_name') == 'Explorator' and 
                agent_data.get('status_light') == 'red' and 
                agent_data.get('error_state') == 'crawl_timeout' and
                agent_data.get('next_retry_at')):
                
                retry_time = agent_data.get('next_retry_at')
                self.log_result('explorator_error_setup', True, f'Explorator error set correctly, retry at: {retry_time}', agent_data, duration)
            else:
                self.log_result('explorator_error_setup', False, f'Explorator error setup incorrect: {agent_data}', agent_data, duration)
                return
                
        except Exception as e:
            self.log_result('explorator_error_setup', False, f'Error setup JSON parse error: {e}', None, duration)
            return
        
        # Immediately check GET /api/agents - should still be red
        success, response, duration = self.make_request('GET', '/agents')
        if success:
            try:
                agents = response.json()
                explorator = next((agent for agent in agents if agent.get('agent_name') == 'Explorator'), None)
                
                if explorator and explorator.get('status_light') == 'red':
                    self.log_result('explorator_immediate_red', True, 'Explorator correctly red immediately after error', explorator, duration)
                else:
                    self.log_result('explorator_immediate_red', False, f'Explorator not red immediately: {explorator.get("status_light") if explorator else "not found"}', explorator, duration)
                    
            except Exception as e:
                self.log_result('explorator_immediate_red', False, f'Immediate check JSON parse error: {e}', None, duration)
        else:
            self.log_result('explorator_immediate_red', False, f'Immediate agents check failed: {response}', None, duration)
        
        # Wait ~65-75 seconds for auto-reset (keeping within 3 minutes total)
        print("Waiting 70 seconds for auto-reset...")
        time.sleep(70)
        
        # Check agents again - Explorator should auto-reset to yellow or green
        success, response, duration = self.make_request('GET', '/agents')
        if success:
            try:
                agents = response.json()
                explorator = next((agent for agent in agents if agent.get('agent_name') == 'Explorator'), None)
                
                if explorator:
                    status = explorator.get('status_light')
                    error_state = explorator.get('error_state')
                    next_retry = explorator.get('next_retry_at')
                    
                    if status in ['yellow', 'green'] and not error_state and not next_retry:
                        self.log_result('explorator_auto_reset', True, f'Explorator auto-reset successful to: {status}', explorator, duration)
                    else:
                        self.log_result('explorator_auto_reset', False, f'Explorator auto-reset failed - status: {status}, error: {error_state}, retry: {next_retry}', explorator, duration)
                else:
                    self.log_result('explorator_auto_reset', False, 'Explorator not found during auto-reset check', None, duration)
                    
            except Exception as e:
                self.log_result('explorator_auto_reset', False, f'Auto-reset check JSON parse error: {e}', None, duration)
        else:
            self.log_result('explorator_auto_reset', False, f'Auto-reset agents check failed: {response}', None, duration)

    def test_events_endpoint(self):
        """Test 5: Events endpoint"""
        print("\n=== Testing Events Endpoint ===")
        
        # Test general events endpoint
        success, response, duration = self.make_request('GET', '/events?limit=50')
        if success:
            try:
                events = response.json()
                if isinstance(events, list):
                    self.log_result('events_general', True, f'Events endpoint working - {len(events)} events found', {'count': len(events)}, duration)
                else:
                    self.log_result('events_general', False, f'Events endpoint returned non-list: {type(events)}', events, duration)
                    
            except Exception as e:
                self.log_result('events_general', False, f'Events endpoint JSON parse error: {e}', None, duration)
        else:
            self.log_result('events_general', False, f'Events endpoint failed: {response}', None, duration)
        
        # Test Explorator-specific events
        success, response, duration = self.make_request('GET', '/events?agent_name=Explorator&limit=20')
        if success:
            try:
                events = response.json()
                if isinstance(events, list):
                    # Look for expected event types
                    event_names = [event.get('event_name') for event in events]
                    expected_events = ['agent_error_detected', 'agent_retry_scheduled', 'agent_error_cleared', 'agent_status_changed']
                    found_events = [name for name in expected_events if name in event_names]
                    
                    # Check for Phoenix timestamps
                    has_phoenix_timestamps = all('timestamp' in event and event['timestamp'] for event in events[:5])
                    
                    self.log_result('events_explorator', True, 
                                  f'Explorator events found: {len(events)} total, expected events: {found_events}, Phoenix timestamps: {has_phoenix_timestamps}', 
                                  {'count': len(events), 'found_events': found_events, 'sample_events': events[:3]}, duration)
                else:
                    self.log_result('events_explorator', False, f'Explorator events returned non-list: {type(events)}', events, duration)
                    
            except Exception as e:
                self.log_result('events_explorator', False, f'Explorator events JSON parse error: {e}', None, duration)
        else:
            self.log_result('events_explorator', False, f'Explorator events endpoint failed: {response}', None, duration)

    def run_all_tests(self):
        """Run all backend API tests"""
        print(f"Starting Backend API Tests - Base URL: {API_BASE}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run tests in order
        self.test_health_endpoints()
        self.test_agents_seeding()
        self.test_research_only_legatus_logic()
        self.test_explorator_error_auto_reset()
        self.test_events_endpoint()
        
        total_duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 60)
        print("BACKEND API TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - passed
        
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total Duration: {total_duration:.2f}s")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['message']}")
        
        return self.results

if __name__ == "__main__":
    tester = BackendTester()
    results = tester.run_all_tests()