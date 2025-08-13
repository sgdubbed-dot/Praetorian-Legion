#!/usr/bin/env python3
"""
Backend API Testing for Augustus - CRITICAL CONTEXT BUG VERIFICATION
Focus: Test Praefectus conversation context management within threads
CRITICAL BUG: Praefectus doesn't read conversation history within the same thread
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

class AugustusKnowledgeIntegrationTester:
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

    def test_knowledge_endpoint(self):
        """Test Praetoria Knowledge Base endpoint - CRITICAL for Augustus integration"""
        print("\n=== TESTING PRAETORIA KNOWLEDGE ENDPOINT ===")
        
        # Test GET /api/knowledge/praetoria
        success, response, duration = self.make_request('GET', '/knowledge/praetoria')
        if not success or response.status_code != 200:
            self.log_result('knowledge_endpoint', False, 
                          f'GET /api/knowledge/praetoria failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        try:
            knowledge_data = response.json()
            
            # Verify comprehensive knowledge structure
            required_keys = [
                'company', 'mission', 'tagline', 'evolution_stages', 
                'target_personas', 'competitive_advantages', 'market_problems', 
                'business_model', 'north_star'
            ]
            
            missing_keys = [key for key in required_keys if key not in knowledge_data]
            if missing_keys:
                self.log_result('knowledge_endpoint', False, 
                              f'Missing required knowledge keys: {missing_keys}', 
                              knowledge_data, duration)
                return
            
            # Verify evolution stages structure
            stages = knowledge_data.get('evolution_stages', {})
            expected_stages = ['stage_1', 'stage_2', 'stage_3']
            missing_stages = [stage for stage in expected_stages if stage not in stages]
            if missing_stages:
                self.log_result('knowledge_endpoint', False, 
                              f'Missing evolution stages: {missing_stages}', 
                              knowledge_data, duration)
                return
            
            # Verify target personas structure
            personas = knowledge_data.get('target_personas', [])
            if not isinstance(personas, list) or len(personas) < 5:
                self.log_result('knowledge_endpoint', False, 
                              f'Target personas incomplete: expected 5+ personas, got {len(personas)}', 
                              knowledge_data, duration)
                return
            
            # Verify competitive advantages
            advantages = knowledge_data.get('competitive_advantages', [])
            if not isinstance(advantages, list) or len(advantages) < 4:
                self.log_result('knowledge_endpoint', False, 
                              f'Competitive advantages incomplete: expected 4+ advantages, got {len(advantages)}', 
                              knowledge_data, duration)
                return
            
            # Check for specific key knowledge elements
            stage_1 = stages.get('stage_1', {})
            if stage_1.get('status') != 'Live now':
                self.log_result('knowledge_endpoint', False, 
                              f'Stage 1 status incorrect: expected "Live now", got "{stage_1.get("status")}"', 
                              knowledge_data, duration)
                return
            
            # Verify framework-agnostic mention
            framework_agnostic_found = any('framework-agnostic' in str(adv).lower() or 'langchain' in str(adv).lower() 
                                         for adv in advantages)
            if not framework_agnostic_found:
                self.log_result('knowledge_endpoint', False, 
                              'Framework-agnostic competitive advantage not found', 
                              knowledge_data, duration)
                return
            
            self.log_result('knowledge_endpoint', True, 
                          f'Praetoria knowledge endpoint comprehensive: {len(required_keys)} sections, {len(personas)} personas, {len(advantages)} advantages', 
                          {
                              'sections': len(required_keys),
                              'personas_count': len(personas),
                              'advantages_count': len(advantages),
                              'stages_count': len(stages),
                              'company': knowledge_data.get('company'),
                              'mission': knowledge_data.get('mission')[:100] + '...' if knowledge_data.get('mission') else None
                          }, duration)
            
            # Store knowledge data for later tests
            self.test_data['knowledge'] = knowledge_data
            
        except Exception as e:
            self.log_result('knowledge_endpoint', False, f'JSON parse error: {e}', None, duration)

    def test_praefectus_knowledge_integration(self):
        """Test Praefectus Mission Control chat with knowledge integration"""
        print("\n=== TESTING PRAEFECTUS KNOWLEDGE INTEGRATION ===")
        
        # First create a thread for testing
        test_thread = {
            "title": "Augustus Knowledge Integration Test"
        }
        
        success, response, duration = self.make_request('POST', '/mission_control/threads', test_thread)
        if not success or response.status_code != 200:
            self.log_result('praefectus_thread_creation', False, 
                          f'Thread creation failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return
        
        try:
            created_thread = response.json()
            thread_id = created_thread.get('thread_id')
            if not thread_id:
                self.log_result('praefectus_thread_creation', False, 'Thread creation missing thread_id', created_thread, duration)
                return
            
            self.test_data['thread_id'] = thread_id
            self.log_result('praefectus_thread_creation', True, 
                          f'Thread created for knowledge testing: {thread_id}', 
                          created_thread, duration)
            
        except Exception as e:
            self.log_result('praefectus_thread_creation', False, f'JSON parse error: {e}', None, duration)
            return
        
        # Test knowledge integration with specific questions
        knowledge_test_questions = [
            {
                "question": "What is Praetoria and what problem does it solve in the agent economy?",
                "expected_keywords": ["praetoria", "agent economy", "visibility", "control", "monitoring", "observability"],
                "test_name": "praetoria_overview_knowledge"
            },
            {
                "question": "Explain Praetoria's 3-stage evolution roadmap and current status.",
                "expected_keywords": ["stage 1", "stage 2", "stage 3", "observability", "registry", "control infrastructure", "live now"],
                "test_name": "evolution_stages_knowledge"
            },
            {
                "question": "Who are Praetoria's target personas and what pain points do we solve for developers?",
                "expected_keywords": ["developers", "startups", "enterprises", "debugging", "observability", "trace", "monitoring"],
                "test_name": "target_personas_knowledge"
            },
            {
                "question": "What makes Praetoria different from competitors? What are our competitive advantages?",
                "expected_keywords": ["framework-agnostic", "langchain", "crewai", "autogen", "agent-native", "privacy-by-design"],
                "test_name": "competitive_advantages_knowledge"
            },
            {
                "question": "How does Praetoria support different agent frameworks like LangChain, CrewAI, and AutoGen?",
                "expected_keywords": ["framework-agnostic", "langchain", "crewai", "autogen", "langgraph", "on-chain"],
                "test_name": "framework_support_knowledge"
            }
        ]
        
        for test_case in knowledge_test_questions:
            print(f"\n--- Testing {test_case['test_name']} ---")
            
            test_message = {
                "thread_id": thread_id,
                "text": test_case["question"]
            }
            
            success, response, duration = self.make_request('POST', '/mission_control/message', test_message)
            if success and response.status_code == 200:
                try:
                    message_response = response.json()
                    assistant_text = message_response.get('assistant', {}).get('text', '')
                    
                    if not assistant_text:
                        self.log_result(test_case['test_name'], False, 
                                      'Praefectus did not respond to knowledge question', 
                                      message_response, duration)
                        continue
                    
                    # Check for expected keywords in response
                    assistant_lower = assistant_text.lower()
                    found_keywords = [kw for kw in test_case['expected_keywords'] if kw.lower() in assistant_lower]
                    missing_keywords = [kw for kw in test_case['expected_keywords'] if kw.lower() not in assistant_lower]
                    
                    # Consider test successful if at least 50% of keywords are found
                    success_threshold = len(test_case['expected_keywords']) * 0.5
                    knowledge_test_passed = len(found_keywords) >= success_threshold
                    
                    if knowledge_test_passed:
                        self.log_result(test_case['test_name'], True, 
                                      f'Praefectus demonstrated knowledge: {len(found_keywords)}/{len(test_case["expected_keywords"])} keywords found, {len(assistant_text)} chars', 
                                      {
                                          'response_length': len(assistant_text),
                                          'found_keywords': found_keywords,
                                          'response_preview': assistant_text[:200] + '...' if len(assistant_text) > 200 else assistant_text
                                      }, duration)
                    else:
                        self.log_result(test_case['test_name'], False, 
                                      f'Insufficient knowledge demonstrated: {len(found_keywords)}/{len(test_case["expected_keywords"])} keywords found. Missing: {missing_keywords}', 
                                      {
                                          'response_length': len(assistant_text),
                                          'found_keywords': found_keywords,
                                          'missing_keywords': missing_keywords,
                                          'response_preview': assistant_text[:200] + '...' if len(assistant_text) > 200 else assistant_text
                                      }, duration)
                    
                except Exception as e:
                    self.log_result(test_case['test_name'], False, f'JSON parse error: {e}', None, duration)
            else:
                self.log_result(test_case['test_name'], False, 
                              f'Message sending failed: {response.status_code if hasattr(response, "status_code") else response}', 
                              None, duration)
            
            # Small delay between questions to avoid rate limiting
            time.sleep(1)

    def test_mission_control_system_prompt_integration(self):
        """Test that Praefectus system prompt includes comprehensive Praetoria knowledge"""
        print("\n=== TESTING SYSTEM PROMPT INTEGRATION ===")
        
        thread_id = self.test_data.get('thread_id')
        if not thread_id:
            self.log_result('system_prompt_integration', False, 'No thread_id available for system prompt testing', None, 0)
            return
        
        # Test with a meta question about Praefectus's role and knowledge
        meta_question = {
            "thread_id": thread_id,
            "text": "As Praefectus, please describe your role in Augustus and your understanding of Praetoria's mission. What specific knowledge do you have about the agent economy?"
        }
        
        success, response, duration = self.make_request('POST', '/mission_control/message', meta_question)
        if success and response.status_code == 200:
            try:
                message_response = response.json()
                assistant_text = message_response.get('assistant', {}).get('text', '')
                
                if not assistant_text:
                    self.log_result('system_prompt_integration', False, 
                                  'Praefectus did not respond to meta question', 
                                  message_response, duration)
                    return
                
                # Check for system prompt integration indicators
                system_prompt_indicators = [
                    "praefectus", "strategic ai commander", "augustus", "praetoria",
                    "agent economy", "observability", "control layer", "mission control",
                    "visibility", "monitoring", "autonomous ai agents"
                ]
                
                assistant_lower = assistant_text.lower()
                found_indicators = [ind for ind in system_prompt_indicators if ind.lower() in assistant_lower]
                
                # Check for role understanding
                role_understanding = any(phrase in assistant_lower for phrase in [
                    "strategic", "commander", "orchestrate", "intelligence", "operations"
                ])
                
                # Check for Praetoria mission understanding
                mission_understanding = any(phrase in assistant_lower for phrase in [
                    "visibility", "control layer", "agent economy", "monitoring", "observability"
                ])
                
                integration_score = len(found_indicators)
                integration_passed = integration_score >= 6 and role_understanding and mission_understanding
                
                if integration_passed:
                    self.log_result('system_prompt_integration', True, 
                                  f'System prompt integration verified: {integration_score} indicators, role & mission understanding confirmed', 
                                  {
                                      'integration_score': integration_score,
                                      'found_indicators': found_indicators,
                                      'role_understanding': role_understanding,
                                      'mission_understanding': mission_understanding,
                                      'response_length': len(assistant_text),
                                      'response_preview': assistant_text[:300] + '...' if len(assistant_text) > 300 else assistant_text
                                  }, duration)
                else:
                    self.log_result('system_prompt_integration', False, 
                                  f'System prompt integration insufficient: {integration_score} indicators, role: {role_understanding}, mission: {mission_understanding}', 
                                  {
                                      'integration_score': integration_score,
                                      'found_indicators': found_indicators,
                                      'role_understanding': role_understanding,
                                      'mission_understanding': mission_understanding,
                                      'response_length': len(assistant_text),
                                      'response_preview': assistant_text[:300] + '...' if len(assistant_text) > 300 else assistant_text
                                  }, duration)
                
            except Exception as e:
                self.log_result('system_prompt_integration', False, f'JSON parse error: {e}', None, duration)
        else:
            self.log_result('system_prompt_integration', False, 
                          f'Meta question failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_agent_economy_expertise(self):
        """Test Praefectus expertise on agent economy challenges and solutions"""
        print("\n=== TESTING AGENT ECONOMY EXPERTISE ===")
        
        thread_id = self.test_data.get('thread_id')
        if not thread_id:
            self.log_result('agent_economy_expertise', False, 'No thread_id available for expertise testing', None, 0)
            return
        
        # Test with complex agent economy scenarios
        expertise_questions = [
            {
                "question": "A startup has deployed 50 AI agents across different frameworks but can't debug when they fail. How does Praetoria solve this?",
                "expected_concepts": ["trace logs", "debugging", "observability", "framework-agnostic", "forensics", "root-cause"],
                "test_name": "debugging_expertise"
            },
            {
                "question": "An enterprise needs governance and compliance for their agent fleet. What does Praetoria offer for Stage 2 and 3?",
                "expected_concepts": ["governance", "compliance", "audit logs", "registry", "identity", "policy enforcement"],
                "test_name": "governance_expertise"
            },
            {
                "question": "How does Praetoria address the challenge of agent identity and reputation in a multi-vendor environment?",
                "expected_concepts": ["agent identity", "reputation", "registry", "verification", "praetoria agent id", "paid"],
                "test_name": "identity_expertise"
            }
        ]
        
        for test_case in expertise_questions:
            print(f"\n--- Testing {test_case['test_name']} ---")
            
            test_message = {
                "thread_id": thread_id,
                "text": test_case["question"]
            }
            
            success, response, duration = self.make_request('POST', '/mission_control/message', test_message)
            if success and response.status_code == 200:
                try:
                    message_response = response.json()
                    assistant_text = message_response.get('assistant', {}).get('text', '')
                    
                    if not assistant_text:
                        self.log_result(test_case['test_name'], False, 
                                      'Praefectus did not respond to expertise question', 
                                      message_response, duration)
                        continue
                    
                    # Check for expected concepts and expertise depth
                    assistant_lower = assistant_text.lower()
                    found_concepts = [concept for concept in test_case['expected_concepts'] if concept.lower() in assistant_lower]
                    
                    # Check for solution-oriented response (not just generic AI talk)
                    solution_indicators = ["praetoria", "stage", "mission control", "trace", "registry", "control infrastructure"]
                    solution_mentions = [ind for ind in solution_indicators if ind.lower() in assistant_lower]
                    
                    # Expertise criteria: good concept coverage + solution focus + sufficient detail
                    concept_coverage = len(found_concepts) / len(test_case['expected_concepts'])
                    has_solution_focus = len(solution_mentions) >= 2
                    sufficient_detail = len(assistant_text) >= 150  # Detailed response expected
                    
                    expertise_demonstrated = concept_coverage >= 0.4 and has_solution_focus and sufficient_detail
                    
                    if expertise_demonstrated:
                        self.log_result(test_case['test_name'], True, 
                                      f'Agent economy expertise demonstrated: {len(found_concepts)}/{len(test_case["expected_concepts"])} concepts, solution-focused, {len(assistant_text)} chars', 
                                      {
                                          'concept_coverage': f"{len(found_concepts)}/{len(test_case['expected_concepts'])}",
                                          'found_concepts': found_concepts,
                                          'solution_mentions': solution_mentions,
                                          'response_length': len(assistant_text),
                                          'response_preview': assistant_text[:250] + '...' if len(assistant_text) > 250 else assistant_text
                                      }, duration)
                    else:
                        self.log_result(test_case['test_name'], False, 
                                      f'Insufficient expertise: {len(found_concepts)}/{len(test_case["expected_concepts"])} concepts, solution focus: {has_solution_focus}, detail: {sufficient_detail}', 
                                      {
                                          'concept_coverage': f"{len(found_concepts)}/{len(test_case['expected_concepts'])}",
                                          'found_concepts': found_concepts,
                                          'solution_mentions': solution_mentions,
                                          'response_length': len(assistant_text),
                                          'response_preview': assistant_text[:250] + '...' if len(assistant_text) > 250 else assistant_text
                                      }, duration)
                    
                except Exception as e:
                    self.log_result(test_case['test_name'], False, f'JSON parse error: {e}', None, duration)
            else:
                self.log_result(test_case['test_name'], False, 
                              f'Expertise question failed: {response.status_code if hasattr(response, "status_code") else response}', 
                              None, duration)
            
            # Small delay between questions
            time.sleep(1)

    def run_augustus_knowledge_integration_test(self):
        """Run comprehensive Augustus knowledge integration test"""
        print(f"Starting Augustus Knowledge Integration Testing - Base URL: {API_BASE}")
        print("=" * 100)
        print("FOCUS: Verify Praetoria knowledge integration in Praefectus system and knowledge endpoints")
        print("=" * 100)
        
        start_time = time.time()
        
        # Run knowledge integration test suites
        self.test_health_endpoints()
        self.test_knowledge_endpoint()
        self.test_praefectus_knowledge_integration()
        self.test_mission_control_system_prompt_integration()
        self.test_agent_economy_expertise()
        
        total_duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 100)
        print("AUGUSTUS KNOWLEDGE INTEGRATION TEST SUMMARY")
        print("=" * 100)
        
        passed = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - passed
        
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.results)*100):.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")
        
        # Categorize results
        knowledge_tests = [r for r in self.results if 'knowledge' in r['test']]
        praefectus_tests = [r for r in self.results if 'praefectus' in r['test'] or 'system_prompt' in r['test']]
        expertise_tests = [r for r in self.results if 'expertise' in r['test'] or any(x in r['test'] for x in ['debugging', 'governance', 'identity'])]
        
        print(f"\nKNOWLEDGE ENDPOINT TESTS: {sum(1 for r in knowledge_tests if r['success'])}/{len(knowledge_tests)} passed")
        print(f"PRAEFECTUS INTEGRATION TESTS: {sum(1 for r in praefectus_tests if r['success'])}/{len(praefectus_tests)} passed")
        print(f"AGENT ECONOMY EXPERTISE TESTS: {sum(1 for r in expertise_tests if r['success'])}/{len(expertise_tests)} passed")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['message']}")
        
        # Knowledge integration assessment
        critical_tests = ['knowledge_endpoint', 'praetoria_overview_knowledge', 'system_prompt_integration']
        critical_passed = sum(1 for r in self.results if r['test'] in critical_tests and r['success'])
        
        print(f"\nCRITICAL KNOWLEDGE INTEGRATION: {critical_passed}/{len(critical_tests)} core tests passed")
        
        if critical_passed == len(critical_tests):
            print("🎉 AUGUSTUS KNOWLEDGE INTEGRATION: SUCCESSFUL")
            print("✅ Praetoria knowledge endpoint comprehensive")
            print("✅ Praefectus demonstrates expert knowledge")
            print("✅ System prompt integration verified")
        else:
            print("⚠️  AUGUSTUS KNOWLEDGE INTEGRATION: NEEDS ATTENTION")
            print("❌ Critical knowledge integration tests failed")
        
        # Test data summary
        if self.test_data:
            print(f"\nTEST DATA CREATED:")
            for key, value in self.test_data.items():
                if isinstance(value, str):
                    print(f"- {key}: {value}")
                elif isinstance(value, dict) and key == 'knowledge':
                    print(f"- {key}: {value.get('company', 'N/A')} knowledge base loaded")
                elif isinstance(value, list):
                    print(f"- {key}: {len(value)} items")
        
        return self.results, passed, failed

if __name__ == "__main__":
    tester = AugustusKnowledgeIntegrationTester()
    results, passed, failed = tester.run_augustus_knowledge_integration_test()