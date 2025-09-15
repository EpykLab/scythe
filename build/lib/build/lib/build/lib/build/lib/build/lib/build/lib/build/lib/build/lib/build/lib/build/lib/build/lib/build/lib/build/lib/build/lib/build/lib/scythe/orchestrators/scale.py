import time
import uuid
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .base import Orchestrator, OrchestrationResult, OrchestrationStrategy, ExecutionContext, OrchestrationError
from ..core.ttp import TTP
from ..core.executor import TTPExecutor
from ..journeys.base import Journey
from ..journeys.executor import JourneyExecutor


class ScaleOrchestrator(Orchestrator):
    """
    Scale orchestrator for load testing scenarios.
    
    This orchestrator is designed to replicate TTPs or Journeys multiple times
    to test application behavior under load. It supports both sequential and
    parallel execution patterns.
    """
    
    def __init__(self, 
                 name: str = "Scale Orchestrator",
                 description: str = "Orchestrator for scale and load testing",
                 strategy: OrchestrationStrategy = OrchestrationStrategy.PARALLEL,
                 max_workers: int = 10,
                 timeout: Optional[float] = None,
                 ramp_up_delay: float = 0.0,
                 cool_down_delay: float = 0.0,
                 headless: bool = True):
        """
        Initialize the Scale Orchestrator.
        
        Args:
            name: Name of the orchestrator
            description: Description of the orchestrator
            strategy: Orchestration strategy (SEQUENTIAL or PARALLEL)
            max_workers: Maximum number of concurrent workers
            timeout: Optional timeout for entire orchestration
            ramp_up_delay: Delay between starting each execution (seconds)
            cool_down_delay: Delay after each execution completes (seconds)
            headless: Whether to run browsers in headless mode
        """
        super().__init__(name, description, strategy, max_workers, timeout)
        self.ramp_up_delay = ramp_up_delay
        self.cool_down_delay = cool_down_delay
        self.headless = headless
        self.execution_lock = threading.Lock()
        self.active_executions = {}
        
    def orchestrate_ttp(self, 
                       ttp: TTP, 
                       target_url: str,
                       replications: int = 1,
                       **kwargs) -> OrchestrationResult:
        """
        Orchestrate scaled execution of a TTP.
        
        Args:
            ttp: TTP instance to orchestrate
            target_url: Target URL for the TTP
            replications: Number of times to replicate the TTP
            **kwargs: Additional parameters (behavior, delay, etc.)
            
        Returns:
            OrchestrationResult containing execution details
        """
        self._log_orchestration_start(ttp.name, "TTP", replications, target_url)
        
        start_time = time.time()
        results = []
        errors = []
        
        try:
            if self.strategy == OrchestrationStrategy.SEQUENTIAL:
                results, errors = self._execute_ttp_sequential(ttp, target_url, replications, **kwargs)
            elif self.strategy == OrchestrationStrategy.PARALLEL:
                results, errors = self._execute_ttp_parallel(ttp, target_url, replications, **kwargs)
            else:
                raise OrchestrationError(f"Unsupported strategy: {self.strategy}", self.name)
                
        except Exception as e:
            self.logger.error(f"Critical error in TTP orchestration: {e}")
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
                'ramp_up_delay': self.ramp_up_delay,
                'cool_down_delay': self.cool_down_delay,
                'headless': self.headless,
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
        Orchestrate scaled execution of a Journey.
        
        Args:
            journey: Journey instance to orchestrate
            target_url: Target URL for the journey
            replications: Number of times to replicate the journey
            **kwargs: Additional parameters (behavior, etc.)
            
        Returns:
            OrchestrationResult containing execution details
        """
        self._log_orchestration_start(journey.name, "Journey", replications, target_url)
        
        start_time = time.time()
        results = []
        errors = []
        
        try:
            if self.strategy == OrchestrationStrategy.SEQUENTIAL:
                results, errors = self._execute_journey_sequential(journey, target_url, replications, **kwargs)
            elif self.strategy == OrchestrationStrategy.PARALLEL:
                results, errors = self._execute_journey_parallel(journey, target_url, replications, **kwargs)
            else:
                raise OrchestrationError(f"Unsupported strategy: {self.strategy}", self.name)
                
        except Exception as e:
            self.logger.error(f"Critical error in Journey orchestration: {e}")
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
                'ramp_up_delay': self.ramp_up_delay,
                'cool_down_delay': self.cool_down_delay,
                'headless': self.headless,
                **self.metadata
            }
        )
        
        self._log_orchestration_end(orchestration_result)
        return orchestration_result
    
    def _execute_ttp_sequential(self, 
                               ttp: TTP, 
                               target_url: str, 
                               replications: int,
                               **kwargs) -> tuple:
        """Execute TTP replications sequentially."""
        results = []
        errors = []
        
        for i in range(replications):
            context = ExecutionContext(
                execution_id=str(uuid.uuid4()),
                test_name=ttp.name,
                target_url=target_url,
                replication_number=i + 1,
                total_replications=replications
            )
            
            try:
                # Apply ramp-up delay
                if i > 0 and self.ramp_up_delay > 0:
                    self.logger.info(f"Ramp-up delay: {self.ramp_up_delay}s before execution {i+1}")
                    time.sleep(self.ramp_up_delay)
                
                self.logger.info(f"Executing TTP replication {i+1}/{replications}")
                
                # Execute single TTP instance
                result = self._execute_single_ttp(ttp, target_url, context, **kwargs)
                results.append(result)
                
                # Apply cool-down delay
                if self.cool_down_delay > 0:
                    self.logger.info(f"Cool-down delay: {self.cool_down_delay}s after execution {i+1}")
                    time.sleep(self.cool_down_delay)
                    
            except Exception as e:
                error_msg = f"Error in TTP execution {i+1}: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                
                # Add failed result
                results.append({
                    'execution_id': context.execution_id,
                    'replication_number': i + 1,
                    'success': False,
                    'error': str(e),
                    'execution_time': 0
                })
        
        return results, errors
    
    def _execute_ttp_parallel(self, 
                             ttp: TTP, 
                             target_url: str, 
                             replications: int,
                             **kwargs) -> tuple:
        """Execute TTP replications in parallel."""
        results = []
        errors = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all executions
            future_to_context = {}
            
            for i in range(replications):
                context = ExecutionContext(
                    execution_id=str(uuid.uuid4()),
                    test_name=ttp.name,
                    target_url=target_url,
                    replication_number=i + 1,
                    total_replications=replications
                )
                
                # Apply ramp-up delay by staggering submission
                if i > 0 and self.ramp_up_delay > 0:
                    time.sleep(self.ramp_up_delay)
                
                future = executor.submit(self._execute_single_ttp, ttp, target_url, context, **kwargs)
                future_to_context[future] = context
                
                self.logger.info(f"Submitted TTP execution {i+1}/{replications}")
            
            # Collect results as they complete
            for future in as_completed(future_to_context, timeout=self.timeout):
                context = future_to_context[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    self.logger.info(f"Completed TTP execution {context.replication_number}/{replications}")
                    
                    # Apply cool-down delay
                    if self.cool_down_delay > 0:
                        time.sleep(self.cool_down_delay)
                        
                except Exception as e:
                    error_msg = f"Error in TTP execution {context.replication_number}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
                    
                    # Add failed result
                    results.append({
                        'execution_id': context.execution_id,
                        'replication_number': context.replication_number,
                        'success': False,
                        'error': str(e),
                        'execution_time': 0
                    })
        
        return results, errors
    
    def _execute_journey_sequential(self, 
                                   journey: Journey, 
                                   target_url: str, 
                                   replications: int,
                                   **kwargs) -> tuple:
        """Execute Journey replications sequentially."""
        results = []
        errors = []
        
        for i in range(replications):
            context = ExecutionContext(
                execution_id=str(uuid.uuid4()),
                test_name=journey.name,
                target_url=target_url,
                replication_number=i + 1,
                total_replications=replications
            )
            
            try:
                # Apply ramp-up delay
                if i > 0 and self.ramp_up_delay > 0:
                    self.logger.info(f"Ramp-up delay: {self.ramp_up_delay}s before execution {i+1}")
                    time.sleep(self.ramp_up_delay)
                
                self.logger.info(f"Executing Journey replication {i+1}/{replications}")
                
                # Execute single Journey instance
                result = self._execute_single_journey(journey, target_url, context, **kwargs)
                results.append(result)
                
                # Apply cool-down delay
                if self.cool_down_delay > 0:
                    self.logger.info(f"Cool-down delay: {self.cool_down_delay}s after execution {i+1}")
                    time.sleep(self.cool_down_delay)
                    
            except Exception as e:
                error_msg = f"Error in Journey execution {i+1}: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                
                # Add failed result
                results.append({
                    'execution_id': context.execution_id,
                    'replication_number': i + 1,
                    'overall_success': False,
                    'error': str(e),
                    'execution_time': 0
                })
        
        return results, errors
    
    def _execute_journey_parallel(self, 
                                 journey: Journey, 
                                 target_url: str, 
                                 replications: int,
                                 **kwargs) -> tuple:
        """Execute Journey replications in parallel."""
        results = []
        errors = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all executions
            future_to_context = {}
            
            for i in range(replications):
                context = ExecutionContext(
                    execution_id=str(uuid.uuid4()),
                    test_name=journey.name,
                    target_url=target_url,
                    replication_number=i + 1,
                    total_replications=replications
                )
                
                # Apply ramp-up delay by staggering submission
                if i > 0 and self.ramp_up_delay > 0:
                    time.sleep(self.ramp_up_delay)
                
                future = executor.submit(self._execute_single_journey, journey, target_url, context, **kwargs)
                future_to_context[future] = context
                
                self.logger.info(f"Submitted Journey execution {i+1}/{replications}")
            
            # Collect results as they complete
            for future in as_completed(future_to_context, timeout=self.timeout):
                context = future_to_context[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    self.logger.info(f"Completed Journey execution {context.replication_number}/{replications}")
                    
                    # Apply cool-down delay
                    if self.cool_down_delay > 0:
                        time.sleep(self.cool_down_delay)
                        
                except Exception as e:
                    error_msg = f"Error in Journey execution {context.replication_number}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
                    
                    # Add failed result
                    results.append({
                        'execution_id': context.execution_id,
                        'replication_number': context.replication_number,
                        'overall_success': False,
                        'error': str(e),
                        'execution_time': 0
                    })
        
        return results, errors
    
    def _execute_single_ttp(self, 
                           ttp: TTP, 
                           target_url: str, 
                           context: ExecutionContext,
                           **kwargs) -> Dict[str, Any]:
        """Execute a single TTP instance."""
        context.start()
        
        with self.execution_lock:
            self.active_executions[context.execution_id] = context
        
        try:
            # Extract parameters
            behavior = kwargs.get('behavior')
            delay = kwargs.get('delay', 1)
            
            # Create and run TTP executor
            executor = TTPExecutor(
                ttp=ttp,
                target_url=target_url,
                headless=self.headless,
                delay=delay,
                behavior=behavior
            )
            
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
                'timestamp': time.time()
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
    
    def _execute_single_journey(self, 
                               journey: Journey, 
                               target_url: str, 
                               context: ExecutionContext,
                               **kwargs) -> Dict[str, Any]:
        """Execute a single Journey instance."""
        context.start()
        
        with self.execution_lock:
            self.active_executions[context.execution_id] = context
        
        try:
            # Extract parameters
            behavior = kwargs.get('behavior')
            
            # Create and run Journey executor
            executor = JourneyExecutor(
                journey=journey,
                target_url=target_url,
                headless=self.headless,
                behavior=behavior
            )
            
            journey_result = executor.run()
            
            # Add orchestration context to result
            result = journey_result.copy()
            result.update({
                'execution_id': context.execution_id,
                'replication_number': context.replication_number,
                'timestamp': time.time()
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
    
    def get_active_executions(self) -> Dict[str, ExecutionContext]:
        """Get currently active executions."""
        with self.execution_lock:
            return self.active_executions.copy()
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Get status of current orchestration."""
        with self.execution_lock:
            return {
                'active_executions': len(self.active_executions),
                'max_workers': self.max_workers,
                'strategy': self.strategy.value,
                'executions': {
                    execution_id: {
                        'test_name': context.test_name,
                        'replication_number': context.replication_number,
                        'running_time': time.time() - context.start_time if context.start_time else 0
                    }
                    for execution_id, context in self.active_executions.items()
                }
            }