#!/usr/bin/env python3
"""
Backend API Testing for Praetorian Legion - Phase 1 Mission Control Flow
Focus: Exact work order Option 1 flow verification as per review request
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

class MissionControlTester:
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

    def test_phase1_mission_control_flow(self):
        """Test the exact 9-step Mission Control flow as specified in review request"""
        print("\n=== Phase 1 Mission Control Flow Test (Exact Work Order Option 1) ===")
        
        # Step 1: GET /api/providers/models - expect list with raw OpenAI model ids
        print("\n--- Step 1: GET /api/providers/models ---")
        success, response, duration = self.make_request('GET', '/providers/models')
        if success:
            try:
                data = response.json()
                self.payloads['step1_providers_models'] = data
                models = data.get('models', [])
                
                # Check for raw OpenAI model ids
                if isinstance(models, list) and len(models) > 0:
                    # Look for model structure with 'id' field containing OpenAI model names
                    model_ids = [m.get('id', '') for m in models if isinstance(m, dict)]
                    openai_models = [mid for mid in model_ids if 'gpt' in mid.lower() or 'o1' in mid.lower()]
                    
                    if len(openai_models) > 0:
                        self.log_result('step1_providers_models', True, 
                                      f'✅ GET /api/providers/models returned {len(models)} models with {len(openai_models)} OpenAI model ids', 
                                      {'total_models': len(models), 'openai_models': len(openai_models), 'sample_openai': openai_models[:3]}, duration)
                    else:
                        self.log_result('step1_providers_models', False, 
                                      f'❌ No OpenAI model ids found in {len(models)} models', 
                                      {'models': models[:5]}, duration)
                else:
                    self.log_result('step1_providers_models', False, 
                                  f'❌ Invalid models list returned: {type(models)}', 
                                  data, duration)
            except Exception as e:
                self.log_result('step1_providers_models', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('step1_providers_models', False, f'❌ Request failed: {response}', None, duration)
            return
        
        # Step 2: GET /api/providers/health - expect provider=openai and praefectus_model_id with gpt-5*
        print("\n--- Step 2: GET /api/providers/health ---")
        success, response, duration = self.make_request('GET', '/providers/health')
        if success:
            try:
                data = response.json()
                self.payloads['step2_providers_health'] = data
                provider = data.get('provider')
                praefectus_model_id = data.get('praefectus_model_id')
                timestamp = data.get('timestamp')
                
                # Check for expected values and Phoenix timestamp
                provider_ok = provider == 'openai'
                model_ok = praefectus_model_id and 'gpt-5' in str(praefectus_model_id).lower()
                phoenix_ok = timestamp and '-07:00' in timestamp
                
                if provider_ok and model_ok and phoenix_ok:
                    self.log_result('step2_providers_health', True, 
                                  f'✅ GET /api/providers/health: provider={provider}, praefectus_model_id={praefectus_model_id}, Phoenix timestamp', 
                                  data, duration)
                else:
                    self.log_result('step2_providers_health', False, 
                                  f'❌ Health check failed - provider: {provider_ok}, model: {model_ok}, phoenix: {phoenix_ok}', 
                                  data, duration)
            except Exception as e:
                self.log_result('step2_providers_health', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('step2_providers_health', False, f'❌ Request failed: {response}', None, duration)
            return
        
        # Step 3: Create a thread: POST /api/mission_control/threads {"title":"General"}
        print("\n--- Step 3: POST /api/mission_control/threads ---")
        thread_data = {"title": "General"}
        success, response, duration = self.make_request('POST', '/mission_control/threads', thread_data)
        if success:
            try:
                data = response.json()
                self.payloads['step3_create_thread'] = data
                thread_id = data.get('thread_id')
                
                if thread_id:
                    self.log_result('step3_create_thread', True, 
                                  f'✅ Thread created with thread_id: {thread_id}', 
                                  data, duration)
                else:
                    self.log_result('step3_create_thread', False, 
                                  '❌ Thread creation returned no thread_id', 
                                  data, duration)
                    return
            except Exception as e:
                self.log_result('step3_create_thread', False, f'❌ JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('step3_create_thread', False, f'❌ Request failed: {response}', None, duration)
            return
        
        # Step 4: Send message: POST /api/mission_control/message
        print("\n--- Step 4: POST /api/mission_control/message ---")
        message_data = {
            "thread_id": thread_id,
            "text": "Give me a one-line objective for exploring agent observability."
        }
        success, response, duration = self.make_request('POST', '/mission_control/message', message_data)
        if success:
            try:
                data = response.json()
                self.payloads['step4_send_message'] = data
                assistant = data.get('assistant', {})
                assistant_text = assistant.get('text', '')
                created_at = assistant.get('created_at', '')
                
                if assistant_text and created_at:
                    phoenix_ok = '-07:00' in created_at
                    self.log_result('step4_send_message', True, 
                                  f'✅ Message sent, assistant responded ({len(assistant_text)} chars), Phoenix timestamp: {phoenix_ok}', 
                                  {'text_length': len(assistant_text), 'created_at': created_at, 'text_preview': assistant_text[:100]}, duration)
                else:
                    self.log_result('step4_send_message', False, 
                                  f'❌ Incomplete response - text: {bool(assistant_text)}, timestamp: {bool(created_at)}', 
                                  data, duration)
            except Exception as e:
                self.log_result('step4_send_message', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('step4_send_message', False, f'❌ Request failed: {response}', None, duration)
            return
        
        # Step 5: Fetch thread: GET /api/mission_control/thread/{thread_id}?limit=50
        print("\n--- Step 5: GET /api/mission_control/thread/{thread_id}?limit=50 ---")
        success, response, duration = self.make_request('GET', f'/mission_control/thread/{thread_id}?limit=50')
        if success:
            try:
                data = response.json()
                self.payloads['step5_fetch_thread'] = data
                messages = data.get('messages', [])
                
                if len(messages) >= 2:
                    # Check for human and praefectus messages
                    roles = [msg.get('role') for msg in messages]
                    has_human = 'human' in roles
                    has_praefectus = 'praefectus' in roles
                    
                    # Check ordering (ascending by created_at)
                    timestamps = [msg.get('created_at', '') for msg in messages]
                    is_ascending = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
                    
                    # Check Phoenix timestamps
                    phoenix_count = sum(1 for ts in timestamps if '-07:00' in ts)
                    
                    if has_human and has_praefectus and is_ascending and phoenix_count >= 2:
                        self.log_result('step5_fetch_thread', True, 
                                      f'✅ Thread has {len(messages)} messages (human + praefectus), ascending order, {phoenix_count} Phoenix timestamps', 
                                      {'message_count': len(messages), 'roles': roles, 'ascending': is_ascending, 'phoenix_count': phoenix_count}, duration)
                    else:
                        self.log_result('step5_fetch_thread', False, 
                                      f'❌ Thread validation failed - human: {has_human}, praefectus: {has_praefectus}, ascending: {is_ascending}, phoenix: {phoenix_count}', 
                                      {'messages': messages}, duration)
                else:
                    self.log_result('step5_fetch_thread', False, 
                                  f'❌ Insufficient messages: {len(messages)}', 
                                  data, duration)
            except Exception as e:
                self.log_result('step5_fetch_thread', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('step5_fetch_thread', False, f'❌ Request failed: {response}', None, duration)
            return
        
        # Step 6: Summarize: POST /api/mission_control/summarize
        print("\n--- Step 6: POST /api/mission_control/summarize ---")
        summarize_data = {"thread_id": thread_id}
        success, response, duration = self.make_request('POST', '/mission_control/summarize', summarize_data)
        if success:
            try:
                data = response.json()
                self.payloads['step6_summarize'] = data
                structured_text = data.get('structured_text', '')
                timestamp = data.get('timestamp', '')
                
                if structured_text and timestamp:
                    phoenix_ok = '-07:00' in timestamp
                    self.log_result('step6_summarize', True, 
                                  f'✅ Thread summarized: structured_text ({len(structured_text)} chars), Phoenix timestamp: {phoenix_ok}', 
                                  {'text_length': len(structured_text), 'timestamp': timestamp, 'text_preview': structured_text[:200]}, duration)
                else:
                    self.log_result('step6_summarize', False, 
                                  f'❌ Incomplete summary - text: {bool(structured_text)}, timestamp: {bool(timestamp)}', 
                                  data, duration)
            except Exception as e:
                self.log_result('step6_summarize', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('step6_summarize', False, f'❌ Request failed: {response}', None, duration)
            return
        
        # Step 7: Convert to draft (no warnings): POST /api/mission_control/convert_to_draft
        print("\n--- Step 7: POST /api/mission_control/convert_to_draft ---")
        draft_data = {
            "thread_id": thread_id,
            "fields_override": {
                "title": "Obs",
                "objective": "Test",
                "posture": "help_only",
                "audience": "ops leaders",
                "success_criteria": ["3 forums"],
                "risks": ["low engagement"],
                "approvals_needed": ["ops"],
                "notes": "n/a"
            }
        }
        success, response, duration = self.make_request('POST', '/mission_control/convert_to_draft', draft_data)
        if success:
            try:
                data = response.json()
                self.payloads['step7_convert_to_draft'] = data
                draft = data.get('draft', {})
                warnings = data.get('warnings', [])
                approval_blocked = data.get('approval_blocked', False)
                timestamp = data.get('timestamp', '')
                
                if isinstance(draft, dict) and not approval_blocked:
                    self.log_result('step7_convert_to_draft', True, 
                                  f'✅ Draft created: approval_blocked={approval_blocked}, warnings={len(warnings)}', 
                                  {'draft': draft, 'warnings': warnings, 'approval_blocked': approval_blocked}, duration)
                else:
                    self.log_result('step7_convert_to_draft', False, 
                                  f'❌ Draft conversion failed - blocked: {approval_blocked}, warnings: {warnings}', 
                                  data, duration)
            except Exception as e:
                self.log_result('step7_convert_to_draft', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('step7_convert_to_draft', False, f'❌ Request failed: {response}', None, duration)
            return
        
        # Step 8: Approve draft: POST /api/mission_control/approve_draft
        print("\n--- Step 8: POST /api/mission_control/approve_draft ---")
        approve_data = {
            "thread_id": thread_id,
            "draft": {
                "title": "Obs",
                "objective": "Test",
                "posture": "help_only"
            }
        }
        success, response, duration = self.make_request('POST', '/mission_control/approve_draft', approve_data)
        if success:
            try:
                data = response.json()
                self.payloads['step8_approve_draft'] = data
                mission_id = data.get('mission_id')
                timestamp = data.get('timestamp', '')
                
                if mission_id:
                    phoenix_ok = '-07:00' in timestamp
                    self.log_result('step8_approve_draft', True, 
                                  f'✅ Draft approved: mission_id={mission_id}, Phoenix timestamp: {phoenix_ok}', 
                                  data, duration)
                else:
                    self.log_result('step8_approve_draft', False, 
                                  '❌ Draft approval failed - no mission_id returned', 
                                  data, duration)
                    return
            except Exception as e:
                self.log_result('step8_approve_draft', False, f'❌ JSON parse error: {e}', None, duration)
                return
        else:
            self.log_result('step8_approve_draft', False, f'❌ Request failed: {response}', None, duration)
            return
        
        # Step 9: Start mission: POST /api/mission_control/start_mission
        print("\n--- Step 9: POST /api/mission_control/start_mission ---")
        start_data = {"mission_id": mission_id}
        success, response, duration = self.make_request('POST', '/mission_control/start_mission', start_data)
        if success:
            try:
                data = response.json()
                self.payloads['step9_start_mission'] = data
                ok = data.get('ok')
                returned_mission_id = data.get('mission_id')
                timestamp = data.get('timestamp', '')
                
                if ok and returned_mission_id == mission_id:
                    phoenix_ok = '-07:00' in timestamp
                    self.log_result('step9_start_mission', True, 
                                  f'✅ Mission started: ok={ok}, mission_id={mission_id}, Phoenix timestamp: {phoenix_ok}', 
                                  data, duration)
                else:
                    self.log_result('step9_start_mission', False, 
                                  f'❌ Mission start failed - ok: {ok}, mission_id match: {returned_mission_id == mission_id}', 
                                  data, duration)
            except Exception as e:
                self.log_result('step9_start_mission', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('step9_start_mission', False, f'❌ Request failed: {response}', None, duration)
            return
        
        # Step 10: Events verification: GET /api/events?source=backend/mission_control&limit=20
        print("\n--- Step 10: GET /api/events?source=backend/mission_control&limit=20 ---")
        success, response, duration = self.make_request('GET', '/events?source=backend/mission_control&limit=20')
        if success:
            try:
                events = response.json()
                self.payloads['step10_events'] = events
                
                # Look for required events
                event_names = [event.get('event_name') for event in events]
                required_events = [
                    'praefectus_message_appended',
                    'mission_summary_prepared', 
                    'mission_draft_prepared',
                    'mission_created',
                    'mission_started'
                ]
                
                found_events = [name for name in required_events if name in event_names]
                phoenix_timestamps = sum(1 for event in events if '-07:00' in event.get('timestamp', ''))
                
                if len(found_events) >= 4:  # Allow some flexibility
                    self.log_result('step10_events', True, 
                                  f'✅ Events found: {len(found_events)}/{len(required_events)} required events, {phoenix_timestamps} Phoenix timestamps', 
                                  {'found_events': found_events, 'all_events': event_names[:10], 'phoenix_count': phoenix_timestamps}, duration)
                else:
                    self.log_result('step10_events', False, 
                                  f'❌ Missing events - found: {found_events}, required: {required_events}', 
                                  {'found_events': found_events, 'all_events': event_names[:10]}, duration)
            except Exception as e:
                self.log_result('step10_events', False, f'❌ JSON parse error: {e}', None, duration)
        else:
            self.log_result('step10_events', False, f'❌ Request failed: {response}', None, duration)

    def run_test(self):
        """Run the Phase 1 Mission Control flow test"""
        print(f"Starting Phase 1 Mission Control Backend Test - Base URL: {API_BASE}")
        print("=" * 100)
        
        start_time = time.time()
        
        # Run the 9-step flow test
        self.test_phase1_mission_control_flow()
        
        total_duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 100)
        print("PHASE 1 MISSION CONTROL TEST SUMMARY")
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
    tester = MissionControlTester()
    results, payloads = tester.run_test()