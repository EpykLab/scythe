from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum
import time
import logging
from concurrent.futures import ThreadPoolExecutor

from ..core.ttp import TTP
from ..journeys.base import Journey


class OrchestrationStrategy(Enum):
    """Enumeration of orchestration strategies."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BATCH = "batch"
    DISTRIBUTED = "distributed"


@dataclass
class OrchestrationResult:
    """Result of an orchestration execution."""
    orchestrator_name: str
    strategy: OrchestrationStrategy
    total_executions: int
    successful_executions: int
    failed_executions: int
    start_time: float
    end_time: float
    execution_time: float
    results: List[Dict[str, Any]]
    errors: List[str]
    metadata: Dict[str, Any]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100
    
    @property
    def average_execution_time(self) -> float:
        """Calculate average execution time per test."""
        if self.total_executions == 0:
            return 0.0
        return self.execution_time / self.total_executions
    
    def summary(self) -> Dict[str, Any]:
        """Get a summary of the orchestration results."""
        return {
            'orchestrator': self.orchestrator_name,
            'strategy': self.strategy.value,
            'executions': {
                'total': self.total_executions,
                'successful': self.successful_executions,
                'failed': self.failed_executions,
                'success_rate': f"{self.success_rate:.1f}%"
            },
            'timing': {
                'total_time': f"{self.execution_time:.2f}s",
                'average_time': f"{self.average_execution_time:.2f}s"
            },
            'errors': len(self.errors),
            'metadata': self.metadata
        }


class Orchestrator(ABC):
    """
    Abstract base class for orchestrating TTPs and Journeys at scale.
    
    Orchestrators provide capabilities for running tests in various patterns:
    - Scale testing (many instances of the same test)
    - Distributed testing (across multiple networks/proxies)
    - Batch processing (dividing work across limited resources)
    """
    
    def __init__(self, 
                 name: str, 
                 description: str,
                 strategy: OrchestrationStrategy = OrchestrationStrategy.SEQUENTIAL,
                 max_workers: int = 4,
                 timeout: Optional[float] = None):
        """
        Initialize the orchestrator.
        
        Args:
            name: Name of the orchestrator
            description: Description of what this orchestrator does
            strategy: Orchestration strategy to use
            max_workers: Maximum number of concurrent workers
            timeout: Optional timeout for the entire orchestration
        """
        self.name = name
        self.description = description
        self.strategy = strategy
        self.max_workers = max_workers
        self.timeout = timeout
        self.logger = logging.getLogger(f"Orchestrator.{name}")
        self.metadata = {}
        
    @abstractmethod
    def orchestrate_ttp(self, 
                       ttp: TTP, 
                       target_url: str,
                       replications: int = 1,
                       **kwargs) -> OrchestrationResult:
        """
        Orchestrate execution of a TTP.
        
        Args:
            ttp: TTP instance to orchestrate
            target_url: Target URL for the TTP
            replications: Number of times to replicate the TTP
            **kwargs: Additional orchestration parameters
            
        Returns:
            OrchestrationResult containing execution details
        """
        pass
    
    @abstractmethod
    def orchestrate_journey(self, 
                           journey: Journey, 
                           target_url: str,
                           replications: int = 1,
                           **kwargs) -> OrchestrationResult:
        """
        Orchestrate execution of a Journey.
        
        Args:
            journey: Journey instance to orchestrate
            target_url: Target URL for the journey
            replications: Number of times to replicate the journey
            **kwargs: Additional orchestration parameters
            
        Returns:
            OrchestrationResult containing execution details
        """
        pass
    
    def orchestrate_mixed(self,
                         tests: List[Union[TTP, Journey]],
                         target_urls: List[str],
                         replications: int = 1,
                         **kwargs) -> OrchestrationResult:
        """
        Orchestrate execution of mixed TTPs and Journeys.
        
        Args:
            tests: List of TTP and Journey instances
            target_urls: List of target URLs (one per test or one for all)
            replications: Number of times to replicate each test
            **kwargs: Additional orchestration parameters
            
        Returns:
            OrchestrationResult containing execution details
        """
        start_time = time.time()
        all_results = []
        all_errors = []
        
        # Ensure we have enough URLs
        if len(target_urls) == 1:
            target_urls = target_urls * len(tests)
        elif len(target_urls) != len(tests):
            raise ValueError("Number of target URLs must be 1 or equal to number of tests")
        
        try:
            for test, url in zip(tests, target_urls):
                if isinstance(test, TTP):
                    result = self.orchestrate_ttp(test, url, replications, **kwargs)
                elif isinstance(test, Journey):
                    result = self.orchestrate_journey(test, url, replications, **kwargs)
                else:
                    self.logger.error(f"Unknown test type: {type(test)}")
                    continue
                
                all_results.extend(result.results)
                all_errors.extend(result.errors)
        
        except Exception as e:
            self.logger.error(f"Error in mixed orchestration: {e}")
            all_errors.append(str(e))
        
        end_time = time.time()
        
        # Calculate aggregated metrics
        total_executions = len(all_results)
        successful_executions = sum(1 for r in all_results 
                                  if r.get('success', False) or 
                                     r.get('overall_success', False))
        
        return OrchestrationResult(
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
            metadata=self.metadata.copy()
        )
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set orchestrator metadata."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get orchestrator metadata."""
        return self.metadata.get(key, default)
    
    def _execute_with_timeout(self, 
                             func: Callable, 
                             *args, 
                             timeout: Optional[float] = None,
                             **kwargs) -> Any:
        """
        Execute a function with optional timeout.
        
        Args:
            func: Function to execute
            *args: Function arguments
            timeout: Timeout in seconds
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if timeout
        """
        if timeout is None:
            return func(*args, **kwargs)
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout)
            except TimeoutError:
                self.logger.warning(f"Function {func.__name__} timed out after {timeout}s")
                return None
    
    def _log_orchestration_start(self, 
                                test_name: str, 
                                test_type: str,
                                replications: int,
                                target_url: str):
        """Log the start of an orchestration."""
        self.logger.info("="*60)
        self.logger.info(f"STARTING ORCHESTRATION: {self.name}")
        self.logger.info("="*60)
        self.logger.info(f"Test: {test_name} ({test_type})")
        self.logger.info(f"Target URL: {target_url}")
        self.logger.info(f"Strategy: {self.strategy.value}")
        self.logger.info(f"Replications: {replications}")
        self.logger.info(f"Max Workers: {self.max_workers}")
        if self.timeout:
            self.logger.info(f"Timeout: {self.timeout}s")
    
    def _log_orchestration_end(self, result: OrchestrationResult):
        """Log the end of an orchestration."""
        self.logger.info("\n" + "="*60)
        self.logger.info(f"ORCHESTRATION SUMMARY: {self.name}")
        self.logger.info("="*60)
        
        summary = result.summary()
        
        self.logger.info(f"Strategy: {summary['strategy']}")
        self.logger.info(f"Executions: {summary['executions']['successful']}/{summary['executions']['total']} successful ({summary['executions']['success_rate']})")
        self.logger.info(f"Total Time: {summary['timing']['total_time']}")
        self.logger.info(f"Average Time: {summary['timing']['average_time']}")
        
        if result.errors:
            self.logger.warning(f"Errors: {len(result.errors)}")
            for i, error in enumerate(result.errors[:3], 1):
                self.logger.warning(f"  {i}. {error}")
            if len(result.errors) > 3:
                self.logger.warning(f"  ... and {len(result.errors) - 3} more errors")
        
        self.logger.info("="*60)


class ExecutionContext:
    """Context for individual test executions within orchestration."""
    
    def __init__(self, 
                 execution_id: str,
                 test_name: str,
                 target_url: str,
                 replication_number: int,
                 total_replications: int,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize execution context.
        
        Args:
            execution_id: Unique identifier for this execution
            test_name: Name of the test being executed
            target_url: Target URL for execution
            replication_number: Current replication number (1-based)
            total_replications: Total number of replications
            metadata: Additional context metadata
        """
        self.execution_id = execution_id
        self.test_name = test_name
        self.target_url = target_url
        self.replication_number = replication_number
        self.total_replications = total_replications
        self.metadata = metadata or {}
        self.start_time = None
        self.end_time = None
        self.result = None
        self.error = None
    
    def start(self):
        """Mark the start of execution."""
        self.start_time = time.time()
    
    def end(self, result: Any = None, error: Optional[Exception] = None):
        """Mark the end of execution."""
        self.end_time = time.time()
        self.result = result
        self.error = error
    
    @property
    def execution_time(self) -> float:
        """Get execution time in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def is_successful(self) -> bool:
        """Check if execution was successful."""
        if self.error:
            return False
        if isinstance(self.result, dict):
            return (self.result.get('success', False) or 
                   self.result.get('overall_success', False))
        return self.result is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'execution_id': self.execution_id,
            'test_name': self.test_name,
            'target_url': self.target_url,
            'replication_number': self.replication_number,
            'total_replications': self.total_replications,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'execution_time': self.execution_time,
            'successful': self.is_successful,
            'error': str(self.error) if self.error else None,
            'metadata': self.metadata,
            'result': self.result
        }


class OrchestrationError(Exception):
    """Exception raised during orchestration operations."""
    
    def __init__(self, message: str, orchestrator_name: Optional[str] = None, context: Optional[ExecutionContext] = None):
        self.orchestrator_name = orchestrator_name
        self.context = context
        super().__init__(message)