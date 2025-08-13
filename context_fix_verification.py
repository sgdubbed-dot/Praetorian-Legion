#!/usr/bin/env python3
"""
CRITICAL BUG FIX VERIFICATION - CONTEXT MANAGEMENT SUCCESS
Verify the specific scenarios mentioned in the review request
"""

import requests
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://progress-pulse-21.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class ContextFixVerifier:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.results = []
        
    def log_result(self, test_name: str, success: bool, message: str, details: dict = None):
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details:
            for key, value in details.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: {value[:100]}...")
                else:
                    print(f"  {key}: {value}")
        
    def make_request(self, method: str, endpoint: str, data: dict = None):
        url = f"{API_BASE}{endpoint}"
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            return True, response
        except Exception as e:
            return False, str(e)

    def test_thread_conversation_continuity(self):
        """Test: Create new thread, have multi-message conversation, ask for summary"""
        print("\n=== TEST 1: THREAD CONVERSATION CONTINUITY ===")
        
        # Create thread
        success, response = self.make_request('POST', '/mission_control/threads', {
            "title": "Operation Test"
        })
        
        if not success or response.status_code != 200:
            self.log_result('thread_creation', False, f'Failed to create thread: {response}')
            return None
            
        thread_id = response.json().get('thread_id')
        
        # Multi-message conversation
        messages = [
            "I need to identify our target market for Praetoria. Focus on GitHub repositories and Discord communities",
            "What specific types of GitHub repositories should we target?",
            "How should we approach Discord communities without being spammy?"
        ]
        
        responses = []
        for i, msg in enumerate(messages):
            success, response = self.make_request('POST', '/mission_control/message', {
                "thread_id": thread_id,
                "text": msg
            })
            
            if success and response.status_code == 200:
                assistant_text = response.json().get('assistant', {}).get('text', '')
                responses.append(assistant_text)
                print(f"Message {i+1} sent successfully")
            else:
                self.log_result('multi_message_conversation', False, f'Failed to send message {i+1}')
                return None
            
            time.sleep(1)  # Small delay between messages
        
        # Ask for summary
        success, response = self.make_request('POST', '/mission_control/message', {
            "thread_id": thread_id,
            "text": "Tell me about the operation we are building"
        })
        
        if success and response.status_code == 200:
            summary_response = response.json().get('assistant', {}).get('text', '')
            
            # Check if summary references actual conversation
            summary_lower = summary_response.lower()
            context_indicators = [
                'operation', 'target market', 'praetoria', 'github', 'discord',
                'discussed', 'conversation', 'building'
            ]
            
            found_indicators = [ind for ind in context_indicators if ind in summary_lower]
            context_score = len(found_indicators) / len(context_indicators)
            
            if context_score >= 0.5:  # At least 50% of context indicators found
                self.log_result('thread_conversation_continuity', True, 
                              'Praefectus successfully references actual conversation details',
                              {
                                  'thread_id': thread_id,
                                  'context_score': f"{context_score:.2f}",
                                  'found_indicators': found_indicators,
                                  'summary_preview': summary_response[:200]
                              })
            else:
                self.log_result('thread_conversation_continuity', False,
                              'Praefectus does not reference conversation context',
                              {
                                  'context_score': f"{context_score:.2f}",
                                  'found_indicators': found_indicators,
                                  'summary_preview': summary_response[:200]
                              })
        else:
            self.log_result('thread_conversation_continuity', False, 'Failed to get summary response')
            
        return thread_id

    def test_operation_context_persistence(self):
        """Test: Verify Praefectus remembers operation details across messages"""
        print("\n=== TEST 2: OPERATION CONTEXT PERSISTENCE ===")
        
        # Create new thread
        success, response = self.make_request('POST', '/mission_control/threads', {
            "title": "Context Persistence Test"
        })
        
        if not success or response.status_code != 200:
            self.log_result('context_persistence_setup', False, 'Failed to create thread')
            return
            
        thread_id = response.json().get('thread_id')
        
        # Build operation context step by step
        context_messages = [
            "We're planning Operation Digital Reconnaissance to map the agent ecosystem",
            "Our primary targets are enterprise security teams and AI development companies",
            "The operation will run for 8 weeks with bi-weekly checkpoints",
            "We'll use LinkedIn for executive outreach and GitHub for developer engagement"
        ]
        
        # Send context-building messages
        for i, msg in enumerate(context_messages):
            success, response = self.make_request('POST', '/mission_control/message', {
                "thread_id": thread_id,
                "text": msg
            })
            
            if not (success and response.status_code == 200):
                self.log_result('operation_context_persistence', False, f'Failed to send context message {i+1}')
                return
            
            time.sleep(1)
        
        # Test context persistence with specific questions
        test_questions = [
            "What is the name of our operation?",
            "Who are our primary targets?", 
            "How long will this operation run?",
            "What platforms will we use?"
        ]
        
        expected_answers = [
            ['digital reconnaissance', 'reconnaissance'],
            ['enterprise security', 'ai development', 'security teams'],
            ['8 weeks', 'eight weeks', 'bi-weekly'],
            ['linkedin', 'github']
        ]
        
        persistence_score = 0
        for i, question in enumerate(test_questions):
            success, response = self.make_request('POST', '/mission_control/message', {
                "thread_id": thread_id,
                "text": question
            })
            
            if success and response.status_code == 200:
                answer = response.json().get('assistant', {}).get('text', '').lower()
                
                # Check if answer contains expected elements
                found_elements = [elem for elem in expected_answers[i] if elem in answer]
                if found_elements:
                    persistence_score += 1
                    print(f"Question {i+1}: ✅ Found {found_elements}")
                else:
                    print(f"Question {i+1}: ❌ No expected elements found")
            
            time.sleep(1)
        
        persistence_working = persistence_score >= 3  # At least 3/4 questions answered correctly
        
        if persistence_working:
            self.log_result('operation_context_persistence', True,
                          f'Operation context persists across messages: {persistence_score}/4 questions answered correctly',
                          {'thread_id': thread_id, 'score': f"{persistence_score}/4"})
        else:
            self.log_result('operation_context_persistence', False,
                          f'Operation context does not persist: only {persistence_score}/4 questions answered correctly',
                          {'thread_id': thread_id, 'score': f"{persistence_score}/4"})

    def test_context_integration_with_system_prompt(self):
        """Test: Verify updated SYSTEM_PROMPT works with conversation history"""
        print("\n=== TEST 3: CONTEXT INTEGRATION WITH SYSTEM PROMPT ===")
        
        # Create thread
        success, response = self.make_request('POST', '/mission_control/threads', {
            "title": "System Prompt Integration Test"
        })
        
        if not success or response.status_code != 200:
            self.log_result('system_prompt_integration', False, 'Failed to create thread')
            return
            
        thread_id = response.json().get('thread_id')
        
        # Send message that should trigger system prompt behavior
        success, response = self.make_request('POST', '/mission_control/message', {
            "thread_id": thread_id,
            "text": "Let's plan Operation Market Intelligence to identify Praetoria's ideal customers"
        })
        
        if not (success and response.status_code == 200):
            self.log_result('system_prompt_integration', False, 'Failed to send initial message')
            return
        
        initial_response = response.json().get('assistant', {}).get('text', '')
        
        # Test if system prompt context awareness works
        success, response = self.make_request('POST', '/mission_control/message', {
            "thread_id": thread_id,
            "text": "What operation are we planning based on our conversation?"
        })
        
        if success and response.status_code == 200:
            context_response = response.json().get('assistant', {}).get('text', '').lower()
            
            # Check for system prompt integration indicators
            integration_indicators = [
                'market intelligence',
                'operation',
                'conversation',
                'discussed',
                'planning',
                'praetoria'
            ]
            
            found_indicators = [ind for ind in integration_indicators if ind in context_response]
            integration_score = len(found_indicators) / len(integration_indicators)
            
            # Also check that it doesn't give generic responses
            generic_indicators = [
                "we haven't actually defined",
                "haven't discussed any operation",
                "no operation defined"
            ]
            
            shows_generic_response = any(ind in context_response for ind in generic_indicators)
            
            if integration_score >= 0.5 and not shows_generic_response:
                self.log_result('system_prompt_integration', True,
                              'System prompt integrates properly with conversation history',
                              {
                                  'integration_score': f"{integration_score:.2f}",
                                  'found_indicators': found_indicators,
                                  'shows_generic_response': shows_generic_response,
                                  'response_preview': context_response[:200]
                              })
            else:
                self.log_result('system_prompt_integration', False,
                              'System prompt does not integrate properly with conversation history',
                              {
                                  'integration_score': f"{integration_score:.2f}",
                                  'shows_generic_response': shows_generic_response,
                                  'response_preview': context_response[:200]
                              })
        else:
            self.log_result('system_prompt_integration', False, 'Failed to get context response')

    def test_multiple_thread_isolation(self):
        """Test: Ensure different threads maintain separate contexts"""
        print("\n=== TEST 4: MULTIPLE THREAD ISOLATION ===")
        
        # Create two separate threads
        thread_data = []
        for i in range(2):
            success, response = self.make_request('POST', '/mission_control/threads', {
                "title": f"Isolation Test Thread {i+1}"
            })
            
            if success and response.status_code == 200:
                thread_id = response.json().get('thread_id')
                thread_data.append(thread_id)
            else:
                self.log_result('thread_isolation', False, f'Failed to create thread {i+1}')
                return
        
        # Send different context to each thread
        contexts = [
            {
                'thread_id': thread_data[0],
                'operation': 'Operation Alpha',
                'target': 'financial services',
                'platform': 'LinkedIn'
            },
            {
                'thread_id': thread_data[1], 
                'operation': 'Operation Beta',
                'target': 'healthcare companies',
                'platform': 'Twitter'
            }
        ]
        
        # Build context in each thread
        for ctx in contexts:
            success, response = self.make_request('POST', '/mission_control/message', {
                "thread_id": ctx['thread_id'],
                "text": f"We're planning {ctx['operation']} to target {ctx['target']} using {ctx['platform']}"
            })
            
            if not (success and response.status_code == 200):
                self.log_result('thread_isolation', False, f'Failed to send context to thread')
                return
            
            time.sleep(1)
        
        # Test isolation by asking each thread about its context
        isolation_working = True
        for i, ctx in enumerate(contexts):
            success, response = self.make_request('POST', '/mission_control/message', {
                "thread_id": ctx['thread_id'],
                "text": "What operation are we planning and who are we targeting?"
            })
            
            if success and response.status_code == 200:
                response_text = response.json().get('assistant', {}).get('text', '').lower()
                
                # Check if response contains correct context for this thread
                correct_elements = [
                    ctx['operation'].lower(),
                    ctx['target'].lower(),
                    ctx['platform'].lower()
                ]
                
                # Check if response contains incorrect context from other thread
                other_ctx = contexts[1-i]  # Get the other thread's context
                incorrect_elements = [
                    other_ctx['operation'].lower(),
                    other_ctx['target'].lower(),
                    other_ctx['platform'].lower()
                ]
                
                correct_found = sum(1 for elem in correct_elements if elem in response_text)
                incorrect_found = sum(1 for elem in incorrect_elements if elem in response_text)
                
                print(f"Thread {i+1}: {correct_found}/3 correct elements, {incorrect_found}/3 incorrect elements")
                
                if correct_found < 2 or incorrect_found > 0:
                    isolation_working = False
            else:
                isolation_working = False
        
        if isolation_working:
            self.log_result('thread_isolation', True,
                          'Thread contexts are properly isolated',
                          {'thread_1': thread_data[0], 'thread_2': thread_data[1]})
        else:
            self.log_result('thread_isolation', False,
                          'Thread contexts are not properly isolated',
                          {'thread_1': thread_data[0], 'thread_2': thread_data[1]})

    def run_verification(self):
        """Run all verification tests"""
        print("CRITICAL BUG FIX VERIFICATION - CONTEXT MANAGEMENT SUCCESS")
        print("=" * 80)
        print("Testing the specific scenarios mentioned in the review request:")
        print("1. Thread Conversation Continuity")
        print("2. Operation Context Persistence") 
        print("3. Context Integration with SYSTEM_PROMPT")
        print("4. Multiple Thread Isolation")
        print("=" * 80)
        
        start_time = time.time()
        
        # Run all tests
        self.test_thread_conversation_continuity()
        self.test_operation_context_persistence()
        self.test_context_integration_with_system_prompt()
        self.test_multiple_thread_isolation()
        
        total_duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 80)
        print("CONTEXT FIX VERIFICATION SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - passed
        
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.results)*100):.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED - CONTEXT BUG FIX VERIFIED!")
            print("✅ Thread conversation continuity working")
            print("✅ Operation context persistence working")
            print("✅ Context integration with SYSTEM_PROMPT working")
            print("✅ Multiple thread isolation working")
        else:
            print(f"\n⚠️  {failed} TEST(S) FAILED:")
            for result in self.results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['message']}")
        
        return self.results, passed, failed

if __name__ == "__main__":
    verifier = ContextFixVerifier()
    results, passed, failed = verifier.run_verification()