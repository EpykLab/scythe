from typing import Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
import time
import random
from .base import Behavior

class StealthBehavior(Behavior):
    """
    Behavior that emulates stealthy interaction patterns during TTP execution.
    
    This behavior focuses on evading detection by implementing randomized timing,
    user agent rotation, and anti-fingerprinting techniques to appear more like
    legitimate user traffic.
    """
    
    def __init__(self, 
                 min_delay: float = 3.0,
                 max_delay: float = 8.0,
                 burst_probability: float = 0.1,
                 burst_size: int = 3,
                 long_pause_probability: float = 0.15,
                 long_pause_duration: float = 30.0,
                 max_requests_per_session: int = 20,
                 session_cooldown: float = 300.0):
        """
        Initialize StealthBehavior.
        
        Args:
            min_delay: Minimum delay between actions in seconds
            max_delay: Maximum delay between actions in seconds
            burst_probability: Probability of executing a burst of actions
            burst_size: Number of actions in a burst
            long_pause_probability: Probability of taking a long pause
            long_pause_duration: Duration of long pauses in seconds
            max_requests_per_session: Maximum requests before session reset
            session_cooldown: Cooldown period between sessions in seconds
        """
        super().__init__(
            name="Stealth Behavior",
            description="Emulates stealthy interaction patterns to evade detection with randomized timing and anti-fingerprinting"
        )
        
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.burst_probability = burst_probability
        self.burst_size = burst_size
        self.long_pause_probability = long_pause_probability
        self.long_pause_duration = long_pause_duration
        self.max_requests_per_session = max_requests_per_session
        self.session_cooldown = session_cooldown
        
        self.requests_in_session = 0
        self.in_burst = False
        self.burst_remaining = 0
        self.last_session_reset = 0
        
        # Common user agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
        
    def pre_execution(self, driver: WebDriver, target_url: str) -> None:
        """
        Prepare for stealthy execution with anti-detection measures.
        """
        # Randomize window size to avoid fingerprinting
        common_resolutions = [
            (1920, 1080), (1366, 768), (1440, 900), (1536, 864), (1280, 720)
        ]
        width, height = random.choice(common_resolutions)
        driver.set_window_size(width, height)
        
        # Set random user agent
        user_agent = random.choice(self.user_agents)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": user_agent
        })
        
        # Initial reconnaissance delay
        reconnaissance_delay = self._random_delay(5.0, 15.0)
        time.sleep(reconnaissance_delay)
        
        # Simulate browsing behavior before starting
        self._simulate_reconnaissance(driver, target_url)
        
    def pre_step(self, driver: WebDriver, payload: Any, step_number: int) -> None:
        """
        Prepare for each step with stealth considerations.
        """
        # Check if we need to reset session
        if self.requests_in_session >= self.max_requests_per_session:
            self._reset_session(driver)
        
        # Random long pause to simulate user going away
        if random.random() < self.long_pause_probability:
            pause_duration = self._random_delay(
                self.long_pause_duration * 0.5, 
                self.long_pause_duration * 1.5
            )
            time.sleep(pause_duration)
        
        # Simulate legitimate user behavior
        self._simulate_legitimate_browsing(driver)
        
    def post_step(self, driver: WebDriver, payload: Any, step_number: int, success: bool) -> None:
        """
        Post-step behavior with stealth considerations.
        """
        self.requests_in_session += 1
        
        # Handle burst behavior
        if self.in_burst:
            self.burst_remaining -= 1
            if self.burst_remaining <= 0:
                self.in_burst = False
                # Longer pause after burst
                time.sleep(self._random_delay(10.0, 20.0))
        
        # Simulate reading/analyzing results
        if success:
            # Longer pause on success to "analyze" results
            analysis_delay = self._random_delay(8.0, 15.0)
            time.sleep(analysis_delay)
            self._simulate_result_analysis(driver)
        else:
            # Shorter pause on failure, but still realistic
            time.sleep(self._random_delay(3.0, 6.0))
        
        # Random additional stealth actions
        if random.random() < 0.3:  # 30% chance
            self._perform_stealth_action(driver)
            
    def post_execution(self, driver: WebDriver, results: list) -> None:
        """
        Final stealth behavior after execution completes.
        """
        # Simulate user finishing their session naturally
        self._simulate_session_cleanup(driver)
        
        # Final delay before closing
        final_delay = self._random_delay(5.0, 10.0)
        time.sleep(final_delay)
        
    def get_step_delay(self, step_number: int) -> float:
        """
        Calculate stealth delay with randomization and burst detection.
        
        Stealth behavior uses highly variable timing to avoid pattern detection.
        """
        # Check for burst behavior
        if not self.in_burst and random.random() < self.burst_probability:
            self.in_burst = True
            self.burst_remaining = self.burst_size
            return self._random_delay(0.5, 2.0)  # Short delay during burst
        
        if self.in_burst:
            return self._random_delay(0.5, 2.0)  # Short delay during burst
        
        # Normal stealth timing with high variance
        base_delay = self._random_delay(self.min_delay, self.max_delay)
        
        # Add exponential backoff for consecutive requests
        backoff_factor = min(2.0, 1.0 + (self.requests_in_session * 0.1))
        
        return base_delay * backoff_factor
    
    def should_continue(self, step_number: int, consecutive_failures: int) -> bool:
        """
        Stealth decision making on whether to continue.
        
        Stealth behavior is more cautious and gives up sooner to avoid detection.
        """
        # More conservative approach - give up after fewer failures
        if consecutive_failures >= 2:
            return False
            
        # Limit total requests per session
        if self.requests_in_session >= self.max_requests_per_session:
            return False
            
        return True
    
    def on_error(self, error: Exception, step_number: int) -> bool:
        """
        Stealth error handling with anti-detection measures.
        """
        # Longer pause on errors to simulate user confusion
        error_delay = self._random_delay(10.0, 30.0)
        time.sleep(error_delay)
        
        # Reset session on certain errors to avoid detection
        detection_errors = [
            "WebDriverException",
            "TimeoutException", 
            "ElementNotInteractableException"
        ]
        
        if any(error_type in str(type(error)) for error_type in detection_errors):
            if random.random() < 0.7:  # 70% chance to reset session
                self._reset_session()
                return False
        
        # Conservative approach - don't retry as much
        return step_number < 3
    
    def _reset_session(self, driver: WebDriver | None = None) -> None:
        """
        Reset session to avoid detection patterns.
        """
        current_time = time.time()
        
        # Enforce cooldown period
        if current_time - self.last_session_reset < self.session_cooldown:
            remaining_cooldown = self.session_cooldown - (current_time - self.last_session_reset)
            time.sleep(remaining_cooldown)
        
        # Reset counters
        self.requests_in_session = 0
        self.last_session_reset = current_time
        
        if driver:
            # Clear cookies and reset browser state
            driver.delete_all_cookies()
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            
            # Change user agent
            user_agent = random.choice(self.user_agents)
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent
            })
    
    def _simulate_reconnaissance(self, driver: WebDriver, target_url: str) -> None:
        """
        Simulate reconnaissance behavior before starting attacks.
        """
        try:
            # Visit related pages to establish legitimate-looking traffic
            if "://" in target_url:
                base_url = target_url.split("://")[1].split("/")[0]
                recon_urls = [
                    f"https://{base_url}",
                    f"https://{base_url}/robots.txt",
                    f"https://{base_url}/sitemap.xml"
                ]
                
                for url in recon_urls:
                    try:
                        driver.get(url)
                        time.sleep(self._random_delay(2.0, 5.0))
                    except Exception:
                        continue
                        
        except Exception:
            pass
    
    def _simulate_legitimate_browsing(self, driver: WebDriver) -> None:
        """
        Simulate legitimate user browsing behavior.
        """
        try:
            # Random scrolling
            if random.random() < 0.4:  # 40% chance
                scroll_amount = random.randint(100, 500)
                direction = random.choice(["down", "up"])
                
                if direction == "down":
                    driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                else:
                    driver.execute_script(f"window.scrollBy(0, -{scroll_amount});")
                
                time.sleep(self._random_delay(1.0, 3.0))
            
            # Random element hovering
            if random.random() < 0.3:  # 30% chance
                try:
                    elements = driver.find_elements(By.TAG_NAME, "a")[:5]
                    if elements:
                        element = random.choice(elements)
                        ActionChains(driver).move_to_element(element).perform()
                        time.sleep(self._random_delay(0.5, 1.5))
                except Exception:
                    pass
                    
        except Exception:
            pass
    
    def _simulate_result_analysis(self, driver: WebDriver) -> None:
        """
        Simulate analyzing results after successful action.
        """
        try:
            # Look for specific result indicators
            indicators = ["dashboard", "profile", "admin", "welcome", "success"]
            
            for indicator in indicators:
                try:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{indicator}')]")
                    if elements:
                        # Focus on result elements
                        ActionChains(driver).move_to_element(elements[0]).perform()
                        time.sleep(self._random_delay(1.0, 2.0))
                        break
                except Exception:
                    continue
                    
        except Exception:
            pass
    
    def _perform_stealth_action(self, driver: WebDriver) -> None:
        """
        Perform random stealth actions to maintain cover.
        """
        actions = [
            self._random_page_interaction,
            self._check_page_source,
            self._random_navigation
        ]
        
        action = random.choice(actions)
        try:
            action(driver)
        except Exception:
            pass
    
    def _random_page_interaction(self, driver: WebDriver) -> None:
        """Random interaction with page elements."""
        try:
            # Find interactive elements
            elements = driver.find_elements(By.TAG_NAME, "input")
            elements.extend(driver.find_elements(By.TAG_NAME, "button"))
            elements.extend(driver.find_elements(By.TAG_NAME, "select"))
            
            if elements:
                element = random.choice(elements[:3])  # Choose from first 3
                ActionChains(driver).move_to_element(element).perform()
                time.sleep(self._random_delay(0.5, 1.0))
                
        except Exception:
            pass
    
    def _check_page_source(self, driver: WebDriver) -> None:
        """Simulate checking page source or network activity."""
        try:
            # Open developer tools briefly (if possible)
            driver.execute_script("console.log('Checking page...');")
            time.sleep(self._random_delay(1.0, 2.0))
            
        except Exception:
            pass
    
    def _random_navigation(self, driver: WebDriver) -> None:
        """Simulate random navigation behavior."""
        try:
            # Random chance to go back and forward
            if random.random() < 0.3:  # 30% chance
                driver.back()
                time.sleep(self._random_delay(1.0, 2.0))
                driver.forward()
                time.sleep(self._random_delay(1.0, 2.0))
                
        except Exception:
            pass
    
    def _simulate_session_cleanup(self, driver: WebDriver) -> None:
        """
        Simulate natural session cleanup behavior.
        """
        try:
            # Visit some benign pages to mask the session
            cleanup_actions = [
                lambda: driver.get("https://www.google.com"),
                lambda: driver.get("https://www.example.com"),
                lambda: driver.execute_script("window.location.reload();")
            ]
            
            action = random.choice(cleanup_actions)
            action()
            time.sleep(self._random_delay(2.0, 5.0))
            
        except Exception:
            pass