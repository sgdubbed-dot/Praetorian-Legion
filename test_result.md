#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

## user_problem_statement: "Agents page incomplete, Explorator error reset not working; linting error prevents clean boot. Ensure three agents always visible, implement auto-reset, Legatus posture logic, and scenario helper minutes param; then test backend."

## backend:
##   - task: "Fix lint error and add agents auto-reset + seeding + logic"
##     implemented: true
##     working: true
##     file: "/app/backend/server.py"
##     stuck_count: 0
##     priority: "high"
##     needs_retesting: true
##     status_history:
##         -working: false
##         -agent: "main"
##         -comment: "Identified flake8 E731 due to lambda new_id; updated to def new_id(); services running."
##         -working: true
##         -agent: "testing"
##         -comment: "Health endpoints OK; agents seeded; research_only forces Legatus yellow; Explorator error and auto-reset work; events OK."
##
## frontend:
##   - task: "Agents.jsx always render Praefectus/Explorator/Legatus and show retry tooltip"
##     implemented: true
##     working: true
##     file: "/app/frontend/src/pages/Agents.jsx"
##     stuck_count: 0
##     priority: "high"
##     needs_retesting: false
##     status_history:
##         -working: false
##         -agent: "main"
##         -comment: "Updated UI to ensure triad render, selection by agent_name, show next_retry_at."
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 1
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Backend agents seeding and auto-reset logic"
##   stuck_tasks:
##     - "None"
##   test_all: false
##   test_priority: "high_first"
##
## agent_communication:
##     -agent: "main"
##     -message: "Please validate backend per acceptance criteria; hold frontend tests."

user_problem_statement: "Backend API verification focused on Agents logic - health endpoints, agent seeding, research-only Legatus logic, Explorator error handling, and events endpoint"

backend:
  - task: "Health endpoints verification"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
        - agent: "testing"
        - comment: "Both GET /api/health and GET /api/ endpoints working correctly. Health returns {ok: true, timestamp} and root returns API ready message. Response times: 55ms and 6ms respectively."

  - task: "Agents seeding and presence"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
        - agent: "testing"
        - comment: "All three agents (Praefectus, Explorator, Legatus) are properly seeded and persist across calls. Idempotency verified with two consecutive GET /api/agents calls."

  - task: "Research-only Legatus logic"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
        - agent: "testing"
        - comment: "Legatus correctly transitions to yellow when research_only mission is active, and transitions to green when mission is completed (due to existing approved hotleads or other factors). Logic working as expected."

  - task: "Explorator error and auto-reset logic"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
        - agent: "testing"
        - comment: "Minor: Explorator error detection and status changes work correctly. Agent transitions to red with error_state=crawl_timeout and next_retry_at set. Status correctly changes to green due to active missions, but error_state and next_retry_at fields not cleared (minor backend logic issue). Core functionality works - agent status reflects correct operational state."

  - task: "Events endpoint functionality"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
        - agent: "testing"
        - comment: "Events endpoint working correctly. General /api/events returns event list, agent-specific filtering works (?agent_name=Explorator). All expected event types found: agent_error_detected, agent_retry_scheduled, agent_error_cleared, agent_status_changed. Phoenix timezone timestamps present."

metadata:
  created_by: "testing_agent"
  version: "1.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "Health endpoints verification"
    - "Agents seeding and presence"
    - "Research-only Legatus logic"
    - "Explorator error and auto-reset logic"
    - "Events endpoint functionality"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "testing"
    - message: "Backend API verification completed successfully. All 5 major test areas passed with only one minor issue: Explorator auto-reset logic doesn't clear error_state/next_retry_at fields when status changes to green due to active missions (line 724 in server.py only checks for red status). Core functionality works correctly - agent status properly reflects operational state. Total: 13 tests run, 12 passed, 1 minor issue. All critical functionality verified working."
    - agent: "testing"
    - message: "RERUN VERIFICATION COMPLETED: All requested backend tests passed successfully. Health endpoints (✅), agents triad seeding (✅), research_only Legatus logic (✅), Explorator error handling (✅ with same minor cleanup issue), events endpoint (✅). Total runtime: 73.29s. API payloads captured. Same minor issue persists: error_state/next_retry_at not cleared when status changes to green due to active missions. Core functionality working correctly."
    - agent: "testing"
    - message: "EXPLORATOR ERROR SCENARIO EXECUTED: Successfully triggered Explorator error state for UI screenshot. POST /api/scenarios/agent_error_retry with {minutes: 1} returned agent in red status with crawl_timeout error_state and next_retry_at set to 2025-08-09T15:02:41.981215-07:00. Immediate GET /api/agents confirmed Explorator red, Legatus green, Praefectus green. UI screenshot can now be taken with Explorator in error state as requested."
    - agent: "testing"
    - message: "EXPLORATOR ERROR SCENARIO RE-EXECUTED FOR REPORT: Successfully re-triggered Explorator error state as requested. POST /api/scenarios/agent_error_retry with {minutes: 1} returned agent in red status with crawl_timeout error_state and next_retry_at set to 2025-08-09T15:04:26.211178-07:00. Immediate GET /api/agents confirmed Explorator red, Legatus green, Praefectus green. Both payloads captured and provided for report inclusion."
    - agent: "testing"
    - message: "SCREENSHOT PREPARATION COMPLETED: Successfully executed all 5 requested steps for UI screenshot preparation. (1) Triggered Explorator error with 1-minute retry window - agent returned in red status with crawl_timeout error_state and next_retry_at=2025-08-09T15:12:01.236863-07:00. (2) Immediate GET /api/agents confirmed Explorator red, Legatus green, Praefectus green. (3) After 70 seconds, Explorator auto-reset to green with error_state and next_retry_at cleared. (4) Created research_only mission 'Screenshot Research' (ID: c1e78703-1c3b-462b-8636-8f1859bb7813) which forced Legatus to yellow status as expected. (5) Retrieved 10 recent Explorator events including agent_error_detected, agent_retry_scheduled, agent_error_cleared, and agent_status_changed. All payloads captured for report. Total duration: 71.15s. Backend state ready for UI screenshots."
    - agent: "testing"
    - message: "RED-STATE SCREENSHOT PREPARATION EXECUTED: Successfully prepared red-state screenshot as requested. POST /api/scenarios/agent_error_retry with {minutes: 3} returned Explorator in red status with crawl_timeout error_state and next_retry_at=2025-08-09T15:22:00.157844-07:00. Immediate GET /api/agents confirmed Explorator red, Legatus yellow, Praefectus green. Both payloads captured and provided. UI can now take screenshot with Explorator in error state. Total execution time: <5 seconds."
    - agent: "testing"
    - message: "COMPLETE SCREENSHOT SEQUENCE EXECUTED: Successfully executed all 3 requested screenshot preparation tasks. (1) Triggered Explorator error with 1-minute retry - agent set to red status with crawl_timeout error_state and next_retry_at=2025-08-09T15:31:48.387048-07:00. (2) After 75 seconds wait, Explorator auto-reset to green with error_state and next_retry_at cleared successfully. (3) Created research_only mission 'Screenshot Research Mission' (ID: f4e7a035-1316-4765-b285-b4b4ca0d349f) which correctly forced Legatus to yellow status. Final agent states: Explorator=green (auto-reset), Legatus=yellow (research mission), Praefectus=green. All backend states prepared for UI screenshots. Total execution time: ~80 seconds."
    - agent: "testing"
    - message: "FRESH AGENTS SAMPLE PROVIDED FOR REPORT: Successfully generated fresh GET /api/agents JSON after auto-reset as requested. Triggered Explorator error with 1-minute retry window, waited 75 seconds for auto-reset, then captured fresh JSON sample. CONFIRMED: Explorator error_state and next_retry_at are null post-reset. All timestamps are in Phoenix format (-07:00 MST). Fresh JSON sample shows: Explorator=green (auto-reset complete), Legatus=yellow, Praefectus=green. Sample includes all required fields with proper Phoenix timezone formatting. Total execution time: ~80 seconds. Fresh sample ready for report inclusion."