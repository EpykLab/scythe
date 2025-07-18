import time
import uuid
import math
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dataclasses import dataclass

from .base import Orchestrator, OrchestrationResult, OrchestrationStrategy, ExecutionContext
from ..core.ttp import TTP
from ..core.executor import TTPExecutor
from ..journeys.base import Journey
from ..journeys.executor import JourneyExecutor


@dataclass
class BatchConfiguration:
    """Configuration for batch processing."""
    batch_size: int
    batch_delay: float = 0.0
    max_concurrent_batches: int = 1
    retry_failed_batches: bool = False
    max_retries: int = 1


class BatchOrchestrator(Orchestrator):
    """
    Batch orchestrator for resource-limited scenarios.
    
    This orchestrator divides test executions into batches to work within
    resource constraints such as limited proxies, credentials, or browser
    instances. It supports batching with customizable delays and concurrency.
    """
    
    def __init__(self, 
                 name: str = "Batch Orchestrator",
                 description: str = "Orchestrator for batch processing with resource constraints",
                 strategy: OrchestrationStrategy = OrchestrationStrategy.BATCH,
                 max_workers: int = 4,
                 timeout: Optional[float] = None,
                 batch_config: Optional[BatchConfiguration] = None,
                 headless: bool = True):
        """
        Initialize the Batch Orchestrator.
        
        Args:
            name: Name of the orchestrator
            description: Description of the orchestrator
            strategy: Orchestration strategy (typically BATCH)
            max_workers: Maximum number of concurrent workers per batch
            timeout: Optional timeout for entire orchestration
            batch_config: Batch processing configuration
            headless: Whether to run browsers in headless mode
        """
        super().__init__(name, description, strategy, max_workers, timeout)
        self.batch_config = batch_config or BatchConfiguration(batch_size=10)
        self.headless = headless
        self.execution_lock = threading.Lock()
        self.active_executions = {}
        self.completed_batches = []
        self.failed_batches = []
        
        # Validate batch configuration
        if self.batch_config.batch_size <= 0:
            raise ValueError("Batch size must be greater than 0")
        if self.batch_config.max_concurrent_batches <= 0:
            raise ValueError("Max concurrent batches must be greater than 0")
    
    def orchestrate_ttp(self, 
                       ttp: TTP, 
                       target_url: str,
                       replications: int = 1,
                       **kwargs) -> OrchestrationResult:
        """
        Orchestrate batched execution of a TTP.
        
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
        all_results = []
        all_errors = []
        
        # Calculate batch information
        num_batches = math.ceil(replications / self.batch_config.batch_size)
        
        try:
            self.logger.info(f"Dividing {replications} executions into {num_batches} batches of {self.batch_config.batch_size}")
            
            # Execute batches
            for batch_num in range(num_batches):
                batch_start = batch_num * self.batch_config.batch_size
                batch_end = min((batch_num + 1) * self.batch_config.batch_size, replications)
                batch_size = batch_end - batch_start
                
                self.logger.info(f"Executing batch {batch_num + 1}/{num_batches} (executions {batch_start + 1}-{batch_end})")
                
                # Execute batch
                batch_results, batch_errors = self._execute_ttp_batch(
                    ttp, target_url, batch_num, batch_size, batch_start, **kwargs
                )
                
                all_results.extend(batch_results)
                all_errors.extend(batch_errors)
                
                # Store batch information
                batch_info = {
                    'batch_number': batch_num + 1,
                    'batch_size': batch_size,
                    'successful_executions': sum(1 for r in batch_results if r.get('success', False)),
                    'failed_executions': sum(1 for r in batch_results if not r.get('success', False)),
                    'errors': batch_errors
                }
                
                if batch_errors:
                    self.failed_batches.append(batch_info)
                    
                    # Retry failed batch if configured
                    if (self.batch_config.retry_failed_batches and 
                        batch_info['failed_executions'] > 0 and
                        len([b for b in self.failed_batches if b['batch_number'] == batch_num + 1]) <= self.batch_config.max_retries):
                        
                        self.logger.warning(f"Retrying failed batch {batch_num + 1}")
                        retry_results, retry_errors = self._execute_ttp_batch(
                            ttp, target_url, batch_num, batch_size, batch_start, retry=True, **kwargs
                        )
                        
                        # Replace failed results with retry results
                        all_results = [r for r in all_results if not (
                            r.get('batch_number') == batch_num + 1 and not r.get('success', False)
                        )]
                        all_results.extend(retry_results)
                        all_errors.extend(retry_errors)
                else:
                    self.completed_batches.append(batch_info)
                
                # Delay between batches
                if batch_num < num_batches - 1 and self.batch_config.batch_delay > 0:
                    self.logger.info(f"Batch delay: {self.batch_config.batch_delay}s before next batch")
                    time.sleep(self.batch_config.batch_delay)
                
        except Exception as e:
            self.logger.error(f"Critical error in batch TTP orchestration: {e}")
            all_errors.append(str(e))
        
        end_time = time.time()
        
        # Calculate metrics
        total_executions = len(all_results)
        successful_executions = sum(1 for r in all_results if r.get('success', False))
        
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
            results=all_results,
            errors=all_errors,
            metadata={
                'test_type': 'TTP',
                'test_name': ttp.name,
                'target_url': target_url,
                'replications': replications,
                'total_batches': num_batches,
                'completed_batches': len(self.completed_batches),
                'failed_batches': len(self.failed_batches),
                'batch_size': self.batch_config.batch_size,
                'batch_delay': self.batch_config.batch_delay,
                'max_concurrent_batches': self.batch_config.max_concurrent_batches,
                'retry_enabled': self.batch_config.retry_failed_batches,
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
        Orchestrate batched execution of a Journey.
        
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
        all_results = []
        all_errors = []
        
        # Calculate batch information
        num_batches = math.ceil(replications / self.batch_config.batch_size)
        
        try:
            self.logger.info(f"Dividing {replications} executions into {num_batches} batches of {self.batch_config.batch_size}")
            
            # Execute batches
            for batch_num in range(num_batches):
                batch_start = batch_num * self.batch_config.batch_size
                batch_end = min((batch_num + 1) * self.batch_config.batch_size, replications)
                batch_size = batch_end - batch_start
                
                self.logger.info(f"Executing batch {batch_num + 1}/{num_batches} (executions {batch_start + 1}-{batch_end})")
                
                # Execute batch
                batch_results, batch_errors = self._execute_journey_batch(
                    journey, target_url, batch_num, batch_size, batch_start, **kwargs
                )
                
                all_results.extend(batch_results)
                all_errors.extend(batch_errors)
                
                # Store batch information
                batch_info = {
                    'batch_number': batch_num + 1,
                    'batch_size': batch_size,
                    'successful_executions': sum(1 for r in batch_results if r.get('overall_success', False)),
                    'failed_executions': sum(1 for r in batch_results if not r.get('overall_success', False)),
                    'errors': batch_errors
                }
                
                if batch_errors:
                    self.failed_batches.append(batch_info)
                    
                    # Retry failed batch if configured
                    if (self.batch_config.retry_failed_batches and 
                        batch_info['failed_executions'] > 0 and
                        len([b for b in self.failed_batches if b['batch_number'] == batch_num + 1]) <= self.batch_config.max_retries):
                        
                        self.logger.warning(f"Retrying failed batch {batch_num + 1}")
                        retry_results, retry_errors = self._execute_journey_batch(
                            journey, target_url, batch_num, batch_size, batch_start, retry=True, **kwargs
                        )
                        
                        # Replace failed results with retry results
                        all_results = [r for r in all_results if not (
                            r.get('batch_number') == batch_num + 1 and not r.get('overall_success', False)
                        )]
                        all_results.extend(retry_results)
                        all_errors.extend(retry_errors)
                else:
                    self.completed_batches.append(batch_info)
                
                # Delay between batches
                if batch_num < num_batches - 1 and self.batch_config.batch_delay > 0:
                    self.logger.info(f"Batch delay: {self.batch_config.batch_delay}s before next batch")
                    time.sleep(self.batch_config.batch_delay)
                
        except Exception as e:
            self.logger.error(f"Critical error in batch Journey orchestration: {e}")
            all_errors.append(str(e))
        
        end_time = time.time()
        
        # Calculate metrics
        total_executions = len(all_results)
        successful_executions = sum(1 for r in all_results if r.get('overall_success', False))
        
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
            results=all_results,
            errors=all_errors,
            metadata={
                'test_type': 'Journey',
                'test_name': journey.name,
                'target_url': target_url,
                'replications': replications,
                'total_batches': num_batches,
                'completed_batches': len(self.completed_batches),
                'failed_batches': len(self.failed_batches),
                'batch_size': self.batch_config.batch_size,
                'batch_delay': self.batch_config.batch_delay,
                'max_concurrent_batches': self.batch_config.max_concurrent_batches,
                'retry_enabled': self.batch_config.retry_failed_batches,
                **self.metadata
            }
        )
        
        self._log_orchestration_end(orchestration_result)
        return orchestration_result
    
    def _execute_ttp_batch(self, 
                          ttp: TTP, 
                          target_url: str, 
                          batch_number: int,
                          batch_size: int,
                          start_index: int,
                          retry: bool = False,
                          **kwargs) -> Tuple[List[Dict], List[str]]:
        """Execute a batch of TTP replications."""
        results = []
        errors = []
        
        # Create execution contexts for this batch
        contexts = []
        for i in range(batch_size):
            context = ExecutionContext(
                execution_id=str(uuid.uuid4()),
                test_name=ttp.name,
                target_url=target_url,
                replication_number=start_index + i + 1,
                total_replications=start_index + batch_size,
                metadata={
                    'batch_number': batch_number + 1,
                    'batch_position': i + 1,
                    'batch_size': batch_size,
                    'retry': retry
                }
            )
            contexts.append(context)
        
        # Execute batch in parallel with limited workers
        max_workers = min(self.max_workers, batch_size, self.batch_config.max_concurrent_batches)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all executions in this batch
            future_to_context = {}
            
            for context in contexts:
                future = executor.submit(self._execute_single_ttp_in_batch, ttp, target_url, context, **kwargs)
                future_to_context[future] = context
            
            # Collect results as they complete
            for future in as_completed(future_to_context, timeout=self.timeout):
                context = future_to_context[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    status = "✓" if result.get('success', False) else "✗"
                    self.logger.info(f"  {status} Batch {batch_number + 1} execution {context.metadata['batch_position']}/{batch_size}")
                    
                except Exception as e:
                    error_msg = f"Error in batch {batch_number + 1} execution {context.metadata['batch_position']}: {str(e)}"
                    self.logger.error(f"  ✗ {error_msg}")
                    errors.append(error_msg)
                    
                    # Add failed result
                    results.append({
                        'execution_id': context.execution_id,
                        'replication_number': context.replication_number,
                        'batch_number': batch_number + 1,
                        'batch_position': context.metadata['batch_position'],
                        'success': False,
                        'error': str(e),
                        'execution_time': 0,
                        'retry': retry
                    })
        
        return results, errors
    
    def _execute_journey_batch(self, 
                              journey: Journey, 
                              target_url: str, 
                              batch_number: int,
                              batch_size: int,
                              start_index: int,
                              retry: bool = False,
                              **kwargs) -> Tuple[List[Dict], List[str]]:
        """Execute a batch of Journey replications."""
        results = []
        errors = []
        
        # Create execution contexts for this batch
        contexts = []
        for i in range(batch_size):
            context = ExecutionContext(
                execution_id=str(uuid.uuid4()),
                test_name=journey.name,
                target_url=target_url,
                replication_number=start_index + i + 1,
                total_replications=start_index + batch_size,
                metadata={
                    'batch_number': batch_number + 1,
                    'batch_position': i + 1,
                    'batch_size': batch_size,
                    'retry': retry
                }
            )
            contexts.append(context)
        
        # Execute batch in parallel with limited workers
        max_workers = min(self.max_workers, batch_size, self.batch_config.max_concurrent_batches)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all executions in this batch
            future_to_context = {}
            
            for context in contexts:
                future = executor.submit(self._execute_single_journey_in_batch, journey, target_url, context, **kwargs)
                future_to_context[future] = context
            
            # Collect results as they complete
            for future in as_completed(future_to_context, timeout=self.timeout):
                context = future_to_context[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    status = "✓" if result.get('overall_success', False) else "✗"
                    self.logger.info(f"  {status} Batch {batch_number + 1} execution {context.metadata['batch_position']}/{batch_size}")
                    
                except Exception as e:
                    error_msg = f"Error in batch {batch_number + 1} execution {context.metadata['batch_position']}: {str(e)}"
                    self.logger.error(f"  ✗ {error_msg}")
                    errors.append(error_msg)
                    
                    # Add failed result
                    results.append({
                        'execution_id': context.execution_id,
                        'replication_number': context.replication_number,
                        'batch_number': batch_number + 1,
                        'batch_position': context.metadata['batch_position'],
                        'overall_success': False,
                        'error': str(e),
                        'execution_time': 0,
                        'retry': retry
                    })
        
        return results, errors
    
    def _execute_single_ttp_in_batch(self, 
                                    ttp: TTP, 
                                    target_url: str, 
                                    context: ExecutionContext,
                                    **kwargs) -> Dict[str, Any]:
        """Execute a single TTP instance within a batch."""
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
                'batch_number': context.metadata['batch_number'],
                'batch_position': context.metadata['batch_position'],
                'test_name': ttp.name,
                'target_url': target_url,
                'success': success,
                'expected_result': expected_success,
                'actual_result': has_results,
                'results_count': len(executor.results),
                'results': executor.results,
                'execution_time': 0,  # Will be updated below
                'timestamp': time.time(),
                'retry': context.metadata.get('retry', False)
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
    
    def _execute_single_journey_in_batch(self, 
                                        journey: Journey, 
                                        target_url: str, 
                                        context: ExecutionContext,
                                        **kwargs) -> Dict[str, Any]:
        """Execute a single Journey instance within a batch."""
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
            
            # Add batch context to result
            result = journey_result.copy()
            result.update({
                'execution_id': context.execution_id,
                'replication_number': context.replication_number,
                'batch_number': context.metadata['batch_number'],
                'batch_position': context.metadata['batch_position'],
                'timestamp': time.time(),
                'retry': context.metadata.get('retry', False)
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
    
    def get_batch_stats(self) -> Dict[str, Any]:
        """Get statistics about batch processing."""
        return {
            'batch_configuration': {
                'batch_size': self.batch_config.batch_size,
                'batch_delay': self.batch_config.batch_delay,
                'max_concurrent_batches': self.batch_config.max_concurrent_batches,
                'retry_failed_batches': self.batch_config.retry_failed_batches,
                'max_retries': self.batch_config.max_retries
            },
            'execution_stats': {
                'completed_batches': len(self.completed_batches),
                'failed_batches': len(self.failed_batches),
                'active_executions': len(self.active_executions),
                'total_batches': len(self.completed_batches) + len(self.failed_batches)
            },
            'batch_details': {
                'completed': self.completed_batches,
                'failed': self.failed_batches
            }
        }
    
    def get_active_batch_status(self) -> Dict[str, Any]:
        """Get status of currently active batch executions."""
        with self.execution_lock:
            batch_groups = {}
            
            for context in self.active_executions.values():
                batch_num = context.metadata.get('batch_number', 'unknown')
                if batch_num not in batch_groups:
                    batch_groups[batch_num] = []
                
                batch_groups[batch_num].append({
                    'execution_id': context.execution_id,
                    'batch_position': context.metadata.get('batch_position', 'unknown'),
                    'test_name': context.test_name,
                    'running_time': time.time() - context.start_time if context.start_time else 0
                })
            
            return {
                'active_batches': len(batch_groups),
                'total_active_executions': len(self.active_executions),
                'batch_details': batch_groups
            }
    
    def clear_batch_history(self) -> None:
        """Clear completed and failed batch history."""
        self.completed_batches.clear()
        self.failed_batches.clear()
        self.logger.info("Batch history cleared")