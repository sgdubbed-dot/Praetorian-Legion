#!/usr/bin/env python3
"""
Backend API Testing for Praetorian Legion - User-Reported Issues Investigation
Focus: Findings endpoints, Mission Control sanity checks, and Phoenix timestamps
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
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://3afd5048-b1fe-4fd7-b71e-338e9cf21c47.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class UserIssuesTester:
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.payloads = {}  # Store all payloads for reporting
        self.created_resources = {}  # Track created resources for cleanup
        
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

    def test_findings_endpoints(self):
        """Test findings endpoints as per user report - create mission, thread, link, snapshot, and verify"""
        print("\n=== FINDINGS ENDPOINTS INVESTIGATION ===")
        
        # Step 1: GET /api/findings (should return 200 with array)
        print("\n--- Step 1: GET /api/findings (initial check) ---")
        success, response, duration = self.make_request('GET', '/findings')
        if success:
            try:
                if response.status_code == 200:
                    data = response.json()
                    self.payloads['findings_initial'] = data
                    if isinstance(data, list):
                        self.log_result('findings_initial_check', True, 
                                      f'✅ GET /api/findings returned 200 with array ({len(data)} items)', 
                                      {'count': len(data), 'sample': data[:2] if data else []}, duration)
                    else:
                        self.log_result('findings_initial_check', False, 
                                      f'❌ GET /api/findings returned non-array: {type(data)}', 
                                      data, duration)
                elif response.status_code == 404:
                    self.log_result('findings_initial_check', False, 
                                  '❌ GET /api/findings returned 404 - endpoint not implemented', 
                                  {'status_code': 404, 'text': response.text}, duration)
                else:
                    self.log_result('findings_initial_check', False, 
                                  f'❌ GET /api/findings returned {response.status_code}', 
                                  {'status_code': response.status_code, 'text': response.text}, duration)
            except Exception as e:
                self.log_result('findings_initial_check', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('findings_initial_check', False, f'❌ Request failed: {response}', None, duration)
        
        # If findings endpoint doesn't exist, create test data and try the full flow
        print("\n--- Creating test mission for findings flow ---")
        
        # Step 2: Create a test mission
        mission_data = {
            "title": "Mission control sanity check",
            "objective": "Test findings endpoints and mission control integration",
            "posture": "help_only",
            "state": "scanning"
        }
        success, response, duration = self.make_request('POST', '/missions', mission_data)
        if success and response.status_code == 200:
            try:
                mission = response.json()
                mission_id = mission.get('id')
                self.created_resources['mission_id'] = mission_id
                self.payloads['test_mission'] = mission
                self.log_result('create_test_mission', True, 
                              f'✅ Test mission created: {mission_id}', 
                              {'mission_id': mission_id, 'title': mission.get('title')}, duration)
            except Exception as e:
                self.log_result('create_test_mission', False, f'❌ JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('create_test_mission', False, 
                          f'❌ Mission creation failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Step 3: Create a thread
        thread_data = {"title": "Findings Test Thread"}
        success, response, duration = self.make_request('POST', '/mission_control/threads', thread_data)
        if success and response.status_code == 200:
            try:
                thread_resp = response.json()
                thread_id = thread_resp.get('thread_id')
                self.created_resources['thread_id'] = thread_id
                self.payloads['test_thread'] = thread_resp
                self.log_result('create_test_thread', True, 
                              f'✅ Test thread created: {thread_id}', 
                              {'thread_id': thread_id}, duration)
            except Exception as e:
                self.log_result('create_test_thread', False, f'❌ JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('create_test_thread', False, 
                          f'❌ Thread creation failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Step 4: Link thread to mission (PATCH /api/mission_control/threads/{id})
        link_data = {"mission_id": mission_id}
        success, response, duration = self.make_request('PATCH', f'/mission_control/threads/{thread_id}', link_data)
        if success and response.status_code == 200:
            try:
                linked_thread = response.json()
                self.payloads['linked_thread'] = linked_thread
                if linked_thread.get('mission_id') == mission_id:
                    self.log_result('link_thread_to_mission', True, 
                                  f'✅ Thread linked to mission successfully', 
                                  {'thread_id': thread_id, 'mission_id': mission_id}, duration)
                else:
                    self.log_result('link_thread_to_mission', False, 
                                  f'❌ Thread linking failed - mission_id mismatch', 
                                  linked_thread, duration)
            except Exception as e:
                self.log_result('link_thread_to_mission', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('link_thread_to_mission', False, 
                          f'❌ Thread linking failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
        
        # Step 5: POST /api/mission_control/snapshot_findings
        print("\n--- Step 5: POST /api/mission_control/snapshot_findings ---")
        success, response, duration = self.make_request('POST', '/mission_control/snapshot_findings')
        if success:
            if response.status_code == 200:
                try:
                    snapshot_data = response.json()
                    self.payloads['snapshot_findings'] = snapshot_data
                    self.log_result('snapshot_findings', True, 
                                  '✅ Snapshot findings endpoint working', 
                                  snapshot_data, duration)
                except Exception as e:
                    self.log_result('snapshot_findings', False, f'❌ JSON parse error: {e}', None, duration)
            elif response.status_code == 404:
                self.log_result('snapshot_findings', False, 
                              '❌ POST /api/mission_control/snapshot_findings returned 404 - endpoint not implemented', 
                              {'status_code': 404, 'text': response.text}, duration)
            else:
                self.log_result('snapshot_findings', False, 
                              f'❌ POST /api/mission_control/snapshot_findings returned {response.status_code}', 
                              {'status_code': response.status_code, 'text': response.text}, duration)
        else:
            self.log_result('snapshot_findings', False, f'❌ Request failed: {response}', None, duration)
        
        # Step 6: GET /api/findings?mission_id=...
        print(f"\n--- Step 6: GET /api/findings?mission_id={mission_id} ---")
        success, response, duration = self.make_request('GET', '/findings', params={'mission_id': mission_id})
        if success:
            if response.status_code == 200:
                try:
                    findings_data = response.json()
                    self.payloads['findings_by_mission'] = findings_data
                    if isinstance(findings_data, list):
                        self.log_result('findings_by_mission', True, 
                                      f'✅ GET /api/findings?mission_id returned {len(findings_data)} findings', 
                                      {'count': len(findings_data), 'sample': findings_data[:2] if findings_data else []}, duration)
                        
                        # If we have findings, test individual finding and export
                        if findings_data:
                            finding_id = findings_data[0].get('id')
                            if finding_id:
                                self.test_individual_finding(finding_id)
                    else:
                        self.log_result('findings_by_mission', False, 
                                      f'❌ GET /api/findings?mission_id returned non-array: {type(findings_data)}', 
                                      findings_data, duration)
                except Exception as e:
                    self.log_result('findings_by_mission', False, f'❌ JSON parse error: {e}', None, duration)
            elif response.status_code == 404:
                self.log_result('findings_by_mission', False, 
                              '❌ GET /api/findings?mission_id returned 404 - endpoint not implemented', 
                              {'status_code': 404, 'text': response.text}, duration)
            else:
                self.log_result('findings_by_mission', False, 
                              f'❌ GET /api/findings?mission_id returned {response.status_code}', 
                              {'status_code': response.status_code, 'text': response.text}, duration)
        else:
            self.log_result('findings_by_mission', False, f'❌ Request failed: {response}', None, duration)

    def test_individual_finding(self, finding_id: str):
        """Test individual finding endpoints"""
        print(f"\n--- Testing individual finding: {finding_id} ---")
        
        # GET /api/findings/{id}
        success, response, duration = self.make_request('GET', f'/findings/{finding_id}')
        if success and response.status_code == 200:
            try:
                finding_data = response.json()
                self.payloads['individual_finding'] = finding_data
                self.log_result('get_individual_finding', True, 
                              f'✅ GET /api/findings/{finding_id} returned finding data', 
                              {'finding_id': finding_id, 'keys': list(finding_data.keys()) if isinstance(finding_data, dict) else None}, duration)
            except Exception as e:
                self.log_result('get_individual_finding', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('get_individual_finding', False, 
                          f'❌ GET /api/findings/{finding_id} failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
        
        # POST /api/findings/{id}/export?format=md
        success, response, duration = self.make_request('POST', f'/findings/{finding_id}/export', params={'format': 'md'})
        if success and response.status_code == 200:
            try:
                export_data = response.text if hasattr(response, 'text') else str(response)
                self.payloads['finding_export'] = export_data[:500]  # Truncate for storage
                self.log_result('export_finding_md', True, 
                              f'✅ POST /api/findings/{finding_id}/export?format=md returned export data ({len(export_data)} chars)', 
                              {'export_length': len(export_data), 'preview': export_data[:200]}, duration)
            except Exception as e:
                self.log_result('export_finding_md', False, f'❌ Export processing error: {e}', None, duration)
        else:
            self.log_result('export_finding_md', False, 
                          f'❌ POST /api/findings/{finding_id}/export?format=md failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_missions_list(self):
        """Test missions list and look for 'Mission control sanity check' mission"""
        print("\n=== MISSIONS LIST INVESTIGATION ===")
        
        success, response, duration = self.make_request('GET', '/missions')
        if success and response.status_code == 200:
            try:
                missions = response.json()
                self.payloads['missions_list'] = missions
                
                if isinstance(missions, list):
                    # Look for mission titled like "Mission control sanity check"
                    sanity_missions = [m for m in missions if 'sanity' in m.get('title', '').lower() or 'mission control' in m.get('title', '').lower()]
                    
                    self.log_result('missions_list_check', True, 
                                  f'✅ GET /api/missions returned {len(missions)} missions, {len(sanity_missions)} sanity/mission control missions found', 
                                  {'total_missions': len(missions), 'sanity_missions': len(sanity_missions), 'sanity_titles': [m.get('title') for m in sanity_missions]}, duration)
                    
                    # Check for Phoenix timestamps in missions
                    phoenix_count = sum(1 for m in missions if '-07:00' in str(m.get('created_at', '')) or '-07:00' in str(m.get('updated_at', '')))
                    self.log_result('missions_phoenix_timestamps', True, 
                                  f'✅ {phoenix_count}/{len(missions)} missions have Phoenix timestamps', 
                                  {'phoenix_count': phoenix_count, 'total': len(missions)}, 0)
                else:
                    self.log_result('missions_list_check', False, 
                                  f'❌ GET /api/missions returned non-array: {type(missions)}', 
                                  missions, duration)
            except Exception as e:
                self.log_result('missions_list_check', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('missions_list_check', False, 
                          f'❌ GET /api/missions failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_mission_control_threads(self):
        """Test Mission Control threads and verify sanity thread exists"""
        print("\n=== MISSION CONTROL THREADS INVESTIGATION ===")
        
        # GET /api/mission_control/threads
        success, response, duration = self.make_request('GET', '/mission_control/threads')
        if success and response.status_code == 200:
            try:
                threads = response.json()
                self.payloads['threads_list'] = threads
                
                if isinstance(threads, list):
                    # Look for threads with sanity or mission control in title
                    sanity_threads = [t for t in threads if 'sanity' in t.get('title', '').lower() or 'mission control' in t.get('title', '').lower()]
                    
                    self.log_result('threads_list_check', True, 
                                  f'✅ GET /api/mission_control/threads returned {len(threads)} threads, {len(sanity_threads)} sanity/mission control threads found', 
                                  {'total_threads': len(threads), 'sanity_threads': len(sanity_threads), 'sanity_titles': [t.get('title') for t in sanity_threads]}, duration)
                    
                    # Get the latest thread and check its messages
                    if threads:
                        latest_thread = max(threads, key=lambda t: t.get('updated_at', ''))
                        thread_id = latest_thread.get('thread_id')
                        self.test_thread_messages(thread_id, latest_thread.get('title', 'Unknown'))
                    
                    # Check for Phoenix timestamps in threads
                    phoenix_count = sum(1 for t in threads if '-07:00' in str(t.get('created_at', '')) or '-07:00' in str(t.get('updated_at', '')))
                    self.log_result('threads_phoenix_timestamps', True, 
                                  f'✅ {phoenix_count}/{len(threads)} threads have Phoenix timestamps', 
                                  {'phoenix_count': phoenix_count, 'total': len(threads)}, 0)
                else:
                    self.log_result('threads_list_check', False, 
                                  f'❌ GET /api/mission_control/threads returned non-array: {type(threads)}', 
                                  threads, duration)
            except Exception as e:
                self.log_result('threads_list_check', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('threads_list_check', False, 
                          f'❌ GET /api/mission_control/threads failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_thread_messages(self, thread_id: str, thread_title: str):
        """Test thread messages for timestamps and message roles"""
        print(f"\n--- Testing messages for thread: {thread_title} ({thread_id}) ---")
        
        success, response, duration = self.make_request('GET', f'/mission_control/thread/{thread_id}')
        if success and response.status_code == 200:
            try:
                thread_data = response.json()
                messages = thread_data.get('messages', [])
                thread_info = thread_data.get('thread', {})
                
                self.payloads[f'thread_messages_{thread_id}'] = thread_data
                
                if messages:
                    # Check message roles and timestamps
                    roles = [msg.get('role') for msg in messages]
                    timestamps = [msg.get('created_at', '') for msg in messages]
                    phoenix_timestamps = [ts for ts in timestamps if '-07:00' in ts]
                    
                    self.log_result('thread_messages_check', True, 
                                  f'✅ Thread {thread_title} has {len(messages)} messages with roles: {set(roles)}, {len(phoenix_timestamps)} Phoenix timestamps', 
                                  {'message_count': len(messages), 'roles': roles, 'phoenix_count': len(phoenix_timestamps), 'sample_timestamps': timestamps[:3]}, duration)
                else:
                    self.log_result('thread_messages_check', True, 
                                  f'✅ Thread {thread_title} exists but has no messages', 
                                  {'message_count': 0, 'thread_info': thread_info}, duration)
            except Exception as e:
                self.log_result('thread_messages_check', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('thread_messages_check', False, 
                          f'❌ GET /api/mission_control/thread/{thread_id} failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def run_investigation(self):
        """Run the user-reported issues investigation"""
        print(f"Starting User-Reported Issues Investigation - Base URL: {API_BASE}")
        print("=" * 100)
        
        start_time = time.time()
        
        # Test findings endpoints
        self.test_findings_endpoints()
        
        # Test missions list
        self.test_missions_list()
        
        # Test mission control threads
        self.test_mission_control_threads()
        
        total_duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 100)
        print("USER-REPORTED ISSUES INVESTIGATION SUMMARY")
        print("=" * 100)
        
        passed = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - passed
        
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total Duration: {total_duration:.2f}s")
        
        # Categorize results
        findings_tests = [r for r in self.results if 'finding' in r['test']]
        missions_tests = [r for r in self.results if 'mission' in r['test']]
        threads_tests = [r for r in self.results if 'thread' in r['test']]
        
        print(f"\nFINDINGS TESTS: {sum(1 for r in findings_tests if r['success'])}/{len(findings_tests)} passed")
        print(f"MISSIONS TESTS: {sum(1 for r in missions_tests if r['success'])}/{len(missions_tests)} passed")
        print(f"THREADS TESTS: {sum(1 for r in threads_tests if r['success'])}/{len(threads_tests)} passed")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['message']}")
        
        print("\nCREATED RESOURCES:")
        for resource_type, resource_id in self.created_resources.items():
            print(f"  {resource_type}: {resource_id}")
        
        print("\nPAYLOADS CAPTURED:")
        for step, payload in self.payloads.items():
            print(f"  {step}: {type(payload).__name__} ({len(str(payload))} chars)")
        
        return self.results, self.payloads

if __name__ == "__main__":
    tester = UserIssuesTester()
    results, payloads = tester.run_investigation()