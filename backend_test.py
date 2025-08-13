#!/usr/bin/env python3
"""
Backend API Testing for Praetorian Legion - Comprehensive Testing After Major Fixes
Focus: Test all critical endpoints including Agents, Prospects, HotLeads, Guardrails, Missions, Mission Control
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://progress-pulse-21.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class ComprehensiveBackendTester:
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.test_data = {}  # Store created test data for cleanup/reference
        
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
        
    def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> tuple:
        """Make HTTP request and return (success, response, duration)"""
        url = f"{API_BASE}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params)
            elif method.upper() == 'PATCH':
                response = self.session.patch(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            duration = time.time() - start_time
            return True, response, duration
            
        except Exception as e:
            duration = time.time() - start_time
            return False, str(e), duration

    def verify_phoenix_timestamps(self, data: Any, context: str = "") -> bool:
        """Verify Phoenix timezone timestamps are present"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['created_at', 'updated_at', 'timestamp', 'last_activity', 'next_retry_at'] and value:
                    if '-07:00' in str(value):
                        return True
            # Check nested objects
            for value in data.values():
                if self.verify_phoenix_timestamps(value, context):
                    return True
        elif isinstance(data, list):
            for item in data:
                if self.verify_phoenix_timestamps(item, context):
                    return True
        return False

    def test_health_endpoints(self):
        """Test basic health endpoints"""
        print("\n=== TESTING HEALTH ENDPOINTS ===")
        
        # Test GET /api/health
        success, response, duration = self.make_request('GET', '/health')
        if success and response.status_code == 200:
            try:
                data = response.json()
                phoenix_ok = self.verify_phoenix_timestamps(data)
                self.log_result('health_endpoint', True, 
                              f'Health endpoint working, Phoenix timestamps: {phoenix_ok}', 
                              data, duration)
            except:
                self.log_result('health_endpoint', False, 'Health endpoint returned invalid JSON', None, duration)
        else:
            self.log_result('health_endpoint', False, 
                          f'Health endpoint failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
        
        # Test GET /api/ (root)
        success, response, duration = self.make_request('GET', '/')
        if success and response.status_code == 200:
            try:
                data = response.json()
                phoenix_ok = self.verify_phoenix_timestamps(data)
                self.log_result('root_endpoint', True, 
                              f'Root endpoint working, Phoenix timestamps: {phoenix_ok}', 
                              data, duration)
            except:
                self.log_result('root_endpoint', False, 'Root endpoint returned invalid JSON', None, duration)
        else:
            self.log_result('root_endpoint', False, 
                          f'Root endpoint failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_agents_system(self):
        """Test Agents system - should return 3 agents with proper status"""
        print("\n=== TESTING AGENTS SYSTEM ===")
        
        # Test GET /api/agents
        success, response, duration = self.make_request('GET', '/agents')
        if not success or response.status_code != 200:
            self.log_result('agents_list', False, 
                          f'GET /api/agents failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        try:
            agents_data = response.json()
            if not isinstance(agents_data, list):
                self.log_result('agents_list', False, 'Agents endpoint returned non-array', agents_data, duration)
                return
            
            # Check for three core agents
            agent_names = [a.get('agent_name') for a in agents_data]
            expected_agents = ['Praefectus', 'Explorator', 'Legatus']
            missing_agents = [name for name in expected_agents if name not in agent_names]
            
            if missing_agents:
                self.log_result('agents_list', False, 
                              f'Missing agents: {missing_agents}. Found: {agent_names}', 
                              agents_data, duration)
                return
            
            phoenix_ok = self.verify_phoenix_timestamps(agents_data)
            self.log_result('agents_list', True, 
                          f'All 3 agents present: {agent_names}, Phoenix timestamps: {phoenix_ok}', 
                          {'agent_count': len(agents_data), 'agents': agent_names, 'phoenix_timestamps': phoenix_ok}, duration)
            
            # Store agents for later tests
            self.test_data['agents'] = agents_data
            
        except Exception as e:
            self.log_result('agents_list', False, f'JSON parse error: {e}', None, duration)
            return
        
        # Test agent error scenario
        print("\n--- Testing Agent Error Scenario ---")
        success, response, duration = self.make_request('POST', '/scenarios/agent_error_retry', {'minutes': 1})
        if success and response.status_code == 200:
            try:
                error_data = response.json()
                agent_data = error_data.get('agent', {})
                if agent_data.get('agent_name') == 'Explorator' and agent_data.get('status_light') == 'red':
                    self.log_result('agent_error_scenario', True, 
                                  f'Explorator error scenario triggered successfully, status: {agent_data.get("status_light")}', 
                                  error_data, duration)
                else:
                    self.log_result('agent_error_scenario', False, 
                                  f'Error scenario failed - unexpected agent data: {agent_data}', 
                                  error_data, duration)
            except Exception as e:
                self.log_result('agent_error_scenario', False, f'JSON parse error: {e}', None, duration)
        else:
            self.log_result('agent_error_scenario', False, 
                          f'Agent error scenario failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_prospects_rolodex(self):
        """Test Prospects (Rolodex) endpoints"""
        print("\n=== TESTING PROSPECTS (ROLODEX) ===")
        
        # Test GET /api/prospects
        success, response, duration = self.make_request('GET', '/prospects')
        if success and response.status_code == 200:
            try:
                prospects_data = response.json()
                if isinstance(prospects_data, list):
                    phoenix_ok = self.verify_phoenix_timestamps(prospects_data)
                    self.log_result('prospects_list', True, 
                                  f'Prospects list working, {len(prospects_data)} prospects, Phoenix timestamps: {phoenix_ok}', 
                                  {'prospect_count': len(prospects_data), 'phoenix_timestamps': phoenix_ok}, duration)
                else:
                    self.log_result('prospects_list', False, 'Prospects endpoint returned non-array', prospects_data, duration)
                    return
            except Exception as e:
                self.log_result('prospects_list', False, f'JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('prospects_list', False, 
                          f'GET /api/prospects failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Test POST /api/prospects (create test prospect)
        test_prospect = {
            "name_or_alias": "Sarah Chen",
            "handles": {
                "linkedin": "https://linkedin.com/in/sarah-chen-ai",
                "twitter": "@sarahchen_ai"
            },
            "priority_state": "warm",
            "source_type": "manual"
        }
        
        success, response, duration = self.make_request('POST', '/prospects', test_prospect)
        if success and response.status_code == 200:
            try:
                created_prospect = response.json()
                prospect_id = created_prospect.get('id')
                if prospect_id:
                    self.test_data['prospect_id'] = prospect_id
                    phoenix_ok = self.verify_phoenix_timestamps(created_prospect)
                    self.log_result('prospects_create', True, 
                                  f'Prospect created successfully: {prospect_id}, Phoenix timestamps: {phoenix_ok}', 
                                  created_prospect, duration)
                else:
                    self.log_result('prospects_create', False, 'Created prospect missing ID', created_prospect, duration)
            except Exception as e:
                self.log_result('prospects_create', False, f'JSON parse error: {e}', None, duration)
        else:
            self.log_result('prospects_create', False, 
                          f'POST /api/prospects failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_hotleads(self):
        """Test HotLeads endpoints"""
        print("\n=== TESTING HOTLEADS ===")
        
        # Test GET /api/hotleads
        success, response, duration = self.make_request('GET', '/hotleads')
        if success and response.status_code == 200:
            try:
                hotleads_data = response.json()
                if isinstance(hotleads_data, list):
                    phoenix_ok = self.verify_phoenix_timestamps(hotleads_data)
                    self.log_result('hotleads_list', True, 
                                  f'HotLeads list working, {len(hotleads_data)} hotleads, Phoenix timestamps: {phoenix_ok}', 
                                  {'hotlead_count': len(hotleads_data), 'phoenix_timestamps': phoenix_ok}, duration)
                else:
                    self.log_result('hotleads_list', False, 'HotLeads endpoint returned non-array', hotleads_data, duration)
                    return
            except Exception as e:
                self.log_result('hotleads_list', False, f'JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('hotleads_list', False, 
                          f'GET /api/hotleads failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Create test hotlead (need prospect_id)
        prospect_id = self.test_data.get('prospect_id')
        if not prospect_id:
            self.log_result('hotleads_create', False, 'No prospect_id available for hotlead creation', None, 0)
            return
        
        test_hotlead = {
            "prospect_id": prospect_id,
            "evidence": [
                {
                    "type": "social_signal",
                    "source": "twitter",
                    "content": "Just posted about needing help with AI automation for her startup",
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "proposed_script": "Hi Sarah! I saw your tweet about AI automation. We specialize in helping startups implement AI solutions efficiently. Would love to share some insights that might be helpful for your project."
        }
        
        success, response, duration = self.make_request('POST', '/hotleads', test_hotlead)
        if success and response.status_code == 200:
            try:
                created_hotlead = response.json()
                hotlead_id = created_hotlead.get('id')
                if hotlead_id:
                    self.test_data['hotlead_id'] = hotlead_id
                    phoenix_ok = self.verify_phoenix_timestamps(created_hotlead)
                    self.log_result('hotleads_create', True, 
                                  f'HotLead created successfully: {hotlead_id}, Phoenix timestamps: {phoenix_ok}', 
                                  created_hotlead, duration)
                    
                    # Test status update
                    success, response, duration = self.make_request('POST', f'/hotleads/{hotlead_id}/status', {'status': 'approved'})
                    if success and response.status_code == 200:
                        try:
                            updated_hotlead = response.json()
                            if updated_hotlead.get('status') == 'approved':
                                self.log_result('hotleads_status_update', True, 
                                              f'HotLead status updated to approved', 
                                              updated_hotlead, duration)
                            else:
                                self.log_result('hotleads_status_update', False, 
                                              f'Status update failed - status not changed', 
                                              updated_hotlead, duration)
                        except Exception as e:
                            self.log_result('hotleads_status_update', False, f'JSON parse error: {e}', None, duration)
                    else:
                        self.log_result('hotleads_status_update', False, 
                                      f'Status update failed: {response.status_code if hasattr(response, "status_code") else response}', 
                                      None, duration)
                else:
                    self.log_result('hotleads_create', False, 'Created hotlead missing ID', created_hotlead, duration)
            except Exception as e:
                self.log_result('hotleads_create', False, f'JSON parse error: {e}', None, duration)
        else:
            self.log_result('hotleads_create', False, 
                          f'POST /api/hotleads failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_guardrails(self):
        """Test Guardrails endpoints"""
        print("\n=== TESTING GUARDRAILS ===")
        
        # Test GET /api/guardrails
        success, response, duration = self.make_request('GET', '/guardrails')
        if success and response.status_code == 200:
            try:
                guardrails_data = response.json()
                if isinstance(guardrails_data, list):
                    phoenix_ok = self.verify_phoenix_timestamps(guardrails_data)
                    self.log_result('guardrails_list', True, 
                                  f'Guardrails list working, {len(guardrails_data)} guardrails, Phoenix timestamps: {phoenix_ok}', 
                                  {'guardrail_count': len(guardrails_data), 'phoenix_timestamps': phoenix_ok}, duration)
                else:
                    self.log_result('guardrails_list', False, 'Guardrails endpoint returned non-array', guardrails_data, duration)
                    return
            except Exception as e:
                self.log_result('guardrails_list', False, f'JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('guardrails_list', False, 
                          f'GET /api/guardrails failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Test POST /api/guardrails (create test guardrail)
        test_guardrail = {
            "type": "dm_etiquette",
            "scope": "global",
            "value": "No cold DMs without prior public interaction",
            "notes": "Test guardrail for comprehensive testing - always engage publicly first",
            "dm_etiquette": "Always engage publicly first before sending DMs"
        }
        
        success, response, duration = self.make_request('POST', '/guardrails', test_guardrail)
        if success and response.status_code == 200:
            try:
                created_guardrail = response.json()
                guardrail_id = created_guardrail.get('id')
                if guardrail_id:
                    self.test_data['guardrail_id'] = guardrail_id
                    phoenix_ok = self.verify_phoenix_timestamps(created_guardrail)
                    self.log_result('guardrails_create', True, 
                                  f'Guardrail created successfully: {guardrail_id}, Phoenix timestamps: {phoenix_ok}', 
                                  created_guardrail, duration)
                else:
                    self.log_result('guardrails_create', False, 'Created guardrail missing ID', created_guardrail, duration)
            except Exception as e:
                self.log_result('guardrails_create', False, f'JSON parse error: {e}', None, duration)
        else:
            self.log_result('guardrails_create', False, 
                          f'POST /api/guardrails failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_missions(self):
        """Test Missions endpoints"""
        print("\n=== TESTING MISSIONS ===")
        
        # Test GET /api/missions
        success, response, duration = self.make_request('GET', '/missions')
        if success and response.status_code == 200:
            try:
                missions_data = response.json()
                if isinstance(missions_data, list):
                    phoenix_ok = self.verify_phoenix_timestamps(missions_data)
                    self.log_result('missions_list', True, 
                                  f'Missions list working, {len(missions_data)} missions, Phoenix timestamps: {phoenix_ok}', 
                                  {'mission_count': len(missions_data), 'phoenix_timestamps': phoenix_ok}, duration)
                    
                    # Store missions for later tests
                    self.test_data['missions'] = missions_data
                else:
                    self.log_result('missions_list', False, 'Missions endpoint returned non-array', missions_data, duration)
                    return
            except Exception as e:
                self.log_result('missions_list', False, f'JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('missions_list', False, 
                          f'GET /api/missions failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Test POST /api/missions (create test mission)
        test_mission = {
            "title": "Comprehensive Backend Test Mission",
            "objective": "Test mission creation and agent integration for comprehensive backend testing",
            "posture": "research_only",
            "state": "draft",
            "agents_assigned": ["Legatus"],
            "insights": ["This is a test mission for comprehensive backend testing", "Testing insights migration to insights_rich"]
        }
        
        success, response, duration = self.make_request('POST', '/missions', test_mission)
        if success and response.status_code == 200:
            try:
                created_mission = response.json()
                mission_id = created_mission.get('id')
                if mission_id:
                    self.test_data['mission_id'] = mission_id
                    phoenix_ok = self.verify_phoenix_timestamps(created_mission)
                    
                    # Check if insights_rich was auto-populated
                    insights_rich = created_mission.get('insights_rich', [])
                    insights_migration_ok = len(insights_rich) > 0 and isinstance(insights_rich[0], dict)
                    
                    self.log_result('missions_create', True, 
                                  f'Mission created successfully: {mission_id}, insights migration: {insights_migration_ok}, Phoenix timestamps: {phoenix_ok}', 
                                  created_mission, duration)
                else:
                    self.log_result('missions_create', False, 'Created mission missing ID', created_mission, duration)
            except Exception as e:
                self.log_result('missions_create', False, f'JSON parse error: {e}', None, duration)
        else:
            self.log_result('missions_create', False, 
                          f'POST /api/missions failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_mission_control(self):
        """Test Mission Control endpoints"""
        print("\n=== TESTING MISSION CONTROL ===")
        
        # Test GET /api/mission_control/threads
        success, response, duration = self.make_request('GET', '/mission_control/threads')
        if success and response.status_code == 200:
            try:
                threads_data = response.json()
                if isinstance(threads_data, list):
                    phoenix_ok = self.verify_phoenix_timestamps(threads_data)
                    self.log_result('mission_control_threads', True, 
                                  f'Mission Control threads working, {len(threads_data)} threads, Phoenix timestamps: {phoenix_ok}', 
                                  {'thread_count': len(threads_data), 'phoenix_timestamps': phoenix_ok}, duration)
                else:
                    self.log_result('mission_control_threads', False, 'Threads endpoint returned non-array', threads_data, duration)
                    return
            except Exception as e:
                self.log_result('mission_control_threads', False, f'JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('mission_control_threads', False, 
                          f'GET /api/mission_control/threads failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Test POST /api/mission_control/threads (create test thread)
        test_thread = {
            "title": "Comprehensive Backend Test Thread",
            "mission_id": self.test_data.get('mission_id')
        }
        
        success, response, duration = self.make_request('POST', '/mission_control/threads', test_thread)
        if success and response.status_code == 200:
            try:
                created_thread = response.json()
                thread_id = created_thread.get('thread_id')
                if thread_id:
                    self.test_data['thread_id'] = thread_id
                    self.log_result('mission_control_create_thread', True, 
                                  f'Thread created successfully: {thread_id}', 
                                  created_thread, duration)
                    
                    # Test sending a message to Praefectus
                    test_message = {
                        "thread_id": thread_id,
                        "text": "Hello Praefectus, this is a comprehensive backend test. Please confirm you can respond to messages in Mission Control."
                    }
                    
                    success, response, duration = self.make_request('POST', '/mission_control/message', test_message)
                    if success and response.status_code == 200:
                        try:
                            message_response = response.json()
                            assistant_text = message_response.get('assistant', {}).get('text', '')
                            if assistant_text:
                                self.log_result('mission_control_chat', True, 
                                              f'Praefectus responded: {len(assistant_text)} chars', 
                                              message_response, duration)
                            else:
                                self.log_result('mission_control_chat', False, 
                                              'Praefectus did not respond', 
                                              message_response, duration)
                        except Exception as e:
                            self.log_result('mission_control_chat', False, f'JSON parse error: {e}', None, duration)
                    else:
                        self.log_result('mission_control_chat', False, 
                                      f'Message sending failed: {response.status_code if hasattr(response, "status_code") else response}', 
                                      None, duration)
                else:
                    self.log_result('mission_control_create_thread', False, 'Created thread missing thread_id', created_thread, duration)
            except Exception as e:
                self.log_result('mission_control_create_thread', False, f'JSON parse error: {e}', None, duration)
        else:
            self.log_result('mission_control_create_thread', False, 
                          f'POST /api/mission_control/threads failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_events_endpoint(self):
        """Test Events endpoint"""
        print("\n=== TESTING EVENTS ===")
        
        # Test GET /api/events
        success, response, duration = self.make_request('GET', '/events')
        if success and response.status_code == 200:
            try:
                events_data = response.json()
                if isinstance(events_data, list):
                    phoenix_ok = self.verify_phoenix_timestamps(events_data)
                    self.log_result('events_list', True, 
                                  f'Events list working, {len(events_data)} events, Phoenix timestamps: {phoenix_ok}', 
                                  {'event_count': len(events_data), 'phoenix_timestamps': phoenix_ok}, duration)
                else:
                    self.log_result('events_list', False, 'Events endpoint returned non-array', events_data, duration)
            except Exception as e:
                self.log_result('events_list', False, f'JSON parse error: {e}', None, duration)
        else:
            self.log_result('events_list', False, 
                          f'GET /api/events failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_findings_endpoints(self):
        """Test Findings endpoints"""
        print("\n=== TESTING FINDINGS ===")
        
        # Test GET /api/findings
        success, response, duration = self.make_request('GET', '/findings')
        if success and response.status_code == 200:
            try:
                findings_data = response.json()
                if isinstance(findings_data, list):
                    phoenix_ok = self.verify_phoenix_timestamps(findings_data)
                    self.log_result('findings_list', True, 
                                  f'Findings list working, {len(findings_data)} findings, Phoenix timestamps: {phoenix_ok}', 
                                  {'finding_count': len(findings_data), 'phoenix_timestamps': phoenix_ok}, duration)
                else:
                    self.log_result('findings_list', False, 'Findings endpoint returned non-array', findings_data, duration)
            except Exception as e:
                self.log_result('findings_list', False, f'JSON parse error: {e}', None, duration)
        else:
            self.log_result('findings_list', False, 
                          f'GET /api/findings failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_forums_endpoints(self):
        """Test Forums endpoints"""
        print("\n=== TESTING FORUMS ===")
        
        # Test GET /api/forums
        success, response, duration = self.make_request('GET', '/forums')
        if success and response.status_code == 200:
            try:
                forums_data = response.json()
                if isinstance(forums_data, list):
                    phoenix_ok = self.verify_phoenix_timestamps(forums_data)
                    self.log_result('forums_list', True, 
                                  f'Forums list working, {len(forums_data)} forums, Phoenix timestamps: {phoenix_ok}', 
                                  {'forum_count': len(forums_data), 'phoenix_timestamps': phoenix_ok}, duration)
                else:
                    self.log_result('forums_list', False, 'Forums endpoint returned non-array', forums_data, duration)
            except Exception as e:
                self.log_result('forums_list', False, f'JSON parse error: {e}', None, duration)
        else:
            self.log_result('forums_list', False, 
                          f'GET /api/forums failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def run_comprehensive_test(self):
        """Run all comprehensive backend tests"""
        print(f"Starting Comprehensive Backend Testing - Base URL: {API_BASE}")
        print("=" * 100)
        
        start_time = time.time()
        
        # Run all test suites
        self.test_health_endpoints()
        self.test_agents_system()
        self.test_prospects_rolodex()
        self.test_hotleads()
        self.test_guardrails()
        self.test_missions()
        self.test_mission_control()
        self.test_events_endpoint()
        self.test_findings_endpoints()
        self.test_forums_endpoints()
        
        total_duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 100)
        print("COMPREHENSIVE TEST EXECUTION SUMMARY")
        print("=" * 100)
        
        passed = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - passed
        
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.results)*100):.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['message']}")
        
        # Phoenix timestamp verification summary
        phoenix_tests = [r for r in self.results if 'phoenix_timestamps' in str(r.get('response_data', {}))]
        phoenix_passed = sum(1 for r in phoenix_tests if r.get('response_data', {}).get('phoenix_timestamps', False))
        print(f"\nPHOENIX TIMESTAMPS: {phoenix_passed}/{len(phoenix_tests)} endpoints verified with Phoenix timezone (-07:00)")
        
        # Test data summary
        print(f"\nTEST DATA CREATED:")
        for key, value in self.test_data.items():
            if isinstance(value, str):
                print(f"- {key}: {value}")
            elif isinstance(value, list):
                print(f"- {key}: {len(value)} items")
        
        return self.results, passed, failed

if __name__ == "__main__":
    tester = ComprehensiveBackendTester()
    results, passed, failed = tester.run_comprehensive_test()