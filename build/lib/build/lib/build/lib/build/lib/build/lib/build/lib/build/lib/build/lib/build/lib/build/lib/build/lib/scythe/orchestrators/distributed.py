import time
import uuid
import random
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dataclasses import dataclass

from .base import Orchestrator, OrchestrationResult, OrchestrationStrategy, ExecutionContext, OrchestrationError
from ..core.ttp import TTP
from ..core.executor import TTPExecutor
from ..journeys.base import Journey
from ..journeys.executor import JourneyExecutor


@dataclass
class NetworkProxy:
    """Represents a network proxy configuration."""
    name: str
    proxy_url: str
    proxy_type: str = "http"  # http, https, socks4, socks5
    username: Optional[str] = None
    password: Optional[str] = None
    location: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_selenium_proxy(self) -> Dict[str, str]:
        """Convert to Selenium proxy configuration."""
        proxy_config = {
            'proxyType': 'MANUAL',
            f'{self.proxy_type}Proxy': self.proxy_url
        }
        
        if self.username and self.password:
            # Note: Selenium doesn't directly support proxy auth in this format
            # This would need to be handled differently in practice
            proxy_config['proxy_auth'] = f"{self.username}:{self.password}"
        
        return proxy_config


@dataclass
class CredentialSet:
    """Represents a set of authentication credentials."""
    name: str
    username: str
    password: str
    additional_data: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}
        if self.metadata is None:
            self.metadata = {}


class DistributedOrchestrator(Orchestrator):
    """
    Distributed orchestrator for network distribution scenarios.
    
    This orchestrator distributes test executions across multiple network
    endpoints (proxies) and can use different credential sets to simulate
    multiple users from different geographical locations.
    """
    
    def __init__(self, 
                 name: str = "Distributed Orchestrator",
                 description: str = "Orchestrator for distributed network testing",
                 strategy: OrchestrationStrategy = OrchestrationStrategy.PARALLEL,
                 max_workers: int = 5,
                 timeout: Optional[float] = None,
                 proxies: Optional[List[NetworkProxy]] = None,
                 credentials: Optional[List[CredentialSet]] = None,
                 proxy_rotation_strategy: str = "round_robin",
                 credential_rotation_strategy: str = "round_robin",
                 headless: bool = True):
        """
        Initialize the Distributed Orchestrator.
        
        Args:
            name: Name of the orchestrator
            description: Description of the orchestrator
            strategy: Orchestration strategy
            max_workers: Maximum number of concurrent workers
            timeout: Optional timeout for entire orchestration
            proxies: List of network proxies to use
            credentials: List of credential sets to use
            proxy_rotation_strategy: How to rotate proxies ("round_robin", "random", "sticky")
            credential_rotation_strategy: How to rotate credentials ("round_robin", "random", "sticky")
            headless: Whether to run browsers in headless mode
        """
        super().__init__(name, description, strategy, max_workers, timeout)
        self.proxies = proxies or []
        self.credentials = credentials or []
        self.proxy_rotation_strategy = proxy_rotation_strategy
        self.credential_rotation_strategy = credential_rotation_strategy
        self.headless = headless
        
        # Rotation state
        self.proxy_index = 0
        self.credential_index = 0
        self.rotation_lock = threading.Lock()
        self.execution_lock = threading.Lock()
        self.active_executions = {}
        
        # Validate configuration
        if not self.proxies:
            self.logger.warning("No proxies configured - tests will run from local network")
        if not self.credentials:
            self.logger.warning("No credentials configured - tests will use default authentication")
    
    def add_proxy(self, proxy: NetworkProxy) -> None:
        """Add a network proxy to the pool."""
        self.proxies.append(proxy)
        self.logger.info(f"Added proxy: {proxy.name} ({proxy.proxy_url})")
    
    def add_credential_set(self, credentials: CredentialSet) -> None:
        """Add a credential set to the pool."""
        self.credentials.append(credentials)
        self.logger.info(f"Added credentials: {credentials.name} ({credentials.username})")
    
    def orchestrate_ttp(self, 
                       ttp: TTP, 
                       target_url: str,
                       replications: int = 1,
                       **kwargs) -> OrchestrationResult:
        """
        Orchestrate distributed execution of a TTP.
        
        Args:
            ttp: TTP instance to orchestrate
            target_url: Target URL for the TTP
            replications: Number of times to replicate the TTP
            **kwargs: Additional parameters
            
        Returns:
            OrchestrationResult containing execution details
        """
        self._log_orchestration_start(ttp.name, "TTP", replications, target_url)
        
        start_time = time.time()
        results = []
        errors = []
        
        try:
            if self.strategy == OrchestrationStrategy.SEQUENTIAL:
                results, errors = self._execute_ttp_distributed_sequential(ttp, target_url, replications, **kwargs)
            elif self.strategy == OrchestrationStrategy.PARALLEL:
                results, errors = self._execute_ttp_distributed_parallel(ttp, target_url, replications, **kwargs)
            else:
                raise OrchestrationError(f"Unsupported strategy: {self.strategy}", self.name)
                
        except Exception as e:
            self.logger.error(f"Critical error in distributed TTP orchestration: {e}")
            errors.append(str(e))
        
        end_time = time.time()
        
        # Calculate metrics
        total_executions = len(results)
        successful_executions = sum(1 for r in results if r.get('success', False))
        
        # Create orchestration result
        orchestration_result = OrchestrationResult(
            orchestrator_name=self.name,
            strategy=self.strategy,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=total_executions - successful_executions,
            start_time=start_time,
            end_time=end_time,
            execution_time=end_time - start_time,
            results=results,
            errors=errors,
            metadata={
                'test_type': 'TTP',
                'test_name': ttp.name,
                'target_url': target_url,
                'replications': replications,
                'proxies_used': len(self.proxies),
                'credentials_used': len(self.credentials),
                'proxy_rotation_strategy': self.proxy_rotation_strategy,
                'credential_rotation_strategy': self.credential_rotation_strategy,
                'distribution_stats': self._calculate_distribution_stats(results),
                **self.metadata
            }
        )
        
        self._log_orchestration_end(orchestration_result)
        return orchestration_result
    
    def orchestrate_journey(self, 
                           journey: Journey, 
                           target_url: str,
                           replications: int = 1,
                           **kwargs) -> OrchestrationResult:
        """
        Orchestrate distributed execution of a Journey.
        
        Args:
            journey: Journey instance to orchestrate
            target_url: Target URL for the journey
            replications: Number of times to replicate the journey
            **kwargs: Additional parameters
            
        Returns:
            OrchestrationResult containing execution details
        """
        self._log_orchestration_start(journey.name, "Journey", replications, target_url)
        
        start_time = time.time()
        results = []
        errors = []
        
        try:
            if self.strategy == OrchestrationStrategy.SEQUENTIAL:
                results, errors = self._execute_journey_distributed_sequential(journey, target_url, replications, **kwargs)
            elif self.strategy == OrchestrationStrategy.PARALLEL:
                results, errors = self._execute_journey_distributed_parallel(journey, target_url, replications, **kwargs)
            else:
                raise OrchestrationError(f"Unsupported strategy: {self.strategy}", self.name)
                
        except Exception as e:
            self.logger.error(f"Critical error in distributed Journey orchestration: {e}")
            errors.append(str(e))
        
        end_time = time.time()
        
        # Calculate metrics
        total_executions = len(results)
        successful_executions = sum(1 for r in results if r.get('overall_success', False))
        
        # Create orchestration result
        orchestration_result = OrchestrationResult(
            orchestrator_name=self.name,
            strategy=self.strategy,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=total_executions - successful_executions,
            start_time=start_time,
            end_time=end_time,
            execution_time=end_time - start_time,
            results=results,
            errors=errors,
            metadata={
                'test_type': 'Journey',
                'test_name': journey.name,
                'target_url': target_url,
                'replications': replications,
                'proxies_used': len(self.proxies),
                'credentials_used': len(self.credentials),
                'proxy_rotation_strategy': self.proxy_rotation_strategy,
                'credential_rotation_strategy': self.credential_rotation_strategy,
                'distribution_stats': self._calculate_distribution_stats(results),
                **self.metadata
            }
        )
        
        self._log_orchestration_end(orchestration_result)
        return orchestration_result
    
    def _execute_ttp_distributed_sequential(self, 
                                           ttp: TTP, 
                                           target_url: str, 
                                           replications: int,
                                           **kwargs) -> Tuple[List[Dict], List[str]]:
        """Execute TTP replications sequentially across distributed network."""
        results = []
        errors = []
        
        for i in range(replications):
            # Initialize variables to avoid unbound errors
            context = None
            proxy = None
            credentials = None
            
            try:
                # Get proxy and credentials for this execution
                proxy, credentials = self._get_execution_resources(i)
                
                context = ExecutionContext(
                    execution_id=str(uuid.uuid4()),
                    test_name=ttp.name,
                    target_url=target_url,
                    replication_number=i + 1,
                    total_replications=replications,
                    metadata={
                        'proxy': proxy.name if proxy else None,
                        'credentials': credentials.name if credentials else None,
                        'proxy_location': proxy.location if proxy else None
                    }
                )
                
                self.logger.info(f"Executing distributed TTP {i+1}/{replications}")
                if proxy:
                    self.logger.info(f"  Using proxy: {proxy.name} ({proxy.location or 'unknown location'})")
                if credentials:
                    self.logger.info(f"  Using credentials: {credentials.name}")
                
                # Execute single TTP instance
                result = self._execute_single_distributed_ttp(ttp, target_url, context, proxy, credentials, **kwargs)
                results.append(result)
                
            except Exception as e:
                error_msg = f"Error in distributed TTP execution {i+1}: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                
                # Add failed result
                results.append({
                    'execution_id': context.execution_id if context else str(uuid.uuid4()),
                    'replication_number': i + 1,
                    'success': False,
                    'error': str(e),
                    'execution_time': 0,
                    'proxy_name': proxy.name if proxy else None,
                    'credentials_name': credentials.name if credentials else None
                })
        
        return results, errors
    
    def _execute_ttp_distributed_parallel(self, 
                                         ttp: TTP, 
                                         target_url: str, 
                                         replications: int,
                                         **kwargs) -> Tuple[List[Dict], List[str]]:
        """Execute TTP replications in parallel across distributed network."""
        results = []
        errors = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all executions
            future_to_context = {}
            
            for i in range(replications):
                # Get proxy and credentials for this execution
                proxy, credentials = self._get_execution_resources(i)
                
                context = ExecutionContext(
                    execution_id=str(uuid.uuid4()),
                    test_name=ttp.name,
                    target_url=target_url,
                    replication_number=i + 1,
                    total_replications=replications,
                    metadata={
                        'proxy': proxy.name if proxy else None,
                        'credentials': credentials.name if credentials else None,
                        'proxy_location': proxy.location if proxy else None
                    }
                )
                
                future = executor.submit(
                    self._execute_single_distributed_ttp, 
                    ttp, target_url, context, proxy, credentials, **kwargs
                )
                future_to_context[future] = context
                
                self.logger.info(f"Submitted distributed TTP execution {i+1}/{replications}")
                if proxy:
                    self.logger.info(f"  Proxy: {proxy.name}")
                if credentials:
                    self.logger.info(f"  Credentials: {credentials.name}")
            
            # Collect results as they complete
            for future in as_completed(future_to_context, timeout=self.timeout):
                context = future_to_context[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    self.logger.info(f"Completed distributed TTP execution {context.replication_number}/{replications}")
                    
                except Exception as e:
                    error_msg = f"Error in distributed TTP execution {context.replication_number}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
                    
                    # Add failed result
                    proxy = context.metadata.get('proxy')
                    credentials = context.metadata.get('credentials')
                    results.append({
                        'execution_id': context.execution_id,
                        'replication_number': context.replication_number,
                        'success': False,
                        'error': str(e),
                        'execution_time': 0,
                        'proxy_name': proxy,
                        'credentials_name': credentials
                    })
        
        return results, errors
    
    def _execute_journey_distributed_sequential(self, 
                                               journey: Journey, 
                                               target_url: str, 
                                               replications: int,
                                               **kwargs) -> Tuple[List[Dict], List[str]]:
        """Execute Journey replications sequentially across distributed network."""
        results = []
        errors = []
        
        for i in range(replications):
            # Initialize variables to avoid unbound errors
            context = None
            proxy = None
            credentials = None
            
            try:
                # Get proxy and credentials for this execution
                proxy, credentials = self._get_execution_resources(i)
                
                context = ExecutionContext(
                    execution_id=str(uuid.uuid4()),
                    test_name=journey.name,
                    target_url=target_url,
                    replication_number=i + 1,
                    total_replications=replications,
                    metadata={
                        'proxy': proxy.name if proxy else None,
                        'credentials': credentials.name if credentials else None,
                        'proxy_location': proxy.location if proxy else None
                    }
                )
                
                self.logger.info(f"Executing distributed Journey {i+1}/{replications}")
                if proxy:
                    self.logger.info(f"  Using proxy: {proxy.name} ({proxy.location or 'unknown location'})")
                if credentials:
                    self.logger.info(f"  Using credentials: {credentials.name}")
                
                # Execute single Journey instance
                result = self._execute_single_distributed_journey(journey, target_url, context, proxy, credentials, **kwargs)
                results.append(result)
                
            except Exception as e:
                error_msg = f"Error in distributed Journey execution {i+1}: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                
                # Add failed result
                results.append({
                    'execution_id': context.execution_id if context else str(uuid.uuid4()),
                    'replication_number': i + 1,
                    'overall_success': False,
                    'error': str(e),
                    'execution_time': 0,
                    'proxy_name': proxy.name if proxy else None,
                    'credentials_name': credentials.name if credentials else None
                })
        
        return results, errors
    
    def _execute_journey_distributed_parallel(self, 
                                             journey: Journey, 
                                             target_url: str, 
                                             replications: int,
                                             **kwargs) -> Tuple[List[Dict], List[str]]:
        """Execute Journey replications in parallel across distributed network."""
        results = []
        errors = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all executions
            future_to_context = {}
            
            for i in range(replications):
                # Get proxy and credentials for this execution
                proxy, credentials = self._get_execution_resources(i)
                
                context = ExecutionContext(
                    execution_id=str(uuid.uuid4()),
                    test_name=journey.name,
                    target_url=target_url,
                    replication_number=i + 1,
                    total_replications=replications,
                    metadata={
                        'proxy': proxy.name if proxy else None,
                        'credentials': credentials.name if credentials else None,
                        'proxy_location': proxy.location if proxy else None
                    }
                )
                
                future = executor.submit(
                    self._execute_single_distributed_journey, 
                    journey, target_url, context, proxy, credentials, **kwargs
                )
                future_to_context[future] = context
                
                self.logger.info(f"Submitted distributed Journey execution {i+1}/{replications}")
                if proxy:
                    self.logger.info(f"  Proxy: {proxy.name}")
                if credentials:
                    self.logger.info(f"  Credentials: {credentials.name}")
            
            # Collect results as they complete
            for future in as_completed(future_to_context, timeout=self.timeout):
                context = future_to_context[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    self.logger.info(f"Completed distributed Journey execution {context.replication_number}/{replications}")
                    
                except Exception as e:
                    error_msg = f"Error in distributed Journey execution {context.replication_number}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
                    
                    # Add failed result
                    proxy = context.metadata.get('proxy')
                    credentials = context.metadata.get('credentials')
                    results.append({
                        'execution_id': context.execution_id,
                        'replication_number': context.replication_number,
                        'overall_success': False,
                        'error': str(e),
                        'execution_time': 0,
                        'proxy_name': proxy,
                        'credentials_name': credentials
                    })
        
        return results, errors
    
    def _get_execution_resources(self, execution_index: int) -> Tuple[Optional[NetworkProxy], Optional[CredentialSet]]:
        """Get proxy and credentials for a specific execution."""
        with self.rotation_lock:
            proxy = self._get_next_proxy(execution_index) if self.proxies else None
            credentials = self._get_next_credentials(execution_index) if self.credentials else None
            return proxy, credentials
    
    def _get_next_proxy(self, execution_index: int) -> Optional[NetworkProxy]:
        """Get the next proxy based on rotation strategy."""
        if not self.proxies:
            return None
        
        if self.proxy_rotation_strategy == "round_robin":
            proxy = self.proxies[self.proxy_index % len(self.proxies)]
            self.proxy_index += 1
            return proxy
        elif self.proxy_rotation_strategy == "random":
            return random.choice(self.proxies)
        elif self.proxy_rotation_strategy == "sticky":
            # Use same proxy for all executions
            return self.proxies[0]
        else:
            return self.proxies[execution_index % len(self.proxies)]
    
    def _get_next_credentials(self, execution_index: int) -> Optional[CredentialSet]:
        """Get the next credentials based on rotation strategy."""
        if not self.credentials:
            return None
        
        if self.credential_rotation_strategy == "round_robin":
            creds = self.credentials[self.credential_index % len(self.credentials)]
            self.credential_index += 1
            return creds
        elif self.credential_rotation_strategy == "random":
            return random.choice(self.credentials)
        elif self.credential_rotation_strategy == "sticky":
            # Use same credentials for all executions
            return self.credentials[0]
        else:
            return self.credentials[execution_index % len(self.credentials)]
    
    def _execute_single_distributed_ttp(self, 
                                       ttp: TTP, 
                                       target_url: str, 
                                       context: ExecutionContext,
                                       proxy: Optional[NetworkProxy],
                                       credentials: Optional[CredentialSet],
                                       **kwargs) -> Dict[str, Any]:
        """Execute a single TTP instance with distributed configuration."""
        context.start()
        
        with self.execution_lock:
            self.active_executions[context.execution_id] = context
        
        try:
            # Extract parameters
            behavior = kwargs.get('behavior')
            delay = kwargs.get('delay', 1)
            
            # Configure TTP with distributed credentials if available
            if credentials and hasattr(ttp, 'authentication'):
                # This would need to be implemented based on TTP's authentication setup
                # For now, we'll store credentials in context for potential use
                context.metadata['username'] = credentials.username
                context.metadata['password'] = credentials.password
                context.metadata['additional_data'] = credentials.additional_data
            
            # Create TTP executor with proxy configuration
            # Note: Actual proxy configuration would need to be implemented
            # in a custom WebDriver setup
            executor = TTPExecutor(
                ttp=ttp,
                target_url=target_url,
                headless=self.headless,
                delay=delay,
                behavior=behavior
            )
            
            # TODO: Configure executor with proxy settings
            # This would require extending TTPExecutor to support proxy configuration
            
            executor.run()
            
            # Determine success based on expected vs actual results
            has_results = len(executor.results) > 0
            expected_success = ttp.expected_result
            
            success = (expected_success and has_results) or (not expected_success and not has_results)
            
            result = {
                'execution_id': context.execution_id,
                'replication_number': context.replication_number,
                'test_name': ttp.name,
                'target_url': target_url,
                'success': success,
                'expected_result': expected_success,
                'actual_result': has_results,
                'results_count': len(executor.results),
                'results': executor.results,
                'execution_time': 0,  # Will be updated below
                'timestamp': time.time(),
                'proxy_name': proxy.name if proxy else None,
                'proxy_location': proxy.location if proxy else None,
                'credentials_name': credentials.name if credentials else None,
                'distributed_metadata': context.metadata
            }
            
            context.end(result)
            result['execution_time'] = context.execution_time
            
            return result
            
        except Exception as e:
            context.end(error=e)
            raise
        
        finally:
            with self.execution_lock:
                self.active_executions.pop(context.execution_id, None)
    
    def _execute_single_distributed_journey(self, 
                                           journey: Journey, 
                                           target_url: str, 
                                           context: ExecutionContext,
                                           proxy: Optional[NetworkProxy],
                                           credentials: Optional[CredentialSet],
                                           **kwargs) -> Dict[str, Any]:
        """Execute a single Journey instance with distributed configuration."""
        context.start()
        
        with self.execution_lock:
            self.active_executions[context.execution_id] = context
        
        try:
            # Extract parameters
            behavior = kwargs.get('behavior')
            
            # Configure Journey with distributed credentials if available
            if credentials:
                # Set credentials in journey context for actions to use
                journey.set_context('distributed_username', credentials.username)
                journey.set_context('distributed_password', credentials.password)
                if credentials.additional_data:
                    for key, value in credentials.additional_data.items():
                        journey.set_context(f'distributed_{key}', value)
            
            # Create Journey executor with proxy configuration
            executor = JourneyExecutor(
                journey=journey,
                target_url=target_url,
                headless=self.headless,
                behavior=behavior
            )
            
            # TODO: Configure executor with proxy settings
            # This would require extending JourneyExecutor to support proxy configuration
            
            journey_result = executor.run()
            
            # Add orchestration context to result
            result = journey_result.copy()
            result.update({
                'execution_id': context.execution_id,
                'replication_number': context.replication_number,
                'timestamp': time.time(),
                'proxy_name': proxy.name if proxy else None,
                'proxy_location': proxy.location if proxy else None,
                'credentials_name': credentials.name if credentials else None,
                'distributed_metadata': context.metadata
            })
            
            context.end(result)
            result['execution_time'] = context.execution_time
            
            return result
            
        except Exception as e:
            context.end(error=e)
            raise
        
        finally:
            with self.execution_lock:
                self.active_executions.pop(context.execution_id, None)
    
    def _calculate_distribution_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics about proxy and credential distribution."""
        proxy_usage = {}
        credential_usage = {}
        location_usage = {}
        
        for result in results:
            proxy_name = result.get('proxy_name')
            if proxy_name:
                proxy_usage[proxy_name] = proxy_usage.get(proxy_name, 0) + 1
            
            credentials_name = result.get('credentials_name')
            if credentials_name:
                credential_usage[credentials_name] = credential_usage.get(credentials_name, 0) + 1
            
            proxy_location = result.get('proxy_location')
            if proxy_location:
                location_usage[proxy_location] = location_usage.get(proxy_location, 0) + 1
        
        return {
            'proxy_usage': proxy_usage,
            'credential_usage': credential_usage,
            'location_usage': location_usage,
            'total_proxies_configured': len(self.proxies),
            'total_credentials_configured': len(self.credentials),
            'proxies_used': len(proxy_usage),
            'credentials_used': len(credential_usage),
            'locations_used': len(location_usage)
        }
    
    def get_proxy_stats(self) -> Dict[str, Any]:
        """Get statistics about proxy configuration and usage."""
        return {
            'total_proxies': len(self.proxies),
            'proxy_rotation_strategy': self.proxy_rotation_strategy,
            'proxies': [
                {
                    'name': proxy.name,
                    'url': proxy.proxy_url,
                    'type': proxy.proxy_type,
                    'location': proxy.location,
                    'has_auth': bool(proxy.username and proxy.password)
                }
                for proxy in self.proxies
            ]
        }
    
    def get_credential_stats(self) -> Dict[str, Any]:
        """Get statistics about credential configuration and usage."""
        return {
            'total_credentials': len(self.credentials),
            'credential_rotation_strategy': self.credential_rotation_strategy,
            'credentials': [
                {
                    'name': creds.name,
                    'username': creds.username,
                    'has_additional_data': bool(creds.additional_data)
                }
                for creds in self.credentials
            ]
        }