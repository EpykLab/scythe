import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from typing import Optional, Dict, Any, List
import requests
from ..behaviors.base import Behavior
from .base import Journey
from ..core.headers import HeaderExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('journey_test.log'),
        logging.StreamHandler()
    ]
)


class JourneyExecutor:
    """
    The main engine for running Journey tests.
    
    Similar to TTPExecutor but designed for complex multi-step scenarios
    involving journeys composed of steps and actions.
    
    Supports two interaction modes:
      - UI: browser-driven via Selenium (default, backward-compatible)
      - API: REST-driven via requests without starting a browser
    """
    
    def __init__(self, 
                 journey: Journey, 
                 target_url: str, 
                 headless: bool = True, 
                 behavior: Optional[Behavior] = None,
                 driver_options: Optional[Dict[str, Any]] = None,
                 mode: str = "UI"):
        """
        Initialize the Journey executor.
        
        Args:
            journey: Journey instance to execute
            target_url: Starting URL for the journey
            headless: Whether to run browser in headless mode
            behavior: Optional behavior to control execution patterns
            driver_options: Additional Chrome driver options
        """
        self.journey = journey
        self.target_url = target_url
        self.behavior = behavior
        self.mode = (mode or "UI").upper()
        self.logger = logging.getLogger(f"Journey.{self.journey.name}")
        
        # Setup Chrome options
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Apply additional driver options
        if driver_options:
            for key, value in driver_options.items():
                if hasattr(self.chrome_options, key):
                    setattr(self.chrome_options, key, value)
                else:
                    self.chrome_options.add_argument(f"--{key}={value}")
        
        # Enable header extraction capabilities
        HeaderExtractor.enable_logging_for_driver(self.chrome_options)
        
        self.driver = None
        self.execution_results = None
        self.header_extractor = HeaderExtractor()
    
    def _setup_driver(self):
        """Initialize the WebDriver."""
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            
            # Add stealth settings
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": self.driver.execute_script("return navigator.userAgent").replace("HeadlessChrome", "Chrome")
            })
            
            self.logger.info("WebDriver initialized for journey execution.")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the complete journey.
        
        Returns:
            Dictionary containing detailed execution results
        """
        self.logger.info("="*60)
        self.logger.info(f"STARTING JOURNEY: {self.journey.name}")
        self.logger.info("="*60)
        self.logger.info(f"Description: {self.journey.description}")
        self.logger.info(f"Target URL: {self.target_url}")
        self.logger.info(f"Expected Result: {'SUCCESS' if self.journey.expected_result else 'FAILURE'}")
        self.logger.info(f"Steps: {len(self.journey.steps)}")
        
        if self.behavior:
            self.logger.info(f"Using behavior: {self.behavior.name}")
            self.logger.info(f"Behavior description: {self.behavior.description}")
        
        try:
            if self.mode == 'API':
                # API mode: no WebDriver, prepare requests session and context
                session = requests.Session()
                auth_headers = {}
                auth_cookies = {}
                if getattr(self.journey, 'authentication', None):
                    # Try to obtain headers/cookies directly (no browser flow)
                    try:
                        auth_headers = self.journey.authentication.get_auth_headers() or {}
                    except Exception as e:
                        self.logger.warning(f"Failed to get auth headers from authentication: {e}")
                    try:
                        if hasattr(self.journey.authentication, 'get_auth_cookies'):
                            auth_cookies = self.journey.authentication.get_auth_cookies() or {}
                    except Exception as e:
                        self.logger.warning(f"Failed to get auth cookies from authentication: {e}")
                if auth_headers:
                    session.headers.update(auth_headers)
                if auth_cookies:
                    for ck, cv in auth_cookies.items():
                        try:
                            session.cookies.set(ck, cv)
                        except Exception:
                            pass
                
                # Seed journey context for API actions
                self.journey.set_context('mode', 'API')
                self.journey.set_context('requests_session', session)
                self.journey.set_context('auth_headers', auth_headers)
                self.journey.set_context('auth_cookies', auth_cookies)
                
                # Execute a journey with a None driver (API actions ignore a driver)
                self.execution_results = self.journey.execute(None, self.target_url)
            else:
                # UI mode (default)
                self._setup_driver()
                
                # Pre-execution behavior setup
                if self.behavior and self.driver:
                    self.behavior.pre_execution(self.driver, self.target_url)
                
                # Execute the journey
                if self.driver:
                    self.execution_results = self.journey.execute(self.driver, self.target_url)
                else:
                    raise RuntimeError("WebDriver not initialized")
                
                # Apply behavior timing between steps if configured
                if self.behavior:
                    self._apply_behavior_to_journey()
                
                # Post-execution behavior cleanup
                if self.behavior and self.driver:
                    behavior_results = self._convert_results_for_behavior()
                    self.behavior.post_execution(self.driver, behavior_results)
        
        except KeyboardInterrupt:
            self.logger.info("Journey interrupted by user.")
            if not self.execution_results:
                self.execution_results = self._create_interrupted_results()
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during journey execution: {e}", exc_info=True)
            if not self.execution_results:
                self.execution_results = self._create_error_results(str(e))
        
        finally:
            # Cleanup and print summary (driver quit only if initialized)
            self._cleanup()
        
        return self.execution_results
    
    def _apply_behavior_to_journey(self):
        """Apply behavior patterns to journey execution results."""
        if not self.behavior or not self.execution_results:
            return
        
        # Apply behavior timing and logging to individual steps
        for i, step_result in enumerate(self.execution_results.get('step_results', []), 1):
            step_name = step_result.get('step_name', f'Step {i}')
            step_success = step_result.get('actual', False)
            
            # Get behavior delay for this step
            if hasattr(self.behavior, 'get_step_delay'):
                delay = self.behavior.get_step_delay(i)
                if delay > 0:
                    self.logger.info(f"Behavior delay: {delay:.2f}s after step '{step_name}'")
                    time.sleep(delay)
            
            # Let behavior react to step results
            if hasattr(self.behavior, 'post_step'):
                try:
                    # Create a mock payload for behavior compatibility
                    mock_payload = step_name
                    if self.driver:
                        self.behavior.post_step(self.driver, mock_payload, i, step_success)
                except Exception as e:
                    self.logger.warning(f"Behavior post_step failed: {e}")
    
    def _convert_results_for_behavior(self) -> List[Dict[str, Any]]:
        """Convert journey results to format expected by behavior system."""
        if not self.execution_results:
            return []
        
        behavior_results = []
        
        # Add overall journey result
        behavior_results.append({
            'journey': self.journey.name,
            'success': self.execution_results.get('overall_success', False),
            'url': self.target_url
        })
        
        # Add step results
        for step_result in self.execution_results.get('step_results', []):
            if step_result.get('actual', False):
                behavior_results.append({
                    'step': step_result.get('step_name', 'Unknown'),
                    'success': True,
                    'url': self.driver.current_url if self.driver else 'unknown'
                })
        
        return behavior_results
    
    def _create_interrupted_results(self) -> Dict[str, Any]:
        """Create results structure for interrupted journey."""
        return {
            'journey_name': self.journey.name,
            'journey_description': self.journey.description,
            'expected_result': self.journey.expected_result,
            'start_time': time.time(),
            'end_time': time.time(),
            'execution_time': 0,
            'steps_executed': 0,
            'steps_succeeded': 0,
            'steps_failed': 0,
            'actions_executed': 0,
            'actions_succeeded': 0,
            'actions_failed': 0,
            'overall_success': False,
            'step_results': [],
            'errors': ['Journey interrupted by user'],
            'status': 'interrupted'
        }
    
    def _create_error_results(self, error_message: str) -> Dict[str, Any]:
        """Create results structure for error case."""
        return {
            'journey_name': self.journey.name,
            'journey_description': self.journey.description,
            'expected_result': self.journey.expected_result,
            'start_time': time.time(),
            'end_time': time.time(),
            'execution_time': 0,
            'steps_executed': 0,
            'steps_succeeded': 0,
            'steps_failed': 1,
            'actions_executed': 0,
            'actions_succeeded': 0,
            'actions_failed': 0,
            'overall_success': False,
            'step_results': [],
            'errors': [error_message],
            'status': 'error'
        }
    
    def _cleanup(self):
        """Close the WebDriver and print journey summary."""
        if self.driver:
            self.driver.quit()
        
        if not self.execution_results:
            return
        
        # Print detailed summary
        self.logger.info("\n" + "="*60)
        self.logger.info(f"JOURNEY SUMMARY: {self.journey.name}")
        self.logger.info("="*60)
        
        # Overall results
        overall_success = self.execution_results.get('overall_success', False)
        expected = self.execution_results.get('expected_result', True)
        execution_time = self.execution_results.get('execution_time', 0)
        
        if overall_success == expected:
            if expected:
                self.logger.info(f"✓ EXPECTED SUCCESS: Journey completed successfully in {execution_time:.2f}s")
            else:
                self.logger.info(f"✓ EXPECTED FAILURE: Journey failed as expected in {execution_time:.2f}s")
        else:
            if expected:
                self.logger.warning(f"✗ UNEXPECTED FAILURE: Journey was expected to succeed but failed in {execution_time:.2f}s")
            else:
                self.logger.warning(f"✗ UNEXPECTED SUCCESS: Journey was expected to fail but succeeded in {execution_time:.2f}s")
        
        # Step statistics
        steps_executed = self.execution_results.get('steps_executed', 0)
        steps_succeeded = self.execution_results.get('steps_succeeded', 0)
        steps_failed = self.execution_results.get('steps_failed', 0)
        
        self.logger.info(f"Steps: {steps_succeeded}/{steps_executed} succeeded ({steps_failed} failed)")
        
        # Action statistics
        actions_executed = self.execution_results.get('actions_executed', 0)
        actions_succeeded = self.execution_results.get('actions_succeeded', 0)
        actions_failed = self.execution_results.get('actions_failed', 0)
        
        self.logger.info(f"Actions: {actions_succeeded}/{actions_executed} succeeded ({actions_failed} failed)")
        
        # Error summary
        errors = self.execution_results.get('errors', [])
        if errors:
            self.logger.error(f"Errors encountered: {len(errors)}")
            for i, error in enumerate(errors[:5], 1):  # Show first 5 errors
                self.logger.error(f"  {i}. {error}")
            if len(errors) > 5:
                self.logger.error(f"  ... and {len(errors) - 5} more errors")
        
        # Step details
        step_results = self.execution_results.get('step_results', [])
        if step_results:
            self.logger.info("\nStep Details:")
            for i, step_result in enumerate(step_results, 1):
                step_name = step_result.get('step_name', f'Step {i}')
                step_success = step_result.get('actual', False)
                step_expected = step_result.get('expected', True)
                actions = step_result.get('actions', [])
                target_version = step_result.get('target_version')
                
                status = "✓" if step_success == step_expected else "✗"
                result_text = "SUCCESS" if step_success else "FAILURE"
                expected_text = "expected" if step_success == step_expected else "unexpected"
                version_info = f" | Version: {target_version}" if target_version else ""
                
                self.logger.info(f"  {status} Step {i}: {step_name} - {result_text} ({expected_text}){version_info}")
                self.logger.info(f"    Actions: {len([a for a in actions if a.get('actual', False)])}/{len(actions)} succeeded")
                # Print diagnostic details only for unexpected outcomes
                for a in actions:
                    actual = a.get('actual', False)
                    expected = a.get('expected', True)
                    if actual != expected:
                        prefix = "✗ Action failed" if expected else "✗ Action unexpectedly succeeded"
                        self.logger.error(f"    {prefix}: {a.get('action_name')}")
                        ad = a.get('details', {}) or {}
                        method = ad.get('request_method')
                        url = ad.get('url')
                        status_code = ad.get('status_code')
                        dur = ad.get('duration_ms')
                        parts = []
                        if method:
                            parts.append(f"method={method}")
                        if url:
                            parts.append(f"url={url}")
                        if status_code is not None:
                            parts.append(f"status={status_code}")
                        if dur is not None:
                            parts.append(f"duration_ms={dur}")
                        if parts:
                            self.logger.error("      Details: " + ", ".join(parts))
                        if ad.get('request_headers'):
                            self.logger.error(f"      Request headers: {ad.get('request_headers')}")
                        if ad.get('request_params'):
                            self.logger.error(f"      Request params: {ad.get('request_params')}")
                        if ad.get('request_json') is not None:
                            self.logger.error(f"      Request JSON: {ad.get('request_json')}")
                        if ad.get('request_data') is not None:
                            self.logger.error(f"      Request data: {ad.get('request_data')}")
                        if ad.get('response_headers'):
                            self.logger.error(f"      Response headers: {ad.get('response_headers')}")
                        if 'response_json' in ad:
                            self.logger.error(f"      Response JSON: {ad.get('response_json')}")
                        elif 'response_text' in ad:
                            self.logger.error(f"      Response text: {ad.get('response_text')}")
                        if ad.get('error'):
                            self.logger.error(f"      Error: {ad.get('error')}")
        
        # Version summary
        target_versions = self.execution_results.get('target_versions', [])
        
        if target_versions:
            self.logger.info("\nTarget Version Summary:")
            self.logger.info(f"  Steps with version info: {len(target_versions)}/{len(step_results) if step_results else 0}")
            unique_versions = list(set(target_versions))
            if unique_versions:
                for version in unique_versions:
                    count = target_versions.count(version)
                    self.logger.info(f"  Version {version}: {count} step(s)")
        else:
            self.logger.info("\nNo X-SCYTHE-TARGET-VERSION headers detected in responses.")
        
        # Log overall test status (similar to TTPExecutor)
        if self.was_successful():
            self.logger.info("\n✓ TEST PASSED: Journey results matched expectations")
        else:
            self.logger.error("\n✗ TEST FAILED: Journey results differed from expected")
        
        self.logger.info("="*60)
    
    def get_results(self) -> Optional[Dict[str, Any]]:
        """
        Get the execution results.
        
        Returns:
            Dictionary containing execution results, or None if journey hasn't been executed
        """
        return self.execution_results
    
    def get_step_results(self) -> List[Dict[str, Any]]:
        """
        Get detailed results for each step.
        
        Returns:
            List of step result dictionaries
        """
        if not self.execution_results:
            return []
        return self.execution_results.get('step_results', [])
    
    def get_action_results(self) -> List[Dict[str, Any]]:
        """
        Get detailed results for each action across all steps.
        
        Returns:
            Flattened list of action result dictionaries
        """
        action_results = []
        for step_result in self.get_step_results():
            actions = step_result.get('actions', [])
            for action in actions:
                action_with_step = action.copy()
                action_with_step['step_name'] = step_result.get('step_name', 'Unknown')
                action_results.append(action_with_step)
        return action_results
    
    def was_successful(self) -> bool:
        """
        Check if the journey execution was successful based on expected results.
        
        Returns:
            True if journey succeeded as expected, False otherwise
        """
        if not self.execution_results:
            return False
        
        actual = self.execution_results.get('overall_success', False)
        expected = self.execution_results.get('expected_result', True)
        return actual == expected


class JourneyRunner:
    """
    Utility class for running multiple journeys in sequence or with specific configurations.
    """
    
    def __init__(self, headless: bool = True, behavior: Optional[Behavior] = None):
        """
        Initialize the journey runner.
        
        Args:
            headless: Whether to run browser in headless mode
            behavior: Optional behavior to apply to all journeys
        """
        self.headless = headless
        self.behavior = behavior
        self.results = []
        self.logger = logging.getLogger("JourneyRunner")
    
    def run_journey(self, journey: Journey, target_url: str, **kwargs) -> Dict[str, Any]:
        """
        Run a single journey.
        
        Args:
            journey: Journey to execute
            target_url: Starting URL for the journey
            **kwargs: Additional arguments for JourneyExecutor
            
        Returns:
            Journey execution results
        """
        executor = JourneyExecutor(
            journey=journey,
            target_url=target_url,
            headless=self.headless,
            behavior=self.behavior,
            **kwargs
        )
        
        results = executor.run()
        self.results.append(results)
        return results
    
    def run_journeys(self, journeys: List[tuple], delay_between: float = 1.0) -> List[Dict[str, Any]]:
        """
        Run multiple journeys in sequence.
        
        Args:
            journeys: List of (journey, target_url) tuples
            delay_between: Delay in seconds between journey executions
            
        Returns:
            List of journey execution results
        """
        self.logger.info(f"Running {len(journeys)} journeys in sequence")
        
        all_results = []
        
        for i, (journey, target_url) in enumerate(journeys, 1):
            self.logger.info(f"\n--- Journey {i}/{len(journeys)}: {journey.name} ---")
            
            results = self.run_journey(journey, target_url)
            all_results.append(results)
            
            # Delay between journeys if not the last one
            if i < len(journeys) and delay_between > 0:
                self.logger.info(f"Waiting {delay_between}s before next journey...")
                time.sleep(delay_between)
        
        # Print summary
        self._print_batch_summary(all_results)
        
        return all_results
    
    def _print_batch_summary(self, results: List[Dict[str, Any]]):
        """Print summary of batch journey execution."""
        self.logger.info("\n" + "="*60)
        self.logger.info("BATCH JOURNEY SUMMARY")
        self.logger.info("="*60)
        
        total_journeys = len(results)
        successful_journeys = sum(1 for r in results if r.get('overall_success') == r.get('expected_result'))
        total_time = sum(r.get('execution_time', 0) for r in results)
        
        self.logger.info(f"Journeys: {successful_journeys}/{total_journeys} completed as expected")
        self.logger.info(f"Total execution time: {total_time:.2f}s")
        self.logger.info(f"Average time per journey: {total_time/total_journeys:.2f}s")
        
        # List individual journey results
        for i, result in enumerate(results, 1):
            journey_name = result.get('journey_name', f'Journey {i}')
            overall_success = result.get('overall_success', False)
            expected = result.get('expected_result', True)
            exec_time = result.get('execution_time', 0)
            
            status = "✓" if overall_success == expected else "✗"
            result_text = "SUCCESS" if overall_success else "FAILURE"
            expected_text = "expected" if overall_success == expected else "unexpected"
            
            self.logger.info(f"  {status} {journey_name}: {result_text} ({expected_text}) - {exec_time:.2f}s")
        
        self.logger.info("="*60)
    
    def get_all_results(self) -> List[Dict[str, Any]]:
        """Get results from all executed journeys."""
        return self.results.copy()
    
    def clear_results(self):
        """Clear stored results."""
        self.results.clear()