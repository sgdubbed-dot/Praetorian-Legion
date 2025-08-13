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

class PraefectusContextBugTester:
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

    def test_basic_health_check(self):
        """Test basic health endpoints to ensure API is working"""
        print("\n=== TESTING BASIC HEALTH CHECK ===")
        
        # Test GET /api/health
        success, response, duration = self.make_request('GET', '/health')
        if success and response.status_code == 200:
            try:
                data = response.json()
                self.log_result('health_endpoint', True, 
                              f'Health endpoint working: {data}', 
                              data, duration)
            except:
                self.log_result('health_endpoint', False, 'Health endpoint returned invalid JSON', None, duration)
        else:
            self.log_result('health_endpoint', False, 
                          f'Health endpoint failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def test_thread_creation_and_messaging(self):
        """Test basic thread creation and messaging functionality"""
        print("\n=== TESTING THREAD CREATION AND MESSAGING ===")
        
        # Create a thread for testing
        test_thread = {
            "title": "Operation Market Cartography"
        }
        
        success, response, duration = self.make_request('POST', '/mission_control/threads', test_thread)
        if not success or response.status_code != 200:
            self.log_result('thread_creation', False, 
                          f'Thread creation failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return None
        
        try:
            created_thread = response.json()
            thread_id = created_thread.get('thread_id')
            if not thread_id:
                self.log_result('thread_creation', False, 'Thread creation missing thread_id', created_thread, duration)
                return None
            
            self.test_data['thread_id'] = thread_id
            self.log_result('thread_creation', True, 
                          f'Thread created successfully: {thread_id}', 
                          created_thread, duration)
            
            return thread_id
            
        except Exception as e:
            self.log_result('thread_creation', False, f'JSON parse error: {e}', None, duration)
            return None

    def send_message_to_thread(self, thread_id: str, message_text: str, test_name: str) -> Optional[str]:
        """Send a message to a thread and return the assistant's response"""
        test_message = {
            "thread_id": thread_id,
            "text": message_text
        }
        
        success, response, duration = self.make_request('POST', '/mission_control/message', test_message)
        if success and response.status_code == 200:
            try:
                message_response = response.json()
                assistant_text = message_response.get('assistant', {}).get('text', '')
                
                if not assistant_text:
                    self.log_result(test_name, False, 
                                  'Praefectus did not respond to message', 
                                  message_response, duration)
                    return None
                
                self.log_result(test_name, True, 
                              f'Message sent and response received: {len(assistant_text)} chars', 
                              {
                                  'message_sent': message_text,
                                  'response_length': len(assistant_text),
                                  'response_preview': assistant_text[:200] + '...' if len(assistant_text) > 200 else assistant_text
                              }, duration)
                
                return assistant_text
                
            except Exception as e:
                self.log_result(test_name, False, f'JSON parse error: {e}', None, duration)
                return None
        else:
            self.log_result(test_name, False, 
                          f'Message sending failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
            return None

    def get_thread_messages(self, thread_id: str) -> Optional[List[Dict]]:
        """Get all messages from a thread"""
        success, response, duration = self.make_request('GET', f'/mission_control/thread/{thread_id}')
        if success and response.status_code == 200:
            try:
                thread_data = response.json()
                messages = thread_data.get('messages', [])
                return messages
            except Exception as e:
                print(f"Error getting thread messages: {e}")
                return None
        else:
            print(f"Failed to get thread messages: {response.status_code if hasattr(response, 'status_code') else response}")
            return None

    def test_critical_context_bug(self):
        """Test the CRITICAL CONTEXT BUG - Praefectus not reading conversation history"""
        print("\n=== TESTING CRITICAL CONTEXT BUG ===")
        print("REPRODUCING USER REPORTED BUG:")
        print("1. Create thread 'Operation Market Cartography'")
        print("2. Send message about identifying target market for Praetoria")
        print("3. Ask 'Tell me about the operation we are building'")
        print("4. Verify if Praefectus references previous conversation")
        
        # Step 1: Create thread
        thread_id = self.test_thread_creation_and_messaging()
        if not thread_id:
            return
        
        # Step 2: Send initial message about market cartography
        initial_message = "I need to identify our target market for Praetoria. Focus on GitHub repositories and Discord communities"
        
        print(f"\n--- Sending initial message ---")
        print(f"Message: {initial_message}")
        
        initial_response = self.send_message_to_thread(
            thread_id, 
            initial_message, 
            'initial_market_message'
        )
        
        if not initial_response:
            self.log_result('context_bug_test', False, 'Failed to send initial message', None, 0)
            return
        
        # Check if initial response mentions Operation Market Cartography
        initial_response_lower = initial_response.lower()
        mentions_operation = any(phrase in initial_response_lower for phrase in [
            'operation market cartography', 'market cartography', 'cartography'
        ])
        
        print(f"Initial response mentions operation: {mentions_operation}")
        print(f"Initial response preview: {initial_response[:300]}...")
        
        # Step 3: Wait a moment then ask about "the operation we are building"
        time.sleep(2)
        
        context_test_message = "Tell me about the operation we are building"
        
        print(f"\n--- Testing context awareness ---")
        print(f"Message: {context_test_message}")
        
        context_response = self.send_message_to_thread(
            thread_id,
            context_test_message,
            'context_awareness_test'
        )
        
        if not context_response:
            self.log_result('context_bug_test', False, 'Failed to send context test message', None, 0)
            return
        
        # Step 4: Analyze the context response for the bug
        context_response_lower = context_response.lower()
        
        # Check for the specific bug indicators
        bug_indicators = [
            "we haven't actually defined any operation",
            "haven't defined any operation yet",
            "no operation defined",
            "haven't discussed any operation"
        ]
        
        shows_bug = any(indicator in context_response_lower for indicator in bug_indicators)
        
        # Check for proper context awareness
        context_indicators = [
            'operation market cartography',
            'market cartography', 
            'cartography',
            'target market',
            'praetoria',
            'github repositories',
            'discord communities',
            'discussed above',
            'conversation above',
            'based on our discussion'
        ]
        
        shows_context_awareness = any(indicator in context_response_lower for indicator in context_indicators)
        
        # Get thread messages to verify conversation history exists
        messages = self.get_thread_messages(thread_id)
        message_count = len(messages) if messages else 0
        
        print(f"\n--- CONTEXT BUG ANALYSIS ---")
        print(f"Thread has {message_count} messages")
        print(f"Shows bug indicators: {shows_bug}")
        print(f"Shows context awareness: {shows_context_awareness}")
        print(f"Context response preview: {context_response[:400]}...")
        
        # Determine if the bug exists
        if shows_bug and not shows_context_awareness:
            self.log_result('context_bug_verification', False, 
                          'CRITICAL CONTEXT BUG CONFIRMED: Praefectus does not read conversation history within threads', 
                          {
                              'thread_id': thread_id,
                              'message_count': message_count,
                              'shows_bug_indicators': shows_bug,
                              'shows_context_awareness': shows_context_awareness,
                              'bug_indicators_found': [ind for ind in bug_indicators if ind in context_response_lower],
                              'context_indicators_found': [ind for ind in context_indicators if ind in context_response_lower],
                              'initial_response_preview': initial_response[:200] + '...' if len(initial_response) > 200 else initial_response,
                              'context_response_preview': context_response[:200] + '...' if len(context_response) > 200 else context_response
                          }, 0)
        elif shows_context_awareness and not shows_bug:
            self.log_result('context_bug_verification', True, 
                          'Context bug appears to be FIXED: Praefectus demonstrates conversation awareness', 
                          {
                              'thread_id': thread_id,
                              'message_count': message_count,
                              'shows_bug_indicators': shows_bug,
                              'shows_context_awareness': shows_context_awareness,
                              'context_indicators_found': [ind for ind in context_indicators if ind in context_response_lower],
                              'context_response_preview': context_response[:200] + '...' if len(context_response) > 200 else context_response
                          }, 0)
        else:
            self.log_result('context_bug_verification', False, 
                          'INCONCLUSIVE: Mixed signals in context awareness testing', 
                          {
                              'thread_id': thread_id,
                              'message_count': message_count,
                              'shows_bug_indicators': shows_bug,
                              'shows_context_awareness': shows_context_awareness,
                              'bug_indicators_found': [ind for ind in bug_indicators if ind in context_response_lower],
                              'context_indicators_found': [ind for ind in context_indicators if ind in context_response_lower],
                              'context_response_preview': context_response[:200] + '...' if len(context_response) > 200 else context_response
                          }, 0)

    def test_conversation_persistence_within_thread(self):
        """Test if Praefectus can reference multiple previous messages in the same thread"""
        print("\n=== TESTING CONVERSATION PERSISTENCE WITHIN THREAD ===")
        
        thread_id = self.test_data.get('thread_id')
        if not thread_id:
            # Create a new thread for this test
            test_thread = {"title": "Context Persistence Test"}
            success, response, duration = self.make_request('POST', '/mission_control/threads', test_thread)
            if success and response.status_code == 200:
                thread_id = response.json().get('thread_id')
                self.test_data['persistence_thread_id'] = thread_id
            else:
                self.log_result('conversation_persistence', False, 'Failed to create thread for persistence test', None, 0)
                return
        
        # Send a series of messages building context
        messages_sequence = [
            "Our mission is to build a stealth intelligence operation called Operation Shadow Network.",
            "The primary target is enterprise security teams who need agent monitoring solutions.",
            "We'll focus on three key platforms: GitHub for developer outreach, LinkedIn for enterprise contacts, and Discord for community building.",
            "The timeline is 6 weeks with weekly progress reviews."
        ]
        
        # Send each message and get responses
        for i, message in enumerate(messages_sequence):
            print(f"\n--- Sending context message {i+1} ---")
            response = self.send_message_to_thread(
                thread_id,
                message,
                f'context_building_message_{i+1}'
            )
            if not response:
                self.log_result('conversation_persistence', False, f'Failed to send context message {i+1}', None, 0)
                return
            time.sleep(1)  # Small delay between messages
        
        # Now test if Praefectus can summarize the entire conversation
        summary_request = "Please summarize everything we've discussed about our operation, including the name, targets, platforms, and timeline."
        
        print(f"\n--- Testing conversation summary ---")
        summary_response = self.send_message_to_thread(
            thread_id,
            summary_request,
            'conversation_summary_test'
        )
        
        if not summary_response:
            self.log_result('conversation_persistence', False, 'Failed to get conversation summary', None, 0)
            return
        
        # Check if the summary includes elements from all previous messages
        summary_lower = summary_response.lower()
        
        expected_elements = [
            'operation shadow network',  # From message 1
            'enterprise security',       # From message 2  
            'github',                   # From message 3
            'linkedin',                 # From message 3
            'discord',                  # From message 3
            '6 weeks',                  # From message 4
            'weekly'                    # From message 4
        ]
        
        found_elements = [elem for elem in expected_elements if elem in summary_lower]
        missing_elements = [elem for elem in expected_elements if elem not in summary_lower]
        
        # Get thread messages to verify conversation history
        messages = self.get_thread_messages(thread_id)
        message_count = len(messages) if messages else 0
        
        persistence_score = len(found_elements) / len(expected_elements)
        persistence_working = persistence_score >= 0.6  # At least 60% of elements should be found
        
        print(f"\n--- CONVERSATION PERSISTENCE ANALYSIS ---")
        print(f"Thread has {message_count} messages")
        print(f"Found {len(found_elements)}/{len(expected_elements)} expected elements")
        print(f"Persistence score: {persistence_score:.2f}")
        print(f"Missing elements: {missing_elements}")
        print(f"Summary preview: {summary_response[:300]}...")
        
        if persistence_working:
            self.log_result('conversation_persistence', True, 
                          f'Conversation persistence WORKING: {len(found_elements)}/{len(expected_elements)} elements found in summary', 
                          {
                              'thread_id': thread_id,
                              'message_count': message_count,
                              'persistence_score': persistence_score,
                              'found_elements': found_elements,
                              'missing_elements': missing_elements,
                              'summary_preview': summary_response[:300] + '...' if len(summary_response) > 300 else summary_response
                          }, 0)
        else:
            self.log_result('conversation_persistence', False, 
                          f'Conversation persistence BROKEN: Only {len(found_elements)}/{len(expected_elements)} elements found in summary', 
                          {
                              'thread_id': thread_id,
                              'message_count': message_count,
                              'persistence_score': persistence_score,
                              'found_elements': found_elements,
                              'missing_elements': missing_elements,
                              'summary_preview': summary_response[:300] + '...' if len(summary_response) > 300 else summary_response
                          }, 0)

    def test_terminology_changes_verification(self):
        """Verify that the Mission→Operation terminology changes are working"""
        print("\n=== TESTING TERMINOLOGY CHANGES VERIFICATION ===")
        
        # Test operations endpoint (should work with new terminology)
        success, response, duration = self.make_request('GET', '/operations')
        if success and response.status_code == 200:
            self.log_result('operations_endpoint', True, 
                          'Operations endpoint working (terminology change successful)', 
                          {'endpoint': '/api/operations'}, duration)
        else:
            self.log_result('operations_endpoint', False, 
                          f'Operations endpoint failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)
        
        # Test creating an operation
        test_operation = {
            "title": "Test Operation for Terminology Verification",
            "objective": "Verify that operation creation works with new terminology",
            "posture": "research_only"
        }
        
        success, response, duration = self.make_request('POST', '/operations', test_operation)
        if success and response.status_code == 200:
            try:
                created_operation = response.json()
                operation_id = created_operation.get('id')
                self.test_data['test_operation_id'] = operation_id
                self.log_result('operation_creation', True, 
                              f'Operation creation successful: {operation_id}', 
                              created_operation, duration)
            except Exception as e:
                self.log_result('operation_creation', False, f'JSON parse error: {e}', None, duration)
        else:
            self.log_result('operation_creation', False, 
                          f'Operation creation failed: {response.status_code if hasattr(response, "status_code") else response}', 
                          None, duration)

    def run_context_bug_verification_test(self):
        """Run comprehensive context bug verification test"""
        print(f"Starting Praefectus Context Bug Verification - Base URL: {API_BASE}")
        print("=" * 100)
        print("CRITICAL BUG VERIFICATION: Praefectus conversation context management")
        print("USER REPORTED: Praefectus doesn't read conversation history within threads")
        print("=" * 100)
        
        start_time = time.time()
        
        # Run test suites in order
        self.test_basic_health_check()
        self.test_terminology_changes_verification()
        self.test_critical_context_bug()
        self.test_conversation_persistence_within_thread()
        
        total_duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 100)
        print("PRAEFECTUS CONTEXT BUG VERIFICATION SUMMARY")
        print("=" * 100)
        
        passed = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - passed
        
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.results)*100):.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")
        
        # Categorize results
        context_tests = [r for r in self.results if 'context' in r['test'] or 'persistence' in r['test']]
        terminology_tests = [r for r in self.results if 'operation' in r['test'] or 'terminology' in r['test']]
        
        print(f"\nCONTEXT BUG TESTS: {sum(1 for r in context_tests if r['success'])}/{len(context_tests)} passed")
        print(f"TERMINOLOGY TESTS: {sum(1 for r in terminology_tests if r['success'])}/{len(terminology_tests)} passed")
        
        # Critical bug analysis
        context_bug_test = next((r for r in self.results if r['test'] == 'context_bug_verification'), None)
        persistence_test = next((r for r in self.results if r['test'] == 'conversation_persistence'), None)
        
        print(f"\n🔍 CRITICAL BUG STATUS:")
        if context_bug_test:
            if context_bug_test['success']:
                print("✅ CONTEXT BUG APPEARS TO BE FIXED")
                print("   Praefectus demonstrates conversation awareness within threads")
            else:
                print("❌ CONTEXT BUG CONFIRMED - STILL PRESENT")
                print("   Praefectus does NOT read conversation history within threads")
                print("   This matches the user's reported issue exactly")
        
        if persistence_test:
            if persistence_test['success']:
                print("✅ CONVERSATION PERSISTENCE WORKING")
            else:
                print("❌ CONVERSATION PERSISTENCE BROKEN")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['message']}")
        
        # Test data summary
        if self.test_data:
            print(f"\nTEST DATA CREATED:")
            for key, value in self.test_data.items():
                if isinstance(value, str):
                    print(f"- {key}: {value}")
        
        return self.results, passed, failed

if __name__ == "__main__":
    tester = PraefectusContextBugTester()
    results, passed, failed = tester.run_context_bug_verification_test()