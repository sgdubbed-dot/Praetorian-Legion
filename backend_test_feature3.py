#!/usr/bin/env python3
"""
Backend API Testing for Praetorian Legion - Feature 3 Regression Tests
Focus: Quick regression on backend after Feature 3 partial backend changes
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
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://progress-pulse-21.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class Feature3RegressionTester:
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.payloads = {}  # Store all payloads for reporting
        
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

    def test_health_endpoint(self):
        """Test 1: Sanity check - GET /api/health"""
        print("\n=== Test 1: Health Endpoint Sanity Check ===")
        
        success, response, duration = self.make_request('GET', '/health')
        if success:
            try:
                data = response.json()
                self.payloads['health_check'] = data
                
                ok = data.get('ok')
                timestamp = data.get('timestamp')
                phoenix_ok = timestamp and '-07:00' in timestamp
                
                if ok and phoenix_ok:
                    self.log_result('health_endpoint', True, 
                                  f'✅ Health endpoint working: ok={ok}, Phoenix timestamp present', 
                                  data, duration)
                else:
                    self.log_result('health_endpoint', False, 
                                  f'❌ Health check failed - ok: {ok}, phoenix: {phoenix_ok}', 
                                  data, duration)
            except Exception as e:
                self.log_result('health_endpoint', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('health_endpoint', False, f'❌ Request failed: {response}', None, duration)

    def test_product_brief_guardrail(self):
        """Test 2: Create product_brief guardrail"""
        print("\n=== Test 2: Create Product Brief Guardrail ===")
        
        # Sample product brief payload
        guardrail_data = {
            "type": "product_brief",
            "scope": "global",
            "value": {
                "title": "Agent Observability Platform",
                "one_liner": "Real-time monitoring and analytics for AI agent systems",
                "category": "DevOps/Observability",
                "value_props": [
                    "Complete visibility into agent behavior",
                    "Performance optimization insights",
                    "Automated anomaly detection"
                ],
                "key_features": [
                    "Real-time dashboards",
                    "Custom alerting",
                    "Integration APIs"
                ],
                "differentiators": [
                    "AI-native monitoring",
                    "Zero-config setup",
                    "Multi-agent orchestration support"
                ],
                "forbidden_tone": [
                    "Overly technical jargon",
                    "Aggressive sales language"
                ]
            }
        }
        
        success, response, duration = self.make_request('POST', '/guardrails', guardrail_data)
        if success:
            try:
                data = response.json()
                self.payloads['product_brief_guardrail'] = data
                
                guardrail_id = data.get('id')
                created_at = data.get('created_at')
                guardrail_type = data.get('type')
                scope = data.get('scope')
                value = data.get('value')
                
                phoenix_ok = created_at and '-07:00' in created_at
                type_ok = guardrail_type == 'product_brief'
                scope_ok = scope == 'global'
                value_ok = isinstance(value, dict) and value.get('title')
                
                if guardrail_id and phoenix_ok and type_ok and scope_ok and value_ok:
                    self.log_result('product_brief_guardrail', True, 
                                  f'✅ Product brief guardrail created: id={guardrail_id}, type={guardrail_type}, scope={scope}', 
                                  {'id': guardrail_id, 'type': guardrail_type, 'scope': scope, 'phoenix_timestamp': phoenix_ok}, duration)
                else:
                    self.log_result('product_brief_guardrail', False, 
                                  f'❌ Guardrail creation failed - id: {bool(guardrail_id)}, type: {type_ok}, scope: {scope_ok}, value: {value_ok}, phoenix: {phoenix_ok}', 
                                  data, duration)
            except Exception as e:
                self.log_result('product_brief_guardrail', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('product_brief_guardrail', False, f'❌ Request failed: {response}', None, duration)

    def test_mission_control_basic_flow(self):
        """Test 3: Mission Control basic flow still works"""
        print("\n=== Test 3: Mission Control Basic Flow ===")
        
        # Step 3a: Create thread
        print("\n--- Step 3a: POST /api/mission_control/threads ---")
        thread_data = {"title": "Feature 3 Test Thread"}
        success, response, duration = self.make_request('POST', '/mission_control/threads', thread_data)
        if not success:
            self.log_result('mission_control_create_thread', False, f'❌ Thread creation failed: {response}', None, duration)
            return
        
        try:
            data = response.json()
            thread_id = data.get('thread_id')
            if not thread_id:
                self.log_result('mission_control_create_thread', False, '❌ No thread_id returned', data, duration)
                return
            
            self.log_result('mission_control_create_thread', True, 
                          f'✅ Thread created: {thread_id}', data, duration)
            self.payloads['mc_create_thread'] = data
        except Exception as e:
            self.log_result('mission_control_create_thread', False, f'❌ JSON parse error: {e}', None, duration)
            return
        
        # Step 3b: Send message
        print("\n--- Step 3b: POST /api/mission_control/message ---")
        message_data = {
            "thread_id": thread_id,
            "text": "Test message for Feature 3 regression - please provide a brief response about agent observability."
        }
        success, response, duration = self.make_request('POST', '/mission_control/message', message_data)
        if not success:
            self.log_result('mission_control_send_message', False, f'❌ Message send failed: {response}', None, duration)
            return
        
        try:
            data = response.json()
            assistant = data.get('assistant', {})
            assistant_text = assistant.get('text', '')
            created_at = assistant.get('created_at', '')
            reframed = assistant.get('reframed', None)
            
            phoenix_ok = '-07:00' in created_at
            
            if assistant_text and created_at:
                self.log_result('mission_control_send_message', True, 
                              f'✅ Message sent, assistant responded ({len(assistant_text)} chars), reframed={reframed}, Phoenix timestamp: {phoenix_ok}', 
                              {'text_length': len(assistant_text), 'reframed': reframed, 'phoenix_timestamp': phoenix_ok}, duration)
                self.payloads['mc_send_message'] = data
            else:
                self.log_result('mission_control_send_message', False, 
                              f'❌ Incomplete response - text: {bool(assistant_text)}, timestamp: {bool(created_at)}', 
                              data, duration)
                return
        except Exception as e:
            self.log_result('mission_control_send_message', False, f'❌ JSON parse error: {e}', None, duration)
            return
        
        # Step 3c: Get thread
        print("\n--- Step 3c: GET /api/mission_control/thread/{thread_id}?limit=50 ---")
        success, response, duration = self.make_request('GET', f'/mission_control/thread/{thread_id}?limit=50')
        if success:
            try:
                data = response.json()
                messages = data.get('messages', [])
                thread_info = data.get('thread', {})
                
                if len(messages) >= 2:
                    roles = [msg.get('role') for msg in messages]
                    has_human = 'human' in roles
                    has_praefectus = 'praefectus' in roles
                    
                    # Check Phoenix timestamps
                    phoenix_count = sum(1 for msg in messages if '-07:00' in msg.get('created_at', ''))
                    
                    if has_human and has_praefectus and phoenix_count >= 2:
                        self.log_result('mission_control_get_thread', True, 
                                      f'✅ Thread retrieved: {len(messages)} messages (human + praefectus), {phoenix_count} Phoenix timestamps', 
                                      {'message_count': len(messages), 'roles': roles, 'phoenix_count': phoenix_count}, duration)
                        self.payloads['mc_get_thread'] = data
                    else:
                        self.log_result('mission_control_get_thread', False, 
                                      f'❌ Thread validation failed - human: {has_human}, praefectus: {has_praefectus}, phoenix: {phoenix_count}', 
                                      {'messages': messages}, duration)
                else:
                    self.log_result('mission_control_get_thread', False, 
                                  f'❌ Insufficient messages: {len(messages)}', 
                                  data, duration)
            except Exception as e:
                self.log_result('mission_control_get_thread', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('mission_control_get_thread', False, f'❌ Request failed: {response}', None, duration)

    def test_context_preamble_event(self):
        """Test 4: Verify context_preamble_used event logged"""
        print("\n=== Test 4: Context Preamble Event Verification ===")
        
        success, response, duration = self.make_request('GET', '/events?source=backend/mission_control&limit=5')
        if success:
            try:
                events = response.json()
                self.payloads['context_preamble_events'] = events
                
                # Look for context_preamble_used event
                preamble_events = [e for e in events if e.get('event_name') == 'context_preamble_used']
                phoenix_timestamps = sum(1 for event in events if '-07:00' in event.get('timestamp', ''))
                
                if len(preamble_events) > 0:
                    latest_event = preamble_events[0]
                    thread_id = latest_event.get('payload', {}).get('thread_id')
                    model_id = latest_event.get('payload', {}).get('model_id')
                    
                    self.log_result('context_preamble_event', True, 
                                  f'✅ context_preamble_used event found: thread_id={thread_id}, model_id={model_id}, {phoenix_timestamps} Phoenix timestamps', 
                                  {'preamble_events': len(preamble_events), 'latest_event': latest_event, 'phoenix_count': phoenix_timestamps}, duration)
                else:
                    self.log_result('context_preamble_event', False, 
                                  f'❌ No context_preamble_used events found in recent events', 
                                  {'all_events': [e.get('event_name') for e in events]}, duration)
            except Exception as e:
                self.log_result('context_preamble_event', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('context_preamble_event', False, f'❌ Request failed: {response}', None, duration)

    def test_assistant_reframed_metadata(self):
        """Test 5: Verify assistant response includes reframed=false in return body"""
        print("\n=== Test 5: Assistant Reframed Metadata Verification ===")
        
        # This test uses the message response from test 3
        if 'mc_send_message' in self.payloads:
            data = self.payloads['mc_send_message']
            assistant = data.get('assistant', {})
            reframed = assistant.get('reframed')
            
            if reframed is not None:
                self.log_result('assistant_reframed_metadata', True, 
                              f'✅ Assistant response includes reframed metadata: reframed={reframed}', 
                              {'reframed': reframed}, 0)
            else:
                self.log_result('assistant_reframed_metadata', False, 
                              f'❌ Assistant response missing reframed metadata', 
                              assistant, 0)
        else:
            self.log_result('assistant_reframed_metadata', False, 
                          '❌ No message response available from previous test', None, 0)

    def test_findings_endpoints_smoke(self):
        """Test 6: Findings endpoints smoke test"""
        print("\n=== Test 6: Findings Endpoints Smoke Test ===")
        
        # Note: Based on the server.py code, I don't see findings endpoints implemented
        # This test will check if the endpoints exist or return appropriate errors
        
        # First, create a mission for testing
        print("\n--- Step 6a: Create mission for findings test ---")
        mission_data = {
            "title": "Findings Test Mission",
            "objective": "Test findings endpoints",
            "posture": "help_only",
            "state": "scanning"
        }
        success, response, duration = self.make_request('POST', '/missions', mission_data)
        if not success:
            self.log_result('findings_create_mission', False, f'❌ Mission creation failed: {response}', None, duration)
            return
        
        try:
            mission = response.json()
            mission_id = mission.get('id')
            if not mission_id:
                self.log_result('findings_create_mission', False, '❌ No mission_id returned', mission, duration)
                return
            
            self.log_result('findings_create_mission', True, 
                          f'✅ Mission created for findings test: {mission_id}', mission, duration)
            self.payloads['findings_mission'] = mission
        except Exception as e:
            self.log_result('findings_create_mission', False, f'❌ JSON parse error: {e}', None, duration)
            return
        
        # Create a thread and link it to the mission
        print("\n--- Step 6b: Create and link thread to mission ---")
        thread_data = {"title": "Findings Test Thread"}
        success, response, duration = self.make_request('POST', '/mission_control/threads', thread_data)
        if not success:
            self.log_result('findings_create_thread', False, f'❌ Thread creation failed: {response}', None, duration)
            return
        
        try:
            data = response.json()
            thread_id = data.get('thread_id')
            if not thread_id:
                self.log_result('findings_create_thread', False, '❌ No thread_id returned', data, duration)
                return
            
            # Link thread to mission via PATCH
            patch_data = {"mission_id": mission_id}
            success, response, duration = self.make_request('PATCH', f'/mission_control/threads/{thread_id}', patch_data)
            if success:
                self.log_result('findings_link_thread', True, 
                              f'✅ Thread linked to mission: thread_id={thread_id}, mission_id={mission_id}', 
                              response.json(), duration)
            else:
                self.log_result('findings_link_thread', False, 
                              f'❌ Thread linking failed: {response}', None, duration)
                return
        except Exception as e:
            self.log_result('findings_link_thread', False, f'❌ JSON parse error: {e}', None, duration)
            return
        
        # Test findings endpoints (these may not be implemented yet)
        print("\n--- Step 6c: Test findings endpoints ---")
        
        # Test POST /api/mission_control/snapshot_findings
        snapshot_success, snapshot_response, snapshot_duration = self.make_request('POST', '/mission_control/snapshot_findings', {})
        if snapshot_success:
            self.log_result('findings_snapshot', True, 
                          '✅ Snapshot findings endpoint exists and responds', 
                          snapshot_response.json(), snapshot_duration)
        else:
            # Check if it's a 404 (not implemented) or other error
            if hasattr(snapshot_response, 'status_code') and snapshot_response.status_code == 404:
                self.log_result('findings_snapshot', False, 
                              '❌ Snapshot findings endpoint not implemented (404)', 
                              {'status_code': snapshot_response.status_code}, snapshot_duration)
            else:
                self.log_result('findings_snapshot', False, 
                              f'❌ Snapshot findings endpoint error: {snapshot_response}', 
                              None, snapshot_duration)
        
        # Test GET /api/findings?mission_id=...
        findings_success, findings_response, findings_duration = self.make_request('GET', f'/findings?mission_id={mission_id}')
        if findings_success:
            self.log_result('findings_get_by_mission', True, 
                          '✅ Get findings by mission endpoint exists and responds', 
                          findings_response.json(), findings_duration)
        else:
            if hasattr(findings_response, 'status_code') and findings_response.status_code == 404:
                self.log_result('findings_get_by_mission', False, 
                              '❌ Get findings endpoint not implemented (404)', 
                              {'status_code': findings_response.status_code}, findings_duration)
            else:
                self.log_result('findings_get_by_mission', False, 
                              f'❌ Get findings endpoint error: {findings_response}', 
                              None, findings_duration)

    def test_phoenix_timestamps(self):
        """Test 7: Confirm Phoenix timestamp strings present in created objects"""
        print("\n=== Test 7: Phoenix Timestamp Verification ===")
        
        # Check timestamps from previous tests
        phoenix_checks = []
        
        # Check health endpoint timestamp
        if 'health_check' in self.payloads:
            timestamp = self.payloads['health_check'].get('timestamp', '')
            phoenix_checks.append(('health_check', '-07:00' in timestamp, timestamp))
        
        # Check guardrail timestamp
        if 'product_brief_guardrail' in self.payloads:
            created_at = self.payloads['product_brief_guardrail'].get('created_at', '')
            phoenix_checks.append(('guardrail_created_at', '-07:00' in created_at, created_at))
        
        # Check mission control message timestamp
        if 'mc_send_message' in self.payloads:
            assistant = self.payloads['mc_send_message'].get('assistant', {})
            created_at = assistant.get('created_at', '')
            phoenix_checks.append(('message_created_at', '-07:00' in created_at, created_at))
        
        # Check mission timestamp
        if 'findings_mission' in self.payloads:
            created_at = self.payloads['findings_mission'].get('created_at', '')
            updated_at = self.payloads['findings_mission'].get('updated_at', '')
            phoenix_checks.append(('mission_created_at', '-07:00' in created_at, created_at))
            phoenix_checks.append(('mission_updated_at', '-07:00' in updated_at, updated_at))
        
        # Evaluate results
        total_checks = len(phoenix_checks)
        passed_checks = sum(1 for _, is_phoenix, _ in phoenix_checks if is_phoenix)
        
        if total_checks > 0:
            if passed_checks == total_checks:
                self.log_result('phoenix_timestamps', True, 
                              f'✅ All {total_checks} timestamps use Phoenix timezone (-07:00)', 
                              {'checks': phoenix_checks, 'passed': passed_checks, 'total': total_checks}, 0)
            else:
                failed_checks = [(name, timestamp) for name, is_phoenix, timestamp in phoenix_checks if not is_phoenix]
                self.log_result('phoenix_timestamps', False, 
                              f'❌ {total_checks - passed_checks}/{total_checks} timestamps missing Phoenix timezone', 
                              {'failed_checks': failed_checks, 'passed': passed_checks, 'total': total_checks}, 0)
        else:
            self.log_result('phoenix_timestamps', False, 
                          '❌ No timestamps available for verification', 
                          {'available_payloads': list(self.payloads.keys())}, 0)

    def run_feature3_regression_tests(self):
        """Run all Feature 3 regression tests"""
        print(f"Starting Feature 3 Regression Tests - Base URL: {API_BASE}")
        print("=" * 100)
        
        start_time = time.time()
        
        # Run all regression tests
        self.test_health_endpoint()
        self.test_product_brief_guardrail()
        self.test_mission_control_basic_flow()
        self.test_context_preamble_event()
        self.test_assistant_reframed_metadata()
        self.test_findings_endpoints_smoke()
        self.test_phoenix_timestamps()
        
        total_duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 100)
        print("FEATURE 3 REGRESSION TEST SUMMARY")
        print("=" * 100)
        
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
        
        print("\nPAYLOADS CAPTURED:")
        for step, payload in self.payloads.items():
            print(f"  {step}: {type(payload).__name__} ({len(str(payload))} chars)")
        
        return self.results, self.payloads

if __name__ == "__main__":
    tester = Feature3RegressionTester()
    results, payloads = tester.run_feature3_regression_tests()