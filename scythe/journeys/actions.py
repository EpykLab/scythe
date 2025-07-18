import time
from typing import Dict, Any, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base import Action
from ..core.ttp import TTP


class NavigateAction(Action):
    """Action to navigate to a specific URL."""
    
    def __init__(self, url: str, name: Optional[str] = None, description: Optional[str] = None, expected_result: bool = True):
        """
        Initialize navigation action.
        
        Args:
            url: URL to navigate to
            name: Optional custom name for the action
            description: Optional custom description
            expected_result: Whether navigation is expected to succeed
        """
        self.url = url
        name = name or f"Navigate to {url}"
        description = description or f"Navigate browser to {url}"
        super().__init__(name, description, expected_result)
    
    def execute(self, driver: WebDriver, context: Dict[str, Any]) -> bool:
        """
        Execute navigation.
        
        Args:
            driver: WebDriver instance
            context: Shared context data
            
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            # Support URL templates using context
            actual_url = self.url.format(**context)
            driver.get(actual_url)
            
            # Store the current URL in context
            context['current_url'] = driver.current_url
            self.store_result('navigated_url', actual_url)
            self.store_result('final_url', driver.current_url)
            
            return True
            
        except Exception as e:
            self.store_result('error', str(e))
            return False


class ClickAction(Action):
    """Action to click on an element."""
    
    def __init__(self, 
                 selector: str, 
                 selector_type: str = "css",
                 wait_timeout: float = 10.0,
                 name: Optional[str] = None, 
                 description: Optional[str] = None, 
                 expected_result: bool = True):
        """
        Initialize click action.
        
        Args:
            selector: Element selector (CSS, XPath, ID, etc.)
            selector_type: Type of selector ('css', 'xpath', 'id', 'name', 'class', 'tag')
            wait_timeout: Maximum time to wait for element
            name: Optional custom name
            description: Optional custom description
            expected_result: Whether click is expected to succeed
        """
        self.selector = selector
        self.selector_type = selector_type.lower()
        self.wait_timeout = wait_timeout
        
        name = name or f"Click {selector}"
        description = description or f"Click element matching {selector_type} selector: {selector}"
        super().__init__(name, description, expected_result)
    
    def execute(self, driver: WebDriver, context: Dict[str, Any]) -> bool:
        """
        Execute click action.
        
        Args:
            driver: WebDriver instance
            context: Shared context data
            
        Returns:
            True if click successful, False otherwise
        """
        try:
            # Get the appropriate By method
            by_method = self._get_by_method()
            if not by_method:
                self.store_result('error', f"Unsupported selector type: {self.selector_type}")
                return False
            
            # Wait for element to be clickable
            wait = WebDriverWait(driver, self.wait_timeout)
            element = wait.until(EC.element_to_be_clickable((by_method, self.selector)))
            
            # Store element info
            self.store_result('element_tag', element.tag_name)
            self.store_result('element_text', element.text)
            
            # Click the element
            element.click()
            
            # Store success info
            self.store_result('clicked_url', driver.current_url)
            context['last_clicked_element'] = self.selector
            
            return True
            
        except TimeoutException:
            self.store_result('error', f"Element not found or not clickable within {self.wait_timeout}s")
            return False
        except Exception as e:
            self.store_result('error', str(e))
            return False
    
    def _get_by_method(self):
        """Get the appropriate By method for the selector type."""
        selector_map = {
            'css': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'tag': By.TAG_NAME,
            'link_text': By.LINK_TEXT,
            'partial_link_text': By.PARTIAL_LINK_TEXT
        }
        by_method = selector_map.get(self.selector_type)
        if by_method is None:
            raise ValueError(f"Unsupported selector type: {self.selector_type}")
        return by_method


class FillFormAction(Action):
    """Action to fill form fields."""
    
    def __init__(self, 
                 field_data: Dict[str, str],
                 selector_type: str = "css",
                 wait_timeout: float = 10.0,
                 clear_before_fill: bool = True,
                 name: Optional[str] = None, 
                 description: Optional[str] = None,
                 expected_result: bool = True):
        """
        Initialize form fill action.
        
        Args:
            field_data: Dictionary mapping selectors to values
            selector_type: Type of selector for all fields
            wait_timeout: Maximum time to wait for each field
            clear_before_fill: Whether to clear fields before filling
            name: Optional custom name
            description: Optional custom description
            expected_result: Whether form filling is expected to succeed
        """
        self.field_data = field_data
        self.selector_type = selector_type.lower()
        self.wait_timeout = wait_timeout
        self.clear_before_fill = clear_before_fill
        
        name = name or "Fill Form Fields"
        description = description or f"Fill {len(field_data)} form fields"
        super().__init__(name, description, expected_result)
    
    def execute(self, driver: WebDriver, context: Dict[str, Any]) -> bool:
        """
        Execute form filling.
        
        Args:
            driver: WebDriver instance
            context: Shared context data
            
        Returns:
            True if all fields filled successfully, False otherwise
        """
        try:
            by_method = self._get_by_method()
            if not by_method:
                self.store_result('error', f"Unsupported selector type: {self.selector_type}")
                return False
            
            filled_fields = []
            failed_fields = []
            
            for selector, value in self.field_data.items():
                try:
                    # Support value templates using context
                    actual_value = str(value).format(**context)
                    
                    # Wait for field to be present
                    wait = WebDriverWait(driver, self.wait_timeout)
                    element = wait.until(EC.presence_of_element_located((by_method, selector)))
                    
                    # Clear field if requested
                    if self.clear_before_fill:
                        element.clear()
                    
                    # Fill the field
                    element.send_keys(actual_value)
                    
                    filled_fields.append({
                        'selector': selector,
                        'value': actual_value,
                        'element_type': element.get_attribute('type') or element.tag_name
                    })
                    
                except Exception as e:
                    failed_fields.append({
                        'selector': selector,
                        'value': value,
                        'error': str(e)
                    })
            
            # Store results
            self.store_result('filled_fields', filled_fields)
            self.store_result('failed_fields', failed_fields)
            self.store_result('fields_filled', len(filled_fields))
            self.store_result('fields_failed', len(failed_fields))
            
            # Update context with filled data
            context['last_form_data'] = self.field_data
            
            return len(failed_fields) == 0
            
        except Exception as e:
            self.store_result('error', str(e))
            return False
    
    def _get_by_method(self):
        """Get the appropriate By method for the selector type."""
        selector_map = {
            'css': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'name': By.NAME,
            'class': By.CLASS_NAME
        }
        by_method = selector_map.get(self.selector_type)
        if by_method is None:
            raise ValueError(f"Unsupported selector type: {self.selector_type}")
        return by_method


class WaitAction(Action):
    """Action to wait for a condition or specific time."""
    
    def __init__(self, 
                 wait_type: str = "time",
                 duration: float = 1.0,
                 selector: Optional[str] = None,
                 selector_type: str = "css",
                 condition: str = "presence",
                 name: Optional[str] = None, 
                 description: Optional[str] = None,
                 expected_result: bool = True):
        """
        Initialize wait action.
        
        Args:
            wait_type: Type of wait ('time', 'element', 'url_contains', 'title_contains')
            duration: Time to wait in seconds (for time waits or timeout for others)
            selector: Element selector (for element waits)
            selector_type: Type of selector
            condition: Condition to wait for ('presence', 'visible', 'clickable', 'invisible')
            name: Optional custom name
            description: Optional custom description
            expected_result: Whether wait is expected to succeed
        """
        self.wait_type = wait_type.lower()
        self.duration = duration
        self.selector = selector
        self.selector_type = selector_type.lower()
        self.condition = condition.lower()
        
        if not name:
            if wait_type == "time":
                name = f"Wait {duration} seconds"
            elif wait_type == "element":
                name = f"Wait for element {selector}"
            else:
                name = f"Wait for {wait_type}"
        
        description = description or f"Wait using {wait_type} strategy"
        super().__init__(name, description, expected_result)
    
    def execute(self, driver: WebDriver, context: Dict[str, Any]) -> bool:
        """
        Execute wait action.
        
        Args:
            driver: WebDriver instance
            context: Shared context data
            
        Returns:
            True if wait condition met, False otherwise
        """
        start_time = time.time()
        try:
            
            if self.wait_type == "time":
                time.sleep(self.duration)
                self.store_result('wait_time', self.duration)
                return True
            
            elif self.wait_type == "element":
                if not self.selector:
                    self.store_result('error', "No selector provided for element wait")
                    return False
                
                by_method = self._get_by_method()
                if not by_method:
                    self.store_result('error', f"Unsupported selector type: {self.selector_type}")
                    return False
                
                wait = WebDriverWait(driver, self.duration)
                
                if self.condition == "presence":
                    element = wait.until(EC.presence_of_element_located((by_method, self.selector)))
                elif self.condition == "visible":
                    element = wait.until(EC.visibility_of_element_located((by_method, self.selector)))
                elif self.condition == "clickable":
                    element = wait.until(EC.element_to_be_clickable((by_method, self.selector)))
                elif self.condition == "invisible":
                    wait.until(EC.invisibility_of_element_located((by_method, self.selector)))
                    element = None
                else:
                    self.store_result('error', f"Unsupported condition: {self.condition}")
                    return False
                
                if element:
                    self.store_result('element_found', True)
                    self.store_result('element_text', element.text)
                    context['last_waited_element'] = self.selector
                
            elif self.wait_type == "url_contains":
                if not self.selector:  # Using selector as the URL fragment to wait for
                    self.store_result('error', "No URL fragment provided for URL wait")
                    return False
                
                wait = WebDriverWait(driver, self.duration)
                wait.until(EC.url_contains(self.selector))
                
            elif self.wait_type == "title_contains":
                if not self.selector:  # Using selector as the title fragment
                    self.store_result('error', "No title fragment provided for title wait")
                    return False
                
                wait = WebDriverWait(driver, self.duration)
                wait.until(EC.title_contains(self.selector))
                
            else:
                self.store_result('error', f"Unsupported wait type: {self.wait_type}")
                return False
            
            wait_time = time.time() - start_time
            self.store_result('actual_wait_time', wait_time)
            return True
            
        except TimeoutException:
            wait_time = time.time() - start_time
            self.store_result('actual_wait_time', wait_time)
            self.store_result('error', f"Wait condition not met within {self.duration}s")
            return False
        except Exception as e:
            self.store_result('error', str(e))
            return False
    
    def _get_by_method(self):
        """Get the appropriate By method for the selector type."""
        selector_map = {
            'css': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'tag': By.TAG_NAME
        }
        by_method = selector_map.get(self.selector_type)
        if by_method is None:
            raise ValueError(f"Unsupported selector type: {self.selector_type}")
        return by_method


class TTPAction(Action):
    """Action to execute a TTP within a journey."""
    
    def __init__(self, 
                 ttp: TTP,
                 target_url: Optional[str] = None,
                 name: Optional[str] = None, 
                 description: Optional[str] = None, 
                 expected_result: Optional[bool] = None):
        """
        Initialize TTP action.
        
        Args:
            ttp: TTP instance to execute
            target_url: Specific URL for TTP (if different from context)
            use_context_url: Whether to use current URL from context
            name: Optional custom name
            description: Optional custom description
            expected_result: Override TTP's expected result
        """
        self.ttp = ttp
        self.target_url = target_url
        
        name = name or f"Execute TTP: {ttp.name}"
        description = description or f"Execute TTP '{ttp.name}': {ttp.description}"
        expected_result = expected_result if expected_result is not None else ttp.expected_result
        
        super().__init__(name, description, expected_result)
    
    def execute(self, driver: WebDriver, context: Dict[str, Any]) -> bool:
        """
        Execute the TTP.
        
        Args:
            driver: WebDriver instance
            context: Shared context data
            
        Returns:
            True if TTP execution matches expected result, False otherwise
        """
        try:
            # Determine target URL
            if self.target_url:
                url = self.target_url
            elif 'current_url' in context:
                url = context['current_url']
            else:
                url = driver.current_url
            
            # Navigate to URL if needed
            if url != driver.current_url:
                driver.get(url)
            
            # Execute TTP authentication if required
            if self.ttp.requires_authentication():
                auth_success = self.ttp.authenticate(driver, url)
                if not auth_success:
                    self.store_result('error', 'TTP authentication failed')
                    return False
            
            # Execute TTP payloads
            ttp_results = []
            success_count = 0
            total_count = 0
            
            for payload in self.ttp.get_payloads():
                total_count += 1
                
                try:
                    # Execute step
                    self.ttp.execute_step(driver, payload)
                    
                    # Verify result
                    result = self.ttp.verify_result(driver)
                    
                    ttp_results.append({
                        'payload': str(payload),
                        'success': result,
                        'url': driver.current_url
                    })
                    
                    if result:
                        success_count += 1
                        
                except Exception as e:
                    ttp_results.append({
                        'payload': str(payload),
                        'success': False,
                        'error': str(e),
                        'url': driver.current_url
                    })
            
            # Store results
            self.store_result('ttp_name', self.ttp.name)
            self.store_result('total_payloads', total_count)
            self.store_result('successful_payloads', success_count)
            self.store_result('ttp_results', ttp_results)
            self.store_result('success_rate', success_count / total_count if total_count > 0 else 0)
            
            # Update context
            context[f'ttp_results_{self.ttp.name}'] = ttp_results
            context['last_ttp_success_count'] = success_count
            
            # Determine action success based on expected result
            has_successes = success_count > 0
            
            if self.expected_result:
                # Expecting TTP to find vulnerabilities/succeed
                return has_successes
            else:
                # Expecting TTP to fail (security controls working)
                return not has_successes
                
        except Exception as e:
            self.store_result('error', str(e))
            return False


class AssertAction(Action):
    """Action to assert conditions and validate state."""
    
    def __init__(self, 
                 assertion_type: str,
                 expected_value: str,
                 selector: Optional[str] = None,
                 selector_type: str = "css",
                 context_key: Optional[str] = None,
                 name: Optional[str] = None, 
                 description: Optional[str] = None, 
                 expected_result: bool = True):
        """
        Initialize assert action.
        
        Args:
            assertion_type: Type of assertion ('url_contains', 'element_text', 'element_present', 
                          'context_value', 'page_contains')
            expected_value: Expected value for the assertion
            selector: Element selector (if needed)
            selector_type: Type of selector
            context_key: Context key to check (for context assertions)
            name: Optional custom name
            description: Optional custom description
            expected_result: Whether assertion is expected to pass
        """
        self.assertion_type = assertion_type.lower()
        self.expected_value = expected_value
        self.selector = selector
        self.selector_type = (selector_type or "css").lower()
        self.context_key = context_key
        
        name = name or f"Assert {assertion_type}"
        description = description or f"Assert that {assertion_type} equals {expected_value}"
        super().__init__(name, description, expected_result)
    
    def execute(self, driver: WebDriver, context: Dict[str, Any]) -> bool:
        """
        Execute assertion.
        
        Args:
            driver: WebDriver instance
            context: Shared context data
            
        Returns:
            True if assertion passes, False otherwise
        """
        try:
            actual_value = None
            
            if self.assertion_type == "url_contains":
                actual_value = driver.current_url
                result = str(self.expected_value) in actual_value
                
            elif self.assertion_type == "url_equals":
                actual_value = driver.current_url
                result = actual_value == str(self.expected_value)
                
            elif self.assertion_type == "page_contains":
                actual_value = driver.page_source
                result = str(self.expected_value) in actual_value
                
            elif self.assertion_type == "element_present":
                try:
                    by_method = self._get_by_method()
                    element = driver.find_element(by_method, self.selector)
                    actual_value = True
                    result = actual_value == bool(self.expected_value)
                except NoSuchElementException:
                    actual_value = False
                    result = actual_value == bool(self.expected_value)
                    
            elif self.assertion_type == "element_text":
                if not self.selector:
                    self.store_result('error', "No selector provided for element text assertion")
                    return False
                    
                by_method = self._get_by_method()
                element = driver.find_element(by_method, self.selector)
                actual_value = element.text
                result = actual_value == str(self.expected_value)
                
            elif self.assertion_type == "element_text_contains":
                if not self.selector:
                    self.store_result('error', "No selector provided for element text assertion")
                    return False
                    
                by_method = self._get_by_method()
                element = driver.find_element(by_method, self.selector)
                actual_value = element.text
                result = str(self.expected_value) in actual_value
                
            elif self.assertion_type == "context_value":
                if not self.context_key:
                    self.store_result('error', "No context key provided for context assertion")
                    return False
                    
                actual_value = context.get(self.context_key)
                result = actual_value == self.expected_value
                
            else:
                self.store_result('error', f"Unsupported assertion type: {self.assertion_type}")
                return False
            
            # Store assertion results
            self.store_result('assertion_type', self.assertion_type)
            self.store_result('expected_value', self.expected_value)
            self.store_result('actual_value', actual_value)
            self.store_result('assertion_passed', result)
            
            return result
            
        except Exception as e:
            self.store_result('error', str(e))
            return False
    
    def _get_by_method(self):
        """Get the appropriate By method for the selector type."""
        selector_map = {
            'css': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'tag': By.TAG_NAME
        }
        by_method = selector_map.get(self.selector_type)
        if by_method is None:
            raise ValueError(f"Unsupported selector type: {self.selector_type}")
        return by_method