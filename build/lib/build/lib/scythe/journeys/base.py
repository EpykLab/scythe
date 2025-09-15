from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from selenium.webdriver.remote.webdriver import WebDriver
import time
import logging

if TYPE_CHECKING:
    from ..auth.base import Authentication


class Action(ABC):
    """
    Abstract base class for individual actions within a journey step.
    
    Actions are the smallest unit of work in a journey and can include
    things like clicking buttons, filling forms, navigating to URLs,
    or executing TTPs.
    """
    
    def __init__(self, name: str, description: str, expected_result: bool = True):
        """
        Initialize an action.
        
        Args:
            name: Name of the action
            description: Description of what this action does
            expected_result: Whether this action is expected to succeed
        """
        self.name = name
        self.description = description
        self.expected_result = expected_result
        self.execution_data = {}
    
    @abstractmethod
    def execute(self, driver: WebDriver, context: Dict[str, Any]) -> bool:
        """
        Execute the action.
        
        Args:
            driver: WebDriver instance
            context: Shared context data between actions
            
        Returns:
            True if action succeeded, False otherwise
        """
        pass
    
    def validate_prerequisites(self, context: Dict[str, Any]) -> bool:
        """
        Validate that prerequisites for this action are met.
        
        Args:
            context: Shared context data
            
        Returns:
            True if prerequisites are met, False otherwise
        """
        return True
    
    def store_result(self, key: str, value: Any) -> None:
        """Store execution result data."""
        self.execution_data[key] = value
    
    def get_result(self, key: str, default: Any = None) -> Any:
        """Retrieve execution result data."""
        return self.execution_data.get(key, default)


class Step:
    """
    A step in a journey, containing one or more actions.
    
    Steps represent logical groupings of actions that accomplish
    a specific goal within the larger journey.
    """
    
    def __init__(self, 
                 name: str, 
                 description: str, 
                 actions: Optional[List[Action]] = None,
                 continue_on_failure: bool = False,
                 expected_result: bool = True):
        """
        Initialize a step.
        
        Args:
            name: Name of the step
            description: Description of what this step accomplishes
            actions: List of actions to execute in this step
            continue_on_failure: Whether to continue if an action fails
            expected_result: Whether this step is expected to succeed
        """
        self.name = name
        self.description = description
        self.actions = actions or []
        self.continue_on_failure = continue_on_failure
        self.expected_result = expected_result
        self.execution_results = []
        self.step_data = {}
    
    def add_action(self, action: Action) -> None:
        """Add an action to this step."""
        self.actions.append(action)
    
    def execute(self, driver: WebDriver|None, context: Dict[str, Any]) -> bool:
        """
        Execute all actions in this step.
        
        Args:
            driver: WebDriver instance
            context: Shared context data
            
        Returns:
            True if a step succeeded, False otherwise
        """
        logger = logging.getLogger(f"Journey.Step.{self.name}")
        logger.info(f"Executing step: {self.name}")
        logger.info(f"Description: {self.description}")
        
        success_count = 0
        failure_count = 0
        
        for i, action in enumerate(self.actions, 1):
            logger.info(f"Action {i}/{len(self.actions)}: {action.name}")
            
            try:
                # Validate prerequisites
                if not action.validate_prerequisites(context):
                    logger.warning(f"Prerequisites not met for action: {action.name}")
                    if not self.continue_on_failure:
                        return False
                    failure_count += 1
                    continue
                
                # Execute action
                result = action.execute(driver, context)
                
                # Store result
                details = getattr(action, 'execution_data', {})
                action_result = {
                    'action_name': action.name,
                    'action_description': action.description,
                    'expected': action.expected_result,
                    'actual': result,
                    'timestamp': time.time(),
                    'details': details.copy() if isinstance(details, dict) else {}
                }
                self.execution_results.append(action_result)
                
                # Log result
                if result:
                    if action.expected_result:
                        logger.info(f"✓ Action succeeded: {action.name}")
                        success_count += 1
                    else:
                        logger.warning(f"✗ Action unexpectedly succeeded: {action.name}")
                        success_count += 1
                else:
                    if action.expected_result:
                        logger.error(f"✗ Action failed: {action.name}")
                        # Emit diagnostic details when available (e.g., for API requests)
                        try:
                            ad = action_result.get('details', {}) or {}
                            method = ad.get('request_method') or getattr(action, 'method', None)
                            url = ad.get('url') or getattr(action, 'url', None)
                            status = ad.get('status_code')
                            dur = ad.get('duration_ms')
                            if method or url or status is not None:
                                parts = []
                                if method:
                                    parts.append(f"method={method}")
                                if url:
                                    parts.append(f"url={url}")
                                if status is not None:
                                    parts.append(f"status={status}")
                                if dur is not None:
                                    parts.append(f"duration_ms={dur}")
                                logger.error("    Details: " + ", ".join(parts))
                            req_headers = ad.get('request_headers')
                            if req_headers:
                                logger.error(f"    Request headers: {req_headers}")
                            req_params = ad.get('request_params')
                            if req_params:
                                logger.error(f"    Request params: {req_params}")
                            req_json = ad.get('request_json')
                            if req_json is not None:
                                logger.error(f"    Request JSON: {req_json}")
                            req_data = ad.get('request_data')
                            if req_data is not None:
                                logger.error(f"    Request data: {req_data}")
                            resp_headers = ad.get('response_headers')
                            if resp_headers:
                                logger.error(f"    Response headers: {resp_headers}")
                            if 'response_json' in ad:
                                logger.error(f"    Response JSON: {ad.get('response_json')}")
                            elif 'response_text' in ad:
                                logger.error(f"    Response text: {ad.get('response_text')}")
                            if ad.get('error'):
                                logger.error(f"    Error: {ad.get('error')}")
                        except Exception:
                            pass
                        failure_count += 1
                        if not self.continue_on_failure:
                            return False
                    else:
                        logger.info(f"✓ Action failed as expected: {action.name}")
                        success_count += 1
                
            except Exception as e:
                logger.error(f"Exception in action {action.name}: {str(e)}")
                # Emit any available diagnostics even on exceptions
                try:
                    details = getattr(action, 'execution_data', {}) or {}
                    if details:
                        method = details.get('request_method') or getattr(action, 'method', None)
                        url = details.get('url') or getattr(action, 'url', None)
                        status = details.get('status_code')
                        dur = details.get('duration_ms')
                        parts = []
                        if method:
                            parts.append(f"method={method}")
                        if url:
                            parts.append(f"url={url}")
                        if status is not None:
                            parts.append(f"status={status}")
                        if dur is not None:
                            parts.append(f"duration_ms={dur}")
                        if parts:
                            logger.error("    Details: " + ", ".join(parts))
                        if details.get('request_headers'):
                            logger.error(f"    Request headers: {details.get('request_headers')}")
                        if details.get('response_headers'):
                            logger.error(f"    Response headers: {details.get('response_headers')}")
                        if 'response_json' in details:
                            logger.error(f"    Response JSON: {details.get('response_json')}")
                        elif 'response_text' in details:
                            logger.error(f"    Response text: {details.get('response_text')}")
                except Exception:
                    pass
                failure_count += 1
                if not self.continue_on_failure:
                    return False
        
        # Determine step success
        step_success = failure_count == 0 or (self.continue_on_failure and success_count > 0)
        
        logger.info(f"Step completed: {success_count} successes, {failure_count} failures")
        return step_success
    
    def store_data(self, key: str, value: Any) -> None:
        """Store step-specific data."""
        self.step_data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve step-specific data."""
        return self.step_data.get(key, default)


class Journey:
    """
    A journey represents a complete test scenario composed of multiple steps.
    
    Journeys provide a high-level abstraction for complex testing workflows
    that may include authentication, navigation, data entry, and verification.
    """
    
    def __init__(self, 
                 name: str, 
                 description: str, 
                 steps: Optional[List[Step]] = None,
                 expected_result: bool = True,
                 authentication: Optional['Authentication'] = None):
        """
        Initialize a journey.
        
        Args:
            name: Name of the journey
            description: Description of what this journey tests
            steps: List of steps to execute in this journey
            expected_result: Whether this journey is expected to succeed overall
            authentication: Optional authentication to perform before journey
        """
        self.name = name
        self.description = description
        self.steps = steps or []
        self.expected_result = expected_result
        self.authentication = authentication
        self.context = {}  # Shared data between steps
        self.execution_results = []
        self.journey_data = {}
    
    def add_step(self, step: Step) -> None:
        """Add a step to this journey."""
        self.steps.append(step)
    
    def set_context(self, key: str, value: Any) -> None:
        """Set shared context data."""
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get shared context data."""
        return self.context.get(key, default)
    
    def clear_context(self) -> None:
        """Clear all context data."""
        self.context.clear()
    
    def requires_authentication(self) -> bool:
        """Check if this journey requires authentication."""
        return self.authentication is not None
    
    def authenticate(self, driver: WebDriver, target_url: str) -> bool:
        """
        Perform authentication if required.
        
        Args:
            driver: WebDriver instance
            target_url: Target URL for authentication
            
        Returns:
            True if authentication successful or not required
        """
        if not self.requires_authentication():
            return True
        
        try:
            if self.authentication:
                return self.authentication.authenticate(driver, target_url)
            return False
        except Exception as e:
            logger = logging.getLogger(f"Journey.{self.name}")
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def execute(self, driver: WebDriver|None, target_url: str) -> Dict[str, Any]:
        """
        Execute the complete journey.
        
        Args:
            driver: WebDriver instance
            target_url: Starting URL for the journey
            
        Returns:
            Dictionary containing execution results and statistics
        """
        logger = logging.getLogger(f"Journey.{self.name}")
        logger.info(f"Starting journey: {self.name}")
        logger.info(f"Description: {self.description}")
        logger.info(f"Steps: {len(self.steps)}")
        
        # Import here to avoid circular imports
        from ..core.headers import HeaderExtractor
        header_extractor = HeaderExtractor()
        
        start_time = time.time()
        
        # Set initial context
        # Normalize target_url to include scheme when missing (e.g., 'localhost:8080' -> 'http://localhost:8080')
        normalized_target_url = HeaderExtractor._normalize_url(target_url) if isinstance(target_url, str) else target_url
        self.set_context('target_url', normalized_target_url)
        self.set_context('journey_name', self.name)
        self.set_context('start_time', start_time)
        
        results = {
            'journey_name': self.name,
            'journey_description': self.description,
            'expected_result': self.expected_result,
            'start_time': start_time,
            'steps_executed': 0,
            'steps_succeeded': 0,
            'steps_failed': 0,
            'actions_executed': 0,
            'actions_succeeded': 0,
            'actions_failed': 0,
            'overall_success': False,
            'execution_time': 0,
            'step_results': [],
            'errors': [],
            'target_versions': [],
            'version_summary': {}
        }
        
        try:
            # Perform authentication if required
            if self.requires_authentication():
                auth_name = self.authentication.name if self.authentication else "Unknown"
                logger.info(f"Authentication required: {auth_name}")
                if driver is None:
                    # API mode: use header-based authentication if available
                    headers = {}
                    try:
                        if self.authentication and hasattr(self.authentication, 'get_auth_headers'):
                            headers = self.authentication.get_auth_headers() or {}
                    except Exception as e:
                        logger.error(f"Failed to get authentication headers: {e}")
                        headers = {}
                    cookies = {}
                    if headers:
                        # Merge into existing context headers
                        existing = self.get_context('auth_headers', {})
                        merged = {**existing, **headers}
                        self.set_context('auth_headers', merged)
                        logger.info("Authentication headers prepared for API mode")
                    # Try to merge cookies as well (hybrid auth)
                    try:
                        if self.authentication and hasattr(self.authentication, 'get_auth_cookies'):
                            cookies = self.authentication.get_auth_cookies() or {}
                    except Exception as e:
                        logger.error(f"Failed to get authentication cookies: {e}")
                        cookies = {}
                    if cookies:
                        existing_cookies = self.get_context('auth_cookies', {})
                        merged_cookies = {**existing_cookies, **cookies}
                        self.set_context('auth_cookies', merged_cookies)
                        logger.info("Authentication cookies prepared for API mode")
                    if not headers and not cookies:
                        logger.error("Authentication required but no headers/cookies available in API mode")
                        results['errors'].append("Authentication failed (no API auth data)")
                        return results
                else:
                    auth_success = self.authenticate(driver, target_url)
                    if not auth_success:
                        logger.error("Authentication failed - aborting journey")
                        results['errors'].append("Authentication failed")
                        return results
                    logger.info("Authentication successful")
            
            # Execute each step
            for i, step in enumerate(self.steps, 1):
                logger.info(f"Step {i}/{len(self.steps)}: {step.name}")
                results['steps_executed'] += 1
                
                try:
                    step_success = step.execute(driver, self.context)
                    
                    if step_success:
                        results['steps_succeeded'] += 1
                        logger.info(f"✓ Step succeeded: {step.name}")
                    else:
                        results['steps_failed'] += 1
                        logger.error(f"✗ Step failed: {step.name}")
                    
                    # Collect step statistics
                    for action_result in step.execution_results:
                        results['actions_executed'] += 1
                        if action_result['actual']:
                            results['actions_succeeded'] += 1
                        else:
                            results['actions_failed'] += 1
                    
                    # Extract target version header after step execution
                    target_version = header_extractor.extract_target_version_hybrid(driver, target_url)
                    if target_version:
                        results['target_versions'].append(target_version)
                        logger.info(f"Target version detected: {target_version}")
                    
                    # Store step results
                    step_result = {
                        'step_name': step.name,
                        'step_description': step.description,
                        'expected': step.expected_result,
                        'actual': step_success,
                        'actions': step.execution_results.copy(),
                        'step_data': step.step_data.copy(),
                        'target_version': target_version
                    }
                    results['step_results'].append(step_result)

                    # If the previous step exhausted the rate limit, pause before starting the next one
                    try:
                        # Prefer an explicit resume time set by actions
                        resume_at = self.context.get('rate_limit_resume_at')
                        now = time.time()
                        if isinstance(resume_at, (int, float)) and resume_at > now:
                            wait_s = min(resume_at - now, 30)
                            if wait_s > 0:
                                logger.info(f"Rate limit backoff in effect; waiting {wait_s:.2f}s before next step")
                                time.sleep(wait_s)
                        else:
                            last_headers = (self.context.get('last_response_headers') or {})
                            if isinstance(last_headers, dict) and last_headers:
                                def _h(name: str):
                                    name = (name or '').lower()
                                    for k, v in last_headers.items():
                                        if isinstance(k, str) and k.lower() == name:
                                            return v
                                    return None
                                retry_after = _h('retry-after')
                                if retry_after is not None:
                                    try:
                                        wait_s = int(str(retry_after).strip())
                                        if wait_s > 0:
                                            logger.info(f"Rate-limited by server (Retry-After={wait_s}s); pausing before next step")
                                            time.sleep(min(wait_s, 30))
                                    except Exception:
                                        pass
                                else:
                                    remaining = _h('x-ratelimit-remaining')
                                    reset = _h('x-ratelimit-reset')
                                    if remaining is not None and str(remaining).strip() == '0' and reset is not None:
                                        try:
                                            wait_s = int(str(reset).strip())
                                            if wait_s > 0:
                                                logger.info(f"Rate limit reached (remaining=0). Waiting {wait_s}s for reset before next step")
                                                time.sleep(min(wait_s, 30))
                                        except Exception:
                                            pass
                    except Exception:
                        pass
                    
                except Exception as e:
                    logger.error(f"Exception in step {step.name}: {str(e)}")
                    results['steps_failed'] += 1
                    results['errors'].append(f"Step {step.name}: {str(e)}")
            
            # Determine overall success
            if self.expected_result:
                # Journey expects to succeed
                results['overall_success'] = results['steps_failed'] == 0
            else:
                # Journey expects to fail
                results['overall_success'] = results['steps_failed'] > 0
            
        except Exception as e:
            logger.error(f"Critical error in journey: {str(e)}")
            results['errors'].append(f"Critical error: {str(e)}")
        
        finally:
            end_time = time.time()
            results['end_time'] = end_time
            results['execution_time'] = end_time - start_time
            
            # Generate version summary
            if results['target_versions']:
                version_summary = header_extractor.get_version_summary([{'target_version': v} for v in results['target_versions']])
                results['version_summary'] = version_summary
                logger.info(f"Target versions detected: {list(set(results['target_versions']))}")
            
            logger.info(f"Journey completed in {results['execution_time']:.2f} seconds")
            logger.info(f"Overall success: {results['overall_success']}")
            logger.info(f"Steps: {results['steps_succeeded']}/{results['steps_executed']} succeeded")
            logger.info(f"Actions: {results['actions_succeeded']}/{results['actions_executed']} succeeded")
        
        return results
    
    def store_data(self, key: str, value: Any) -> None:
        """Store journey-specific data."""
        self.journey_data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve journey-specific data."""
        return self.journey_data.get(key, default)