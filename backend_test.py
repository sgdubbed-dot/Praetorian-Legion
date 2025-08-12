#!/usr/bin/env python3
"""
Backend API Testing for Praetorian Legion - Findings Endpoints Re-Testing
Focus: Re-test findings after backend addition per review request
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

class FindingsRetester:
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

    def test_findings_complete_flow(self):
        """Test complete findings flow as per review request"""
        print("\n=== FINDINGS ENDPOINTS RE-TESTING (COMPLETE FLOW) ===")
        
        # Step 1: GET /api/findings (should 200, array)
        print("\n--- Step 1: GET /api/findings (should 200, array) ---")
        success, response, duration = self.make_request('GET', '/findings')
        if success and response.status_code == 200:
            try:
                findings_data = response.json()
                self.payloads['step1_findings_initial'] = findings_data
                if isinstance(findings_data, list):
                    phoenix_present = self.verify_phoenix_timestamps(findings_data, "initial findings")
                    self.log_result('step1_get_findings', True, 
                                  f'✅ GET /api/findings returned 200 with array ({len(findings_data)} items), Phoenix timestamps: {phoenix_present}', 
                                  {'count': len(findings_data), 'phoenix_timestamps': phoenix_present}, duration)
                else:
                    self.log_result('step1_get_findings', False, 
                                  f'❌ GET /api/findings returned non-array: {type(findings_data)}', 
                                  findings_data, duration)
                    return
            except Exception as e:
                self.log_result('step1_get_findings', False, f'❌ JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('step1_get_findings', False, 
                          f'❌ GET /api/findings failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Step 2: Create mission directly: POST /api/missions
        print("\n--- Step 2: Create mission directly ---")
        mission_data = {
            "title": "Mission control sanity check",
            "objective": "Sanity objective",
            "posture": "help_only",
            "state": "scanning"
        }
        success, response, duration = self.make_request('POST', '/missions', mission_data)
        if success and response.status_code == 200:
            try:
                mission = response.json()
                mission_id = mission.get('id')
                self.created_resources['mission_id'] = mission_id
                self.payloads['step2_mission'] = mission
                phoenix_present = self.verify_phoenix_timestamps(mission, "mission")
                self.log_result('step2_create_mission', True, 
                              f'✅ Mission created: {mission_id}, Phoenix timestamps: {phoenix_present}', 
                              {'mission_id': mission_id, 'title': mission.get('title'), 'phoenix_timestamps': phoenix_present}, duration)
            except Exception as e:
                self.log_result('step2_create_mission', False, f'❌ JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('step2_create_mission', False, 
                          f'❌ Mission creation failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Step 3: Create a thread: POST /api/mission_control/threads
        print("\n--- Step 3: Create a thread ---")
        thread_data = {"title": "Sanity Thread"}
        success, response, duration = self.make_request('POST', '/mission_control/threads', thread_data)
        if success and response.status_code == 200:
            try:
                thread_resp = response.json()
                thread_id = thread_resp.get('thread_id')
                self.created_resources['thread_id'] = thread_id
                self.payloads['step3_thread'] = thread_resp
                self.log_result('step3_create_thread', True, 
                              f'✅ Thread created: {thread_id}', 
                              {'thread_id': thread_id}, duration)
            except Exception as e:
                self.log_result('step3_create_thread', False, f'❌ JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('step3_create_thread', False, 
                          f'❌ Thread creation failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Step 4: Link thread to mission: PATCH /api/mission_control/threads/{thread_id}
        print("\n--- Step 4: Link thread to mission ---")
        link_data = {"mission_id": mission_id}
        success, response, duration = self.make_request('PATCH', f'/mission_control/threads/{thread_id}', link_data)
        if success and response.status_code == 200:
            try:
                linked_thread = response.json()
                self.payloads['step4_linked_thread'] = linked_thread
                phoenix_present = self.verify_phoenix_timestamps(linked_thread, "linked thread")
                if linked_thread.get('mission_id') == mission_id:
                    self.log_result('step4_link_thread', True, 
                                  f'✅ Thread linked to mission successfully, Phoenix timestamps: {phoenix_present}', 
                                  {'thread_id': thread_id, 'mission_id': mission_id, 'phoenix_timestamps': phoenix_present}, duration)
                else:
                    self.log_result('step4_link_thread', False, 
                                  f'❌ Thread linking failed - mission_id mismatch', 
                                  linked_thread, duration)
                    return
            except Exception as e:
                self.log_result('step4_link_thread', False, f'❌ JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('step4_link_thread', False, 
                          f'❌ Thread linking failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Step 5: Send two messages to this thread: POST /api/mission_control/message
        print("\n--- Step 5: Send two messages to thread ---")
        messages = [
            {"thread_id": thread_id, "text": "First test message for findings snapshot"},
            {"thread_id": thread_id, "text": "Second test message to create conversation history"}
        ]
        
        for i, msg_data in enumerate(messages, 1):
            success, response, duration = self.make_request('POST', '/mission_control/message', msg_data)
            if success and response.status_code == 200:
                try:
                    msg_resp = response.json()
                    self.payloads[f'step5_message_{i}'] = msg_resp
                    phoenix_present = self.verify_phoenix_timestamps(msg_resp, f"message {i}")
                    self.log_result(f'step5_send_message_{i}', True, 
                                  f'✅ Message {i} sent successfully, Phoenix timestamps: {phoenix_present}', 
                                  {'message_num': i, 'phoenix_timestamps': phoenix_present}, duration)
                except Exception as e:
                    self.log_result(f'step5_send_message_{i}', False, f'❌ JSON parse error: {e}', None, duration)
            else:
                self.log_result(f'step5_send_message_{i}', False, 
                              f'❌ Message {i} sending failed: {response.status_code if hasattr(response, "status_code") else response}', 
                              None, duration)
        
        # Step 6: Snapshot findings: POST /api/mission_control/snapshot_findings
        print("\n--- Step 6: Snapshot findings ---")
        snapshot_data = {"thread_id": thread_id}
        success, response, duration = self.make_request('POST', '/mission_control/snapshot_findings', snapshot_data)
        if success and response.status_code == 200:
            try:
                finding_created = response.json()
                finding_id = finding_created.get('id')
                self.created_resources['finding_id'] = finding_id
                self.payloads['step6_snapshot'] = finding_created
                phoenix_present = self.verify_phoenix_timestamps(finding_created, "snapshot finding")
                self.log_result('step6_snapshot_findings', True, 
                              f'✅ Findings snapshot created: {finding_id}, Phoenix timestamps: {phoenix_present}', 
                              {'finding_id': finding_id, 'phoenix_timestamps': phoenix_present}, duration)
            except Exception as e:
                self.log_result('step6_snapshot_findings', False, f'❌ JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('step6_snapshot_findings', False, 
                          f'❌ Snapshot findings failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Step 7: GET /api/findings?mission_id=<mission_id> (should contain 1)
        print(f"\n--- Step 7: GET /api/findings?mission_id={mission_id} (should contain 1) ---")
        success, response, duration = self.make_request('GET', '/findings', params={'mission_id': mission_id})
        if success and response.status_code == 200:
            try:
                mission_findings = response.json()
                self.payloads['step7_mission_findings'] = mission_findings
                phoenix_present = self.verify_phoenix_timestamps(mission_findings, "mission findings")
                if isinstance(mission_findings, list):
                    if len(mission_findings) >= 1:
                        self.log_result('step7_get_mission_findings', True, 
                                      f'✅ GET /api/findings?mission_id returned {len(mission_findings)} findings (expected ≥1), Phoenix timestamps: {phoenix_present}', 
                                      {'count': len(mission_findings), 'phoenix_timestamps': phoenix_present}, duration)
                        # Use the finding we just created for next steps
                        if finding_id:
                            test_finding_id = finding_id
                        else:
                            test_finding_id = mission_findings[0].get('id')
                    else:
                        self.log_result('step7_get_mission_findings', False, 
                                      f'❌ GET /api/findings?mission_id returned {len(mission_findings)} findings (expected ≥1)', 
                                      {'count': len(mission_findings)}, duration)
                        return
                else:
                    self.log_result('step7_get_mission_findings', False, 
                                  f'❌ GET /api/findings?mission_id returned non-array: {type(mission_findings)}', 
                                  mission_findings, duration)
                    return
            except Exception as e:
                self.log_result('step7_get_mission_findings', False, f'❌ JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('step7_get_mission_findings', False, 
                          f'❌ GET /api/findings?mission_id failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        # Step 8: GET /api/findings/{id}
        print(f"\n--- Step 8: GET /api/findings/{test_finding_id} ---")
        success, response, duration = self.make_request('GET', f'/findings/{test_finding_id}')
        if success and response.status_code == 200:
            try:
                individual_finding = response.json()
                self.payloads['step8_individual_finding'] = individual_finding
                phoenix_present = self.verify_phoenix_timestamps(individual_finding, "individual finding")
                self.log_result('step8_get_individual_finding', True, 
                              f'✅ GET /api/findings/{test_finding_id} returned finding data, Phoenix timestamps: {phoenix_present}', 
                              {'finding_id': test_finding_id, 'phoenix_timestamps': phoenix_present, 'keys': list(individual_finding.keys()) if isinstance(individual_finding, dict) else None}, duration)
            except Exception as e:
                self.log_result('step8_get_individual_finding', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('step8_get_individual_finding', False, 
                          f'❌ GET /api/findings/{test_finding_id} failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
        
        # Step 9: POST /api/findings/{id}/export?format=md (200, bytes)
        print(f"\n--- Step 9: POST /api/findings/{test_finding_id}/export?format=md (200, bytes) ---")
        success, response, duration = self.make_request('POST', f'/findings/{test_finding_id}/export', params={'format': 'md'})
        if success and response.status_code == 200:
            try:
                export_content = response.text if hasattr(response, 'text') else str(response)
                content_type = response.headers.get('content-type', 'unknown')
                self.payloads['step9_export'] = {
                    'content_preview': export_content[:500],
                    'content_length': len(export_content),
                    'content_type': content_type
                }
                self.log_result('step9_export_finding', True, 
                              f'✅ POST /api/findings/{test_finding_id}/export?format=md returned 200 with {len(export_content)} bytes, content-type: {content_type}', 
                              {'export_length': len(export_content), 'content_type': content_type, 'preview': export_content[:200]}, duration)
            except Exception as e:
                self.log_result('step9_export_finding', False, f'❌ Export processing error: {e}', None, duration)
        else:
            self.log_result('step9_export_finding', False, 
                          f'❌ POST /api/findings/{test_finding_id}/export?format=md failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def run_findings_retest(self):
        """Run the complete findings re-test as per review request"""
        print(f"Starting Findings Endpoints Re-Testing - Base URL: {API_BASE}")
        print("=" * 100)
        
        start_time = time.time()
        
        # Test complete findings flow
        self.test_findings_complete_flow()
        
        total_duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 100)
        print("FINDINGS ENDPOINTS RE-TESTING SUMMARY")
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
        
        print("\nCREATED RESOURCES:")
        for resource_type, resource_id in self.created_resources.items():
            print(f"  {resource_type}: {resource_id}")
        
        print("\nPAYLOADS CAPTURED:")
        for step, payload in self.payloads.items():
            print(f"  {step}: {type(payload).__name__} ({len(str(payload))} chars)")
        
        # Phoenix timestamp verification summary
        phoenix_tests = [r for r in self.results if 'phoenix_timestamps' in str(r.get('response_data', {}))]
        phoenix_passed = sum(1 for r in phoenix_tests if r.get('response_data', {}).get('phoenix_timestamps', False))
        print(f"\nPHOENIX TIMESTAMPS: {phoenix_passed}/{len(phoenix_tests)} endpoints verified with Phoenix timezone (-07:00)")
        
        return self.results, self.payloads

if __name__ == "__main__":
    tester = FindingsRetester()
    results, payloads = tester.run_findings_retest()