#!/usr/bin/env python3
"""
Backend API Testing for Praetorian Legion
Focus: P1 Items Verification - Health, Missions, Forums, Prospects, HotLeads
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
        self.created_resources = {
            'missions': [],
            'forums': [],
            'prospects': [],
            'hotleads': []
        }
        
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
        """P1 Test: Health endpoint GET /api/health"""
        print("\n=== P1 Test: Health Endpoint ===")
        
        success, response, duration = self.make_request('GET', '/health')
        if success:
            try:
                data = response.json()
                if data.get('ok') is True and 'timestamp' in data:
                    # Verify Phoenix timestamp format
                    timestamp = data.get('timestamp', '')
                    has_phoenix_tz = '-07:00' in timestamp or 'MST' in timestamp
                    self.log_result('health_endpoint', True, 
                                  f'Health endpoint working correctly, Phoenix timestamp: {has_phoenix_tz}', 
                                  data, duration)
                else:
                    self.log_result('health_endpoint', False, 
                                  f'Health endpoint returned unexpected data: {data}', data, duration)
            except Exception as e:
                self.log_result('health_endpoint', False, 
                              f'Health endpoint JSON parse error: {e}', None, duration)
        else:
            self.log_result('health_endpoint', False, 
                          f'Health endpoint failed: {response}', None, duration)

    def test_mission_state_transitions(self):
        """P1 Test: Mission state transitions and events"""
        print("\n=== P1 Test: Mission State Transitions ===")
        
        # Create mission
        mission_data = {
            "title": "P1 Test Mission State Transitions",
            "objective": "Test mission state transitions and events",
            "posture": "help_only",
            "state": "draft"
        }
        
        success, response, duration = self.make_request('POST', '/missions', mission_data)
        if not success:
            self.log_result('create_mission', False, f'Failed to create mission: {response}', None, duration)
            return
            
        try:
            mission = response.json()
            mission_id = mission.get('id')
            self.created_resources['missions'].append(mission_id)
            self.log_result('create_mission', True, f'Mission created: {mission_id}', mission, duration)
        except Exception as e:
            self.log_result('create_mission', False, f'Mission creation JSON parse error: {e}', None, duration)
            return
        
        # PATCH to paused
        success, response, duration = self.make_request('PATCH', f'/missions/{mission_id}', {"state": "paused"})
        if success:
            try:
                updated_mission = response.json()
                if updated_mission.get('state') == 'paused' and updated_mission.get('previous_active_state') == 'draft':
                    self.log_result('patch_to_paused', True, 
                                  'Mission successfully patched to paused with previous_active_state stored', 
                                  updated_mission, duration)
                else:
                    self.log_result('patch_to_paused', False, 
                                  f'Mission patch to paused failed - state: {updated_mission.get("state")}, previous: {updated_mission.get("previous_active_state")}', 
                                  updated_mission, duration)
            except Exception as e:
                self.log_result('patch_to_paused', False, f'Patch to paused JSON parse error: {e}', None, duration)
        else:
            self.log_result('patch_to_paused', False, f'Patch to paused failed: {response}', None, duration)
        
        # POST resume
        success, response, duration = self.make_request('POST', f'/missions/{mission_id}/state', {"state": "resume"})
        if success:
            try:
                resumed_mission = response.json()
                if resumed_mission.get('state') == 'draft':  # Should resume to previous_active_state
                    self.log_result('post_resume', True, 
                                  f'Mission successfully resumed to previous state: {resumed_mission.get("state")}', 
                                  resumed_mission, duration)
                else:
                    self.log_result('post_resume', False, 
                                  f'Mission resume failed - state: {resumed_mission.get("state")}', 
                                  resumed_mission, duration)
            except Exception as e:
                self.log_result('post_resume', False, f'Resume JSON parse error: {e}', None, duration)
        else:
            self.log_result('post_resume', False, f'Resume failed: {response}', None, duration)
        
        # POST abort
        success, response, duration = self.make_request('POST', f'/missions/{mission_id}/state', {"state": "abort"})
        if success:
            try:
                aborted_mission = response.json()
                if aborted_mission.get('state') == 'aborted':
                    self.log_result('post_abort', True, 
                                  'Mission successfully aborted', 
                                  aborted_mission, duration)
                else:
                    self.log_result('post_abort', False, 
                                  f'Mission abort failed - state: {aborted_mission.get("state")}', 
                                  aborted_mission, duration)
            except Exception as e:
                self.log_result('post_abort', False, f'Abort JSON parse error: {e}', None, duration)
        else:
            self.log_result('post_abort', False, f'Abort failed: {response}', None, duration)
        
        # Check events for mission_paused, mission_resumed, mission_aborted
        success, response, duration = self.make_request('GET', f'/events?mission_id={mission_id}&limit=10')
        if success:
            try:
                events = response.json()
                event_names = [event.get('event_name') for event in events]
                expected_events = ['mission_paused', 'mission_resumed', 'mission_aborted']
                found_events = [name for name in expected_events if name in event_names]
                
                if len(found_events) >= 2:  # At least paused and aborted should be there
                    self.log_result('mission_events', True, 
                                  f'Mission events found: {found_events}', 
                                  {'events': found_events, 'all_events': event_names}, duration)
                else:
                    self.log_result('mission_events', False, 
                                  f'Missing mission events - found: {found_events}, expected: {expected_events}', 
                                  {'events': found_events, 'all_events': event_names}, duration)
            except Exception as e:
                self.log_result('mission_events', False, f'Mission events JSON parse error: {e}', None, duration)
        else:
            self.log_result('mission_events', False, f'Mission events check failed: {response}', None, duration)

    def test_mission_insights_migration(self):
        """P1 Test: Mission insights_rich auto-population from legacy insights"""
        print("\n=== P1 Test: Mission Insights Migration ===")
        
        # Create mission with legacy insights
        mission_data = {
            "title": "P1 Test Insights Migration",
            "objective": "Test insights_rich auto-population",
            "posture": "research_only",
            "state": "draft",
            "insights": ["Legacy insight 1", "Legacy insight 2"]
        }
        
        success, response, duration = self.make_request('POST', '/missions', mission_data)
        if not success:
            self.log_result('create_mission_with_insights', False, f'Failed to create mission with insights: {response}', None, duration)
            return
            
        try:
            mission = response.json()
            mission_id = mission.get('id')
            self.created_resources['missions'].append(mission_id)
            
            # Check if insights_rich was auto-populated during creation
            insights_rich = mission.get('insights_rich', [])
            if insights_rich and len(insights_rich) == 2:
                self.log_result('create_mission_with_insights', True, 
                              f'Mission created with insights_rich auto-populated: {len(insights_rich)} items', 
                              mission, duration)
            else:
                self.log_result('create_mission_with_insights', True, 
                              f'Mission created, insights_rich: {len(insights_rich)} items', 
                              mission, duration)
        except Exception as e:
            self.log_result('create_mission_with_insights', False, f'Mission with insights creation JSON parse error: {e}', None, duration)
            return
        
        # GET mission to trigger migration if not already done
        success, response, duration = self.make_request('GET', f'/missions/{mission_id}')
        if success:
            try:
                retrieved_mission = response.json()
                insights_rich = retrieved_mission.get('insights_rich', [])
                legacy_insights = retrieved_mission.get('insights', [])
                
                if insights_rich and len(insights_rich) == len(legacy_insights):
                    # Verify structure
                    has_proper_structure = all(
                        isinstance(item, dict) and 'text' in item and 'timestamp' in item 
                        for item in insights_rich
                    )
                    if has_proper_structure:
                        self.log_result('insights_migration', True, 
                                      f'insights_rich properly auto-populated with {len(insights_rich)} items', 
                                      {'insights_rich': insights_rich}, duration)
                    else:
                        self.log_result('insights_migration', False, 
                                      'insights_rich populated but structure incorrect', 
                                      {'insights_rich': insights_rich}, duration)
                else:
                    self.log_result('insights_migration', False, 
                                  f'insights_rich not properly populated - rich: {len(insights_rich)}, legacy: {len(legacy_insights)}', 
                                  {'insights_rich': insights_rich, 'legacy_insights': legacy_insights}, duration)
            except Exception as e:
                self.log_result('insights_migration', False, f'Insights migration check JSON parse error: {e}', None, duration)
        else:
            self.log_result('insights_migration', False, f'GET mission for insights migration failed: {response}', None, duration)

    def test_forum_link_validation(self):
        """P1 Test: Forum link validation and status checking"""
        print("\n=== P1 Test: Forum Link Validation ===")
        
        # Test with reachable URL
        reachable_forum = {
            "platform": "Test Platform",
            "name": "Reachable Forum",
            "url": "https://httpbin.org/status/200",
            "rule_profile": "strict_help_only",
            "topic_tags": ["test"]
        }
        
        success, response, duration = self.make_request('POST', '/forums', reachable_forum)
        if success:
            try:
                forum = response.json()
                forum_id = forum.get('id')
                self.created_resources['forums'].append(forum_id)
                
                link_status = forum.get('link_status')
                last_checked_at = forum.get('last_checked_at')
                
                if link_status == 'ok' and last_checked_at:
                    self.log_result('reachable_forum_creation', True, 
                                  f'Reachable forum created with link_status=ok and last_checked_at set', 
                                  {'link_status': link_status, 'last_checked_at': last_checked_at}, duration)
                else:
                    self.log_result('reachable_forum_creation', False, 
                                  f'Reachable forum link validation failed - status: {link_status}, checked: {last_checked_at}', 
                                  forum, duration)
            except Exception as e:
                self.log_result('reachable_forum_creation', False, f'Reachable forum JSON parse error: {e}', None, duration)
        else:
            self.log_result('reachable_forum_creation', False, f'Reachable forum creation failed: {response}', None, duration)
        
        # Test with invalid URL
        invalid_forum = {
            "platform": "Test Platform",
            "name": "Invalid Forum",
            "url": "https://invalid-domain-that-does-not-exist-12345.com",
            "rule_profile": "strict_help_only",
            "topic_tags": ["test"]
        }
        
        success, response, duration = self.make_request('POST', '/forums', invalid_forum)
        if success:
            try:
                forum = response.json()
                forum_id = forum.get('id')
                self.created_resources['forums'].append(forum_id)
                
                link_status = forum.get('link_status')
                last_checked_at = forum.get('last_checked_at')
                
                if link_status in ['blocked', 'not_found'] and last_checked_at:
                    self.log_result('invalid_forum_creation', True, 
                                  f'Invalid forum created with link_status={link_status} and last_checked_at set', 
                                  {'link_status': link_status, 'last_checked_at': last_checked_at}, duration)
                else:
                    self.log_result('invalid_forum_creation', False, 
                                  f'Invalid forum link validation unexpected - status: {link_status}, checked: {last_checked_at}', 
                                  forum, duration)
            except Exception as e:
                self.log_result('invalid_forum_creation', False, f'Invalid forum JSON parse error: {e}', None, duration)
        else:
            self.log_result('invalid_forum_creation', False, f'Invalid forum creation failed: {response}', None, duration)
        
        # Test check_link endpoint
        if self.created_resources['forums']:
            forum_id = self.created_resources['forums'][0]
            success, response, duration = self.make_request('POST', f'/forums/{forum_id}/check_link')
            if success:
                try:
                    updated_forum = response.json()
                    link_status = updated_forum.get('link_status')
                    last_checked_at = updated_forum.get('last_checked_at')
                    
                    if link_status and last_checked_at:
                        self.log_result('forum_check_link', True, 
                                      f'Forum check_link updated status to {link_status}', 
                                      {'link_status': link_status, 'last_checked_at': last_checked_at}, duration)
                    else:
                        self.log_result('forum_check_link', False, 
                                      f'Forum check_link failed to update - status: {link_status}, checked: {last_checked_at}', 
                                      updated_forum, duration)
                except Exception as e:
                    self.log_result('forum_check_link', False, f'Forum check_link JSON parse error: {e}', None, duration)
            else:
                self.log_result('forum_check_link', False, f'Forum check_link failed: {response}', None, duration)

    def test_prospect_source_type_defaults(self):
        """P1 Test: Prospect source_type defaults and seeded scenarios"""
        print("\n=== P1 Test: Prospect Source Type Defaults ===")
        
        # Test POST /prospects without source_type - should default to manual
        prospect_manual = {
            "name_or_alias": "Manual Test Prospect",
            "handles": {"linkedin": "manual-test"},
            "priority_state": "cold"
        }
        
        success, response, duration = self.make_request('POST', '/prospects', prospect_manual)
        if success:
            try:
                prospect = response.json()
                prospect_id = prospect.get('id')
                self.created_resources['prospects'].append(prospect_id)
                
                source_type = prospect.get('source_type')
                if source_type == 'manual':
                    self.log_result('prospect_manual_default', True, 
                                  'Prospect without source_type correctly defaults to manual', 
                                  {'source_type': source_type}, duration)
                else:
                    self.log_result('prospect_manual_default', False, 
                                  f'Prospect source_type default failed - got: {source_type}', 
                                  prospect, duration)
            except Exception as e:
                self.log_result('prospect_manual_default', False, f'Manual prospect JSON parse error: {e}', None, duration)
        else:
            self.log_result('prospect_manual_default', False, f'Manual prospect creation failed: {response}', None, duration)
        
        # Test scenario_* seeded prospects
        success, response, duration = self.make_request('POST', '/scenarios/strict_rule_mission')
        if success:
            try:
                result = response.json()
                mission_id = result.get('mission_id')
                if mission_id:
                    self.created_resources['missions'].append(mission_id)
                    self.log_result('scenario_seeded_mission', True, 
                                  f'Scenario mission created: {mission_id}', 
                                  result, duration)
                    
                    # Check if prospects were created with source_type=seeded
                    time.sleep(1)  # Brief delay
                    success2, response2, duration2 = self.make_request('GET', '/prospects')
                    if success2:
                        try:
                            prospects = response2.json()
                            seeded_prospects = [p for p in prospects if p.get('source_type') == 'seeded']
                            
                            if len(seeded_prospects) >= 2:
                                self.log_result('scenario_seeded_prospects', True, 
                                              f'Scenario created {len(seeded_prospects)} prospects with source_type=seeded', 
                                              {'seeded_count': len(seeded_prospects)}, duration2)
                            else:
                                self.log_result('scenario_seeded_prospects', False, 
                                              f'Scenario created insufficient seeded prospects: {len(seeded_prospects)}', 
                                              {'seeded_prospects': seeded_prospects}, duration2)
                        except Exception as e:
                            self.log_result('scenario_seeded_prospects', False, f'Seeded prospects check JSON parse error: {e}', None, duration2)
                    else:
                        self.log_result('scenario_seeded_prospects', False, f'Seeded prospects check failed: {response2}', None, duration2)
                else:
                    self.log_result('scenario_seeded_mission', False, 'Scenario mission creation returned no mission_id', result, duration)
            except Exception as e:
                self.log_result('scenario_seeded_mission', False, f'Scenario mission JSON parse error: {e}', None, duration)
        else:
            self.log_result('scenario_seeded_mission', False, f'Scenario mission creation failed: {response}', None, duration)

    def test_hotlead_script_editing(self):
        """P1 Test: HotLead PATCH updates proposed_script and emits event"""
        print("\n=== P1 Test: HotLead Script Editing ===")
        
        # First create a prospect
        prospect_data = {
            "name_or_alias": "HotLead Test Prospect",
            "handles": {"linkedin": "hotlead-test"},
            "priority_state": "hot"
        }
        
        success, response, duration = self.make_request('POST', '/prospects', prospect_data)
        if not success:
            self.log_result('create_prospect_for_hotlead', False, f'Failed to create prospect for hotlead: {response}', None, duration)
            return
            
        try:
            prospect = response.json()
            prospect_id = prospect.get('id')
            self.created_resources['prospects'].append(prospect_id)
            self.log_result('create_prospect_for_hotlead', True, f'Prospect created for hotlead: {prospect_id}', None, duration)
        except Exception as e:
            self.log_result('create_prospect_for_hotlead', False, f'Prospect for hotlead JSON parse error: {e}', None, duration)
            return
        
        # Create hotlead
        hotlead_data = {
            "prospect_id": prospect_id,
            "evidence": [{"quote": "Strong buying signal for testing", "link": "https://example.com/test"}],
            "proposed_script": "Initial script for testing",
            "suggested_actions": ["test action"]
        }
        
        success, response, duration = self.make_request('POST', '/hotleads', hotlead_data)
        if not success:
            self.log_result('create_hotlead', False, f'Failed to create hotlead: {response}', None, duration)
            return
            
        try:
            hotlead = response.json()
            hotlead_id = hotlead.get('id')
            self.created_resources['hotleads'].append(hotlead_id)
            self.log_result('create_hotlead', True, f'HotLead created: {hotlead_id}', hotlead, duration)
        except Exception as e:
            self.log_result('create_hotlead', False, f'HotLead creation JSON parse error: {e}', None, duration)
            return
        
        # PATCH hotlead to update proposed_script
        updated_script = "Updated script after review and refinement"
        patch_data = {"proposed_script": updated_script}
        
        success, response, duration = self.make_request('PATCH', f'/hotleads/{hotlead_id}', patch_data)
        if success:
            try:
                updated_hotlead = response.json()
                if updated_hotlead.get('proposed_script') == updated_script:
                    self.log_result('hotlead_script_update', True, 
                                  'HotLead proposed_script successfully updated', 
                                  {'new_script': updated_script}, duration)
                else:
                    self.log_result('hotlead_script_update', False, 
                                  f'HotLead script update failed - got: {updated_hotlead.get("proposed_script")}', 
                                  updated_hotlead, duration)
            except Exception as e:
                self.log_result('hotlead_script_update', False, f'HotLead script update JSON parse error: {e}', None, duration)
        else:
            self.log_result('hotlead_script_update', False, f'HotLead script update failed: {response}', None, duration)
        
        # Check for hotlead_script_edited event
        success, response, duration = self.make_request('GET', f'/events?hotlead_id={hotlead_id}&limit=10')
        if success:
            try:
                events = response.json()
                event_names = [event.get('event_name') for event in events]
                
                if 'hotlead_script_edited' in event_names:
                    self.log_result('hotlead_script_event', True, 
                                  'hotlead_script_edited event found', 
                                  {'events': event_names}, duration)
                else:
                    self.log_result('hotlead_script_event', False, 
                                  f'hotlead_script_edited event not found - events: {event_names}', 
                                  {'events': event_names}, duration)
            except Exception as e:
                self.log_result('hotlead_script_event', False, f'HotLead script event check JSON parse error: {e}', None, duration)
        else:
            self.log_result('hotlead_script_event', False, f'HotLead script event check failed: {response}', None, duration)

    def verify_phoenix_timestamps(self):
        """Verify Phoenix timestamps across all responses"""
        print("\n=== Verifying Phoenix Timestamps ===")
        
        # Check health endpoint timestamp
        success, response, duration = self.make_request('GET', '/health')
        if success:
            try:
                data = response.json()
                timestamp = data.get('timestamp', '')
                has_phoenix_tz = '-07:00' in timestamp or 'MST' in timestamp
                self.log_result('phoenix_timestamp_health', has_phoenix_tz, 
                              f'Health timestamp Phoenix format: {timestamp}', 
                              {'timestamp': timestamp}, duration)
            except Exception as e:
                self.log_result('phoenix_timestamp_health', False, f'Health timestamp check error: {e}', None, duration)
        
        # Check events timestamps
        success, response, duration = self.make_request('GET', '/events?limit=5')
        if success:
            try:
                events = response.json()
                phoenix_count = 0
                for event in events[:3]:
                    timestamp = event.get('timestamp', '')
                    if '-07:00' in timestamp or 'MST' in timestamp:
                        phoenix_count += 1
                
                has_phoenix = phoenix_count > 0
                self.log_result('phoenix_timestamp_events', has_phoenix, 
                              f'Events Phoenix timestamps: {phoenix_count}/{len(events[:3])}', 
                              {'sample_events': events[:2]}, duration)
            except Exception as e:
                self.log_result('phoenix_timestamp_events', False, f'Events timestamp check error: {e}', None, duration)

    def run_all_tests(self):
        """Run all P1 backend API tests"""
        print(f"Starting P1 Backend API Tests - Base URL: {API_BASE}")
        print("=" * 80)
        
        start_time = time.time()
        
        # Run P1 tests in order
        self.test_health_endpoint()
        self.test_mission_state_transitions()
        self.test_mission_insights_migration()
        self.test_forum_link_validation()
        self.test_prospect_source_type_defaults()
        self.test_hotlead_script_editing()
        self.verify_phoenix_timestamps()
        
        total_duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 80)
        print("P1 BACKEND API TEST SUMMARY")
        print("=" * 80)
        
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
        
        print(f"\nCreated Resources Summary:")
        for resource_type, ids in self.created_resources.items():
            if ids:
                print(f"  {resource_type}: {len(ids)} created")
        
        return self.results

if __name__ == "__main__":
    tester = BackendTester()
    results = tester.run_all_tests()