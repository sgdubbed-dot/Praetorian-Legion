#!/usr/bin/env python3
"""
Backend API Testing for Praetorian Legion - Mission Control Thread Linking & Findings Snapshot
Focus: Execute specific 6-step flow to link latest thread to mission and create findings snapshot
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

class MissionControlTester:
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.payloads = {}  # Store all payloads for reporting
        self.report_data = {}  # Store specific data for final report
        
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

    def execute_mission_control_flow(self):
        """Execute the specific 6-step flow as per review request"""
        print("\n=== MISSION CONTROL THREAD LINKING & FINDINGS SNAPSHOT FLOW ===")
        
        # Step 1: GET /api/mission_control/threads - find latest by updated_at
        print("\n--- Step 1: GET /api/mission_control/threads (find latest by updated_at) ---")
        success, response, duration = self.make_request('GET', '/mission_control/threads')
        if not success or response.status_code != 200:
            self.log_result('step1_get_threads', False, 
                          f'❌ GET /api/mission_control/threads failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return False
        
        try:
            threads_data = response.json()
            self.payloads['step1_threads'] = threads_data
            if not isinstance(threads_data, list) or len(threads_data) == 0:
                self.log_result('step1_get_threads', False, 
                              f'❌ No threads found or invalid response format', 
                              threads_data, duration)
                return False
            
            # Find the most recent thread by updated_at (Phoenix time)
            latest_thread = max(threads_data, key=lambda t: t.get('updated_at', ''))
            thread_id = latest_thread.get('thread_id')
            thread_title = latest_thread.get('title', 'Unknown')
            
            self.report_data['thread_id'] = thread_id
            self.report_data['thread_title'] = thread_title
            
            phoenix_present = self.verify_phoenix_timestamps(threads_data, "threads")
            self.log_result('step1_get_threads', True, 
                          f'✅ Found {len(threads_data)} threads, latest: {thread_id} ("{thread_title}"), Phoenix timestamps: {phoenix_present}', 
                          {'thread_count': len(threads_data), 'latest_thread_id': thread_id, 'latest_title': thread_title, 'phoenix_timestamps': phoenix_present}, duration)
            
        except Exception as e:
            self.log_result('step1_get_threads', False, f'❌ JSON parse error: {e}', None, duration)
            return False
        
        # Step 2: GET /api/missions - find mission with title containing "Mission control sanity check"
        print("\n--- Step 2: GET /api/missions (find 'Mission control sanity check') ---")
        success, response, duration = self.make_request('GET', '/missions')
        if not success or response.status_code != 200:
            self.log_result('step2_get_missions', False, 
                          f'❌ GET /api/missions failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return False
        
        try:
            missions_data = response.json()
            self.payloads['step2_missions'] = missions_data
            if not isinstance(missions_data, list):
                self.log_result('step2_get_missions', False, 
                              f'❌ Invalid missions response format', 
                              missions_data, duration)
                return False
            
            # Find mission with title containing "Mission control sanity check"
            target_missions = [m for m in missions_data if 'mission control sanity check' in m.get('title', '').lower()]
            if not target_missions:
                self.log_result('step2_get_missions', False, 
                              f'❌ No mission found with title containing "Mission control sanity check"', 
                              {'total_missions': len(missions_data)}, duration)
                return False
            
            # If multiple, pick the most recently updated
            target_mission = max(target_missions, key=lambda m: m.get('updated_at', ''))
            mission_id = target_mission.get('id')
            mission_title = target_mission.get('title', 'Unknown')
            
            self.report_data['mission_id'] = mission_id
            self.report_data['mission_title'] = mission_title
            
            phoenix_present = self.verify_phoenix_timestamps(missions_data, "missions")
            self.log_result('step2_get_missions', True, 
                          f'✅ Found {len(target_missions)} matching missions, selected: {mission_id} ("{mission_title}"), Phoenix timestamps: {phoenix_present}', 
                          {'total_missions': len(missions_data), 'matching_missions': len(target_missions), 'selected_mission_id': mission_id, 'selected_title': mission_title, 'phoenix_timestamps': phoenix_present}, duration)
            
        except Exception as e:
            self.log_result('step2_get_missions', False, f'❌ JSON parse error: {e}', None, duration)
            return False
        
        # Step 3: PATCH /api/mission_control/threads/{thread_id} - link thread to mission
        print(f"\n--- Step 3: PATCH /api/mission_control/threads/{thread_id} (link to mission) ---")
        link_data = {"mission_id": mission_id}
        success, response, duration = self.make_request('PATCH', f'/mission_control/threads/{thread_id}', link_data)
        if not success or response.status_code != 200:
            self.log_result('step3_link_thread', False, 
                          f'❌ PATCH /api/mission_control/threads/{thread_id} failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return False
        
        try:
            linked_thread = response.json()
            self.payloads['step3_linked_thread'] = linked_thread
            
            # Verify response shows mission_id set
            if linked_thread.get('mission_id') != mission_id:
                self.log_result('step3_link_thread', False, 
                              f'❌ Thread linking failed - mission_id not set correctly (expected: {mission_id}, got: {linked_thread.get("mission_id")})', 
                              linked_thread, duration)
                return False
            
            phoenix_present = self.verify_phoenix_timestamps(linked_thread, "linked thread")
            self.log_result('step3_link_thread', True, 
                          f'✅ Thread {thread_id} successfully linked to mission {mission_id}, Phoenix timestamps: {phoenix_present}', 
                          {'thread_id': thread_id, 'mission_id': mission_id, 'phoenix_timestamps': phoenix_present}, duration)
            
        except Exception as e:
            self.log_result('step3_link_thread', False, f'❌ JSON parse error: {e}', None, duration)
            return False
        
        # Step 4: POST /api/mission_control/snapshot_findings - create snapshot finding
        print(f"\n--- Step 4: POST /api/mission_control/snapshot_findings (create snapshot) ---")
        snapshot_data = {"thread_id": thread_id}
        success, response, duration = self.make_request('POST', '/mission_control/snapshot_findings', snapshot_data)
        if not success or response.status_code != 200:
            self.log_result('step4_snapshot_findings', False, 
                          f'❌ POST /api/mission_control/snapshot_findings failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return False
        
        try:
            finding_created = response.json()
            self.payloads['step4_snapshot'] = finding_created
            
            finding_id = finding_created.get('id')
            finding_title = finding_created.get('title', 'Unknown')
            
            self.report_data['finding_id'] = finding_id
            self.report_data['finding_title'] = finding_title
            
            phoenix_present = self.verify_phoenix_timestamps(finding_created, "snapshot finding")
            self.log_result('step4_snapshot_findings', True, 
                          f'✅ Findings snapshot created: {finding_id} ("{finding_title}"), Phoenix timestamps: {phoenix_present}', 
                          {'finding_id': finding_id, 'finding_title': finding_title, 'phoenix_timestamps': phoenix_present}, duration)
            
        except Exception as e:
            self.log_result('step4_snapshot_findings', False, f'❌ JSON parse error: {e}', None, duration)
            return False
        
        # Step 5: GET /api/findings?mission_id={mission_id} - verify listing shows the new finding
        print(f"\n--- Step 5: GET /api/findings?mission_id={mission_id} (verify new finding) ---")
        success, response, duration = self.make_request('GET', '/findings', params={'mission_id': mission_id})
        if not success or response.status_code != 200:
            self.log_result('step5_verify_findings', False, 
                          f'❌ GET /api/findings?mission_id={mission_id} failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return False
        
        try:
            mission_findings = response.json()
            self.payloads['step5_mission_findings'] = mission_findings
            
            if not isinstance(mission_findings, list):
                self.log_result('step5_verify_findings', False, 
                              f'❌ Invalid findings response format', 
                              mission_findings, duration)
                return False
            
            # Check if our new finding is in the list
            new_finding_found = any(f.get('id') == finding_id for f in mission_findings)
            if not new_finding_found:
                self.log_result('step5_verify_findings', False, 
                              f'❌ New finding {finding_id} not found in mission findings list', 
                              {'findings_count': len(mission_findings), 'finding_ids': [f.get('id') for f in mission_findings]}, duration)
                return False
            
            # Find the new finding's title in the list
            new_finding_in_list = next((f for f in mission_findings if f.get('id') == finding_id), {})
            list_finding_title = new_finding_in_list.get('title', 'Unknown')
            
            self.report_data['list_count'] = len(mission_findings)
            self.report_data['list_finding_title'] = list_finding_title
            
            phoenix_present = self.verify_phoenix_timestamps(mission_findings, "mission findings")
            self.log_result('step5_verify_findings', True, 
                          f'✅ Mission findings list contains {len(mission_findings)} findings including new finding {finding_id}, Phoenix timestamps: {phoenix_present}', 
                          {'findings_count': len(mission_findings), 'new_finding_found': True, 'phoenix_timestamps': phoenix_present}, duration)
            
        except Exception as e:
            self.log_result('step5_verify_findings', False, f'❌ JSON parse error: {e}', None, duration)
            return False
        
        return True

    def generate_concise_report(self):
        """Generate the concise report as requested"""
        print("\n" + "=" * 80)
        print("CONCISE REPORT - MISSION CONTROL THREAD LINKING & FINDINGS SNAPSHOT")
        print("=" * 80)
        
        # Check if we have all required data
        required_fields = ['thread_id', 'thread_title', 'mission_id', 'mission_title', 'finding_id', 'finding_title']
        missing_fields = [f for f in required_fields if f not in self.report_data]
        
        if missing_fields:
            print(f"❌ INCOMPLETE: Missing data for {missing_fields}")
            return
        
        print(f"Thread ID: {self.report_data['thread_id']}")
        print(f"Thread Title: {self.report_data['thread_title']}")
        print(f"Mission ID: {self.report_data['mission_id']}")
        print(f"Mission Title: {self.report_data['mission_title']}")
        print(f"Finding ID: {self.report_data['finding_id']}")
        print(f"Finding Title: {self.report_data['finding_title']}")
        print(f"List Count: {self.report_data.get('list_count', 'N/A')}")
        print(f"List Finding Title: {self.report_data.get('list_finding_title', 'N/A')}")
        
        # Phoenix timestamp confirmation
        phoenix_confirmed = False
        for payload in self.payloads.values():
            if self.verify_phoenix_timestamps(payload):
                phoenix_confirmed = True
                break
        
        print(f"Phoenix Timestamp Presence: {'✅ CONFIRMED' if phoenix_confirmed else '❌ NOT FOUND'}")
        
        print("\n" + "=" * 80)

    def run_mission_control_test(self):
        """Run the complete mission control test as per review request"""
        print(f"Starting Mission Control Thread Linking & Findings Snapshot Test - Base URL: {API_BASE}")
        print("=" * 100)
        
        start_time = time.time()
        
        # Execute the 6-step flow
        flow_success = self.execute_mission_control_flow()
        
        total_duration = time.time() - start_time
        
        # Generate concise report
        if flow_success:
            self.generate_concise_report()
        
        # Summary
        print("\n" + "=" * 100)
        print("TEST EXECUTION SUMMARY")
        print("=" * 100)
        
        passed = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - passed
        
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Flow Success: {'✅ YES' if flow_success else '❌ NO'}")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['message']}")
        
        # Phoenix timestamp verification summary
        phoenix_tests = [r for r in self.results if 'phoenix_timestamps' in str(r.get('response_data', {}))]
        phoenix_passed = sum(1 for r in phoenix_tests if r.get('response_data', {}).get('phoenix_timestamps', False))
        print(f"\nPHOENIX TIMESTAMPS: {phoenix_passed}/{len(phoenix_tests)} endpoints verified with Phoenix timezone (-07:00)")
        
        return self.results, self.payloads, flow_success

if __name__ == "__main__":
    tester = MissionControlTester()
    results, payloads, success = tester.run_mission_control_test()