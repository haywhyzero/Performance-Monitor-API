"""
Performance Monitor Client Library
Easy-to-use Python client for the Performance Monitoring API

Installation:
    pip install requests

Usage:
    from monitor_client import PerformanceMonitorClient
    
    client = PerformanceMonitorClient(
        api_url="https://your-api.onrender.com",
        api_key="pm_your_api_key_here"
    )
    
    # Get current metrics
    metrics = client.get_metrics()
    print(metrics)
    
    # Monitor a function
    with client.monitor_function("my_function"):
        # Your code here
        time.sleep(2)
"""

import requests
import time
import functools
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager


class PerformanceMonitorClient:
    """Client for Performance Monitoring API"""
    
    def __init__(self, api_url: str, api_key: str, timeout: int = 30):
        """
        Initialize the client
        
        Args:
            api_url: Base URL of the monitoring API (e.g., https://your-api.onrender.com)
            api_key: Your API key
            timeout: Request timeout in seconds (default: 30)
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make HTTP request to the API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /api/metrics)
            **kwargs: Additional arguments for requests
        
        Returns:
            Response JSON as dictionary
        
        Raises:
            Exception: If request fails
        """
        url = f"{self.api_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception(f"Authentication failed. Check your API key.")
            elif e.response.status_code == 429:
                raise Exception(f"Rate limit exceeded. Please slow down your requests.")
            else:
                raise Exception(f"HTTP {e.response.status_code}: {e.response.text}")
        
        except requests.exceptions.Timeout:
            raise Exception(f"Request timed out after {self.timeout} seconds")
        
        except requests.exceptions.ConnectionError:
            raise Exception(f"Failed to connect to {self.api_url}. Check URL and network.")
        
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def health_check(self) -> Dict:
        """
        Check API health status
        
        Returns:
            Health status dictionary
        """
        # Health check doesn't require API key
        response = requests.get(
            f"{self.api_url}/api/health",
            timeout=self.timeout
        )
        return response.json()
    
    def get_metrics(self) -> Dict:
        """
        Get current system metrics
        
        Returns:
            Current metrics including CPU, memory, disk usage
        """
        return self._make_request('GET', '/api/metrics')
    
    def get_errors(self, limit: int = 50, level: Optional[str] = None) -> Dict:
        """
        Get error history
        
        Args:
            limit: Maximum number of errors to retrieve (default: 50)
            level: Filter by error level (ERROR, WARNING, INFO)
        
        Returns:
            Dictionary containing errors list and metadata
        """
        params = {'limit': limit}
        if level:
            params['level'] = level
        
        return self._make_request('GET', '/api/errors', params=params)
    
    def get_performance_history(self, limit: int = 100) -> Dict:
        """
        Get performance metrics history
        
        Args:
            limit: Maximum number of records to retrieve (default: 100)
        
        Returns:
            Dictionary containing metrics history
        """
        params = {'limit': limit}
        return self._make_request('GET', '/api/performance', params=params)
    
    def get_thresholds(self) -> Dict:
        """
        Get current performance thresholds
        
        Returns:
            Dictionary of threshold values
        """
        return self._make_request('GET', '/api/thresholds')
    
    def update_thresholds(self, thresholds: Dict[str, float]) -> Dict:
        """
        Update performance thresholds
        
        Args:
            thresholds: Dictionary of threshold values
                       e.g., {'cpu': 85.0, 'memory': 90.0}
        
        Returns:
            Updated thresholds
        """
        return self._make_request('POST', '/api/thresholds', json=thresholds)
    
    def log_test_error(self, error_type: str = "TEST_ERROR", 
                       message: str = "Test error from client") -> Dict:
        """
        Log a test error
        
        Args:
            error_type: Type of error
            message: Error message
        
        Returns:
            Success confirmation
        """
        data = {
            'type': error_type,
            'message': message
        }
        return self._make_request('POST', '/api/test-error', json=data)
    
    def simulate_load(self, duration: int = 5, cpu_intensive: bool = True) -> Dict:
        """
        Simulate system load for testing
        
        Args:
            duration: Duration in seconds (max 10)
            cpu_intensive: True for CPU load, False for memory load
        
        Returns:
            Simulation results
        """
        data = {
            'duration': min(duration, 10),
            'cpu_intensive': cpu_intensive
        }
        return self._make_request('POST', '/api/simulate-load', json=data)
    
    @contextmanager
    def monitor_function(self, function_name: str):
        """
        Context manager to monitor function execution
        
        Usage:
            with client.monitor_function("my_function"):
                # Your code here
                do_something()
        
        Args:
            function_name: Name of the function being monitored
        """
        start_time = time.time()
        
        try:
            yield
        except Exception as e:
            # Log the error
            try:
                self.log_test_error(
                    error_type=type(e).__name__,
                    message=f"{function_name}: {str(e)}"
                )
            except:
                pass  # Don't fail if error logging fails
            raise
        finally:
            execution_time = time.time() - start_time
            print(f"[Monitor] {function_name} completed in {execution_time:.2f}s")
    
    def monitor_decorator(self, function_name: Optional[str] = None):
        """
        Decorator to monitor function execution
        
        Usage:
            @client.monitor_decorator()
            def my_function():
                # Your code here
                pass
        
        Args:
            function_name: Optional custom name (defaults to function.__name__)
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                name = function_name or func.__name__
                with self.monitor_function(name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator


class MonitoringStats:
    """Helper class for analyzing monitoring data"""
    
    @staticmethod
    def calculate_averages(metrics: List[Dict]) -> Dict[str, float]:
        """
        Calculate average values from metrics list
        
        Args:
            metrics: List of metric dictionaries
        
        Returns:
            Dictionary of average values
        """
        if not metrics:
            return {}
        
        totals = {
            'cpu_usage': 0,
            'memory_usage': 0,
            'disk_usage': 0,
            'execution_time': 0
        }
        
        for metric in metrics:
            totals['cpu_usage'] += metric.get('cpu_usage', 0)
            totals['memory_usage'] += metric.get('memory_usage', 0)
            totals['disk_usage'] += metric.get('disk_usage', 0)
            totals['execution_time'] += metric.get('execution_time', 0)
        
        count = len(metrics)
        return {key: value / count for key, value in totals.items()}
    
    @staticmethod
    def find_peak_usage(metrics: List[Dict]) -> Dict[str, Any]:
        """
        Find peak resource usage from metrics
        
        Args:
            metrics: List of metric dictionaries
        
        Returns:
            Dictionary containing peak values and timestamps
        """
        if not metrics:
            return {}
        
        peak = {
            'cpu': {'value': 0, 'timestamp': None},
            'memory': {'value': 0, 'timestamp': None},
            'execution_time': {'value': 0, 'timestamp': None}
        }
        
        for metric in metrics:
            if metric.get('cpu_usage', 0) > peak['cpu']['value']:
                peak['cpu'] = {
                    'value': metric['cpu_usage'],
                    'timestamp': metric.get('timestamp'),
                    'function': metric.get('function_name')
                }
            
            if metric.get('memory_usage', 0) > peak['memory']['value']:
                peak['memory'] = {
                    'value': metric['memory_usage'],
                    'timestamp': metric.get('timestamp'),
                    'function': metric.get('function_name')
                }
            
            if metric.get('execution_time', 0) > peak['execution_time']['value']:
                peak['execution_time'] = {
                    'value': metric['execution_time'],
                    'timestamp': metric.get('timestamp'),
                    'function': metric.get('function_name')
                }
        
        return peak
    
    @staticmethod
    def count_errors_by_type(errors: List[Dict]) -> Dict[str, int]:
        """
        Count errors by type
        
        Args:
            errors: List of error dictionaries
        
        Returns:
            Dictionary mapping error types to counts
        """
        counts = {}
        for error in errors:
            error_type = error.get('error_type', 'UNKNOWN')
            counts[error_type] = counts.get(error_type, 0) + 1
        return counts


# Example usage
if __name__ == "__main__":
    # Initialize client
    client = PerformanceMonitorClient(
        api_url="https://your-api.onrender.com",
        api_key="pm_your_api_key_here"
    )
    
    print("=" * 60)
    print("Performance Monitor Client - Example Usage")
    print("=" * 60)
    
    # 1. Health check
    print("\n1. Health Check:")
    try:
        health = client.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Version: {health.get('version', 'N/A')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 2. Get current metrics
    print("\n2. Current Metrics:")
    try:
        metrics = client.get_metrics()
        system_metrics = metrics['metrics']
        print(f"   CPU: {system_metrics['cpu_usage']:.1f}%")
        print(f"   Memory: {system_metrics['memory_usage']:.1f}%")
        print(f"   Disk: {system_metrics['disk_usage']:.1f}%")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. Monitor a function
    print("\n3. Monitor Function:")
    try:
        with client.monitor_function("example_operation"):
            print("   Doing some work...")
            time.sleep(1)
            print("   Work completed!")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 4. Get recent errors
    print("\n4. Recent Errors:")
    try:
        errors = client.get_errors(limit=5)
        print(f"   Total errors: {errors['total_count']}")
        for error in errors['errors'][:3]:
            print(f"   - {error['error_type']}: {error['message']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 5. Performance history
    print("\n5. Performance History:")
    try:
        history = client.get_performance_history(limit=10)
        print(f"   Records retrieved: {history['total_count']}")
        
        if history['metrics']:
            stats = MonitoringStats()
            averages = stats.calculate_averages(history['metrics'])
            print(f"   Average CPU: {averages.get('cpu_usage', 0):.1f}%")
            print(f"   Average Memory: {averages.get('memory_usage', 0):.1f}%")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)