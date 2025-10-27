#!/usr/bin/env python3
"""
Enhanced Performance Monitoring API
Author: Swave IT team
Contributors: Ayomide Aregbe
Date: January 2025
Version: 2.0 (Production Ready)
"""

import json
import time
import psutil
import threading
import traceback
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import logging
import os
import sys
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    API_KEYS = os.environ.get('API_KEYS', '').split(',') if os.environ.get('API_KEYS') else []
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'monitoring.db')
    MAX_HISTORY_RECORDS = int(os.environ.get('MAX_HISTORY_RECORDS', 10000))
    RATE_LIMIT = os.environ.get('RATE_LIMIT', '100 per hour')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

@dataclass
class PerformanceMetrics:
    """Data class for performance metrics"""
    id: Optional[int]
    timestamp: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_sent: int
    network_recv: int
    execution_time: float
    function_name: str
    status: str
    api_key: Optional[str] = None

@dataclass
class ErrorLog:
    """Data class for error logging"""
    id: Optional[int]
    timestamp: str
    level: str
    error_type: str
    message: str
    traceback_info: str
    function_name: str
    cpu_impact: float
    memory_impact: float
    severity: float
    explanation: str
    suggested_fix: str
    api_key: Optional[str] = None

class DatabaseManager:
    """Handle all database operations"""
    
    def __init__(self, db_path: str = Config.DATABASE_PATH):
        self.db_path = db_path
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL,
                network_sent INTEGER,
                network_recv INTEGER,
                execution_time REAL,
                function_name TEXT,
                status TEXT,
                api_key TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Error logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT,
                error_type TEXT,
                message TEXT,
                traceback_info TEXT,
                function_name TEXT,
                cpu_impact REAL,
                memory_impact REAL,
                severity REAL,
                explanation TEXT,
                suggested_fix TEXT,
                api_key TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # API keys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT UNIQUE NOT NULL,
                key_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_used DATETIME,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON errors(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_errors_level ON errors(level)')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def get_connection(self):
        """Get database connection"""
        # Use Flask's application context 'g' to store the connection for the request
        if 'db_conn' not in g:
            g.db_conn = sqlite3.connect(self.db_path)
            g.db_conn.row_factory = sqlite3.Row
        return g.db_conn
    
    def save_metric(self, metric: PerformanceMetrics):
        """Save performance metric to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO metrics (timestamp, cpu_usage, memory_usage, disk_usage,
                               network_sent, network_recv, execution_time, 
                               function_name, status, api_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (metric.timestamp, metric.cpu_usage, metric.memory_usage, 
              metric.disk_usage, metric.network_sent, metric.network_recv,
              metric.execution_time, metric.function_name, metric.status, metric.api_key))
        
        conn.commit() # Connection will be closed at the end of the request
    
    def save_error(self, error: ErrorLog):
        """Save error log to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO errors (timestamp, level, error_type, message, traceback_info,
                              function_name, cpu_impact, memory_impact, severity,
                              explanation, suggested_fix, api_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (error.timestamp, error.level, error.error_type, error.message,
              error.traceback_info, error.function_name, error.cpu_impact,
              error.memory_impact, error.severity, error.explanation,
              error.suggested_fix, error.api_key))
        
        conn.commit() # Connection will be closed at the end of the request
    
    def get_metrics(self, limit: int = 100, api_key: Optional[str] = None):
        """Retrieve performance metrics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM metrics'
        params = []
        
        if api_key:
            query += ' WHERE api_key = ?'
            params.append(api_key)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_errors(self, limit: int = 50, level: Optional[str] = None, api_key: Optional[str] = None):
        """Retrieve error logs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM errors WHERE 1=1'
        params = []
        
        if level:
            query += ' AND level = ?'
            params.append(level.upper())
        
        if api_key:
            query += ' AND api_key = ?'
            params.append(api_key)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def _cleanup_old_metrics(self):
        """Remove old metrics to prevent database bloat"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM metrics WHERE id NOT IN (
                SELECT id FROM metrics ORDER BY created_at DESC LIMIT ?
            )
        ''', (Config.MAX_HISTORY_RECORDS,))
        
        conn.commit() # Connection will be closed at the end of the request
    
    def create_api_key(self, key_name: str) -> str:
        """Create a new API key"""
        api_key = f"pm_{secrets.token_urlsafe(32)}"
        key_hash = generate_password_hash(api_key)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO api_keys (key_hash, key_name)
            VALUES (?, ?)
        ''', (key_hash, key_name))
        
        conn.commit() # Connection will be closed at the end of the request
        
        logger.info(f"Created new API key: {key_name}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate an API key"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT key_hash FROM api_keys WHERE is_active = 1')
        rows = cursor.fetchall()
        
        for row in rows:
            if check_password_hash(row['key_hash'], api_key):
                # Update last used timestamp
                cursor.execute('''
                    UPDATE api_keys 
                    SET last_used = CURRENT_TIMESTAMP 
                    WHERE key_hash = ?
                ''', (row['key_hash'],))
                conn.commit() # Connection will be closed at the end of the request
                return True
        
        return False

class PerformanceMonitor:
    """Core performance monitoring class"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.thresholds = {
            'cpu': 80.0,
            'memory': 80.0,
            'disk': 90.0,
            'response_time': 5.0
        }
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            return {
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'disk_usage': disk.percent,
                'network_io': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv
                }
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}
    
    def log_error(self, error_type: str, message: str, function_name: str = "unknown",
                  level: str = "ERROR", api_key: Optional[str] = None):
        """Log an error with detailed information"""
        
        explanation = self._generate_error_explanation(error_type, message)
        suggested_fix = self._generate_suggested_fix(error_type, message)
        performance_impact = self._calculate_performance_impact()
        
        error_log = ErrorLog(
            id=None,
            timestamp=datetime.now().isoformat(),
            level=level,
            error_type=error_type,
            message=message,
            traceback_info=traceback.format_exc() if sys.exc_info()[0] else "No traceback available",
            function_name=function_name,
            cpu_impact=performance_impact['cpu_impact'],
            memory_impact=performance_impact['memory_impact'],
            severity=performance_impact['overall_severity'],
            explanation=explanation,
            suggested_fix=suggested_fix,
            api_key=api_key
        )
        
        self.db.save_error(error_log)
        logger.error(f"{error_type}: {message}")
    
    def _generate_error_explanation(self, error_type: str, message: str) -> str:
        """Generate detailed explanation for the error"""
        explanations = {
            "HIGH_CPU_USAGE": "CPU usage has exceeded the threshold, indicating intensive processing that may slow down the system.",
            "HIGH_MEMORY_USAGE": "Memory usage is critically high, which can lead to system instability and slower performance.",
            "DISK_SPACE_LOW": "Available disk space is running low, which can cause write operations to fail.",
            "SLOW_RESPONSE": "Function execution time exceeded acceptable limits, indicating performance bottleneck.",
            "NETWORK_ERROR": "Network connectivity issue detected, which may affect external API calls or data transfers.",
            "DATABASE_ERROR": "Database operation failed, potentially due to connection issues or query problems.",
            "AUTHENTICATION_ERROR": "Authentication failed, indicating potential security breach or expired credentials.",
            "RATE_LIMIT_EXCEEDED": "Too many requests received in a short time period.",
        }
        return explanations.get(error_type, f"An error of type '{error_type}' occurred: {message}")
    
    def _generate_suggested_fix(self, error_type: str, message: str) -> str:
        """Generate suggested fixes for the error"""
        fixes = {
            "HIGH_CPU_USAGE": "Consider optimizing algorithms, reducing computational complexity, or scaling horizontally.",
            "HIGH_MEMORY_USAGE": "Review memory allocation, implement garbage collection, or increase available RAM.",
            "DISK_SPACE_LOW": "Clean up temporary files, archive old logs, or expand storage capacity.",
            "SLOW_RESPONSE": "Optimize database queries, implement caching, or consider asynchronous processing.",
            "NETWORK_ERROR": "Check network connectivity, implement retry logic, or use circuit breaker pattern.",
            "AUTHENTICATION_ERROR": "Verify API key is valid and has not expired.",
            "RATE_LIMIT_EXCEEDED": "Reduce request frequency or upgrade to a higher rate limit tier.",
        }
        return fixes.get(error_type, f"Review the error details and implement appropriate error handling for '{error_type}'.")
    
    def _calculate_performance_impact(self) -> Dict[str, float]:
        """Calculate performance impact of the current error"""
        metrics = self._get_system_metrics()
        return {
            'cpu_impact': max(0, metrics.get('cpu_usage', 0) - 20),
            'memory_impact': max(0, metrics.get('memory_usage', 0) - 30),
            'overall_severity': min(10, (metrics.get('cpu_usage', 0) + metrics.get('memory_usage', 0)) / 20)
        }
    
    def monitor_function(self, function_name: str, api_key: Optional[str] = None):
        """Decorator for monitoring function performance"""
        from contextlib import contextmanager
        
        @contextmanager
        def _monitor():
            start_time = time.time()
            start_metrics = self._get_system_metrics()
            
            try:
                yield
            except Exception as e:
                self.log_error(
                    error_type=type(e).__name__.upper(),
                    message=str(e),
                    function_name=function_name,
                    api_key=api_key
                )
                raise
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                end_metrics = self._get_system_metrics()
                
                # Check thresholds
                if end_metrics.get('cpu_usage', 0) > self.thresholds['cpu']:
                    self.log_error(
                        "HIGH_CPU_USAGE",
                        f"CPU usage: {end_metrics['cpu_usage']:.2f}% exceeds threshold",
                        function_name,
                        level="WARNING",
                        api_key=api_key
                    )
                
                if execution_time > self.thresholds['response_time']:
                    self.log_error(
                        "SLOW_RESPONSE",
                        f"Execution time: {execution_time:.2f}s exceeds threshold",
                        function_name,
                        level="WARNING",
                        api_key=api_key
                    )
                
                # Save metrics
                metric = PerformanceMetrics(
                    id=None,
                    timestamp=datetime.now().isoformat(),
                    cpu_usage=end_metrics.get('cpu_usage', 0),
                    memory_usage=end_metrics.get('memory_usage', 0),
                    disk_usage=end_metrics.get('disk_usage', 0),
                    network_sent=end_metrics.get('network_io', {}).get('bytes_sent', 0),
                    network_recv=end_metrics.get('network_io', {}).get('bytes_recv', 0),
                    execution_time=execution_time,
                    function_name=function_name,
                    status="completed",
                    api_key=api_key
                )
                
                self.db.save_metric(metric)
        
        return _monitor()

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "X-API-Key"]
    }
})

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[Config.RATE_LIMIT],
    storage_uri="memory://"
)

# Initialize monitor
monitor = PerformanceMonitor()

# Close DB connection at the end of each request
@app.teardown_appcontext
def teardown_db(exception):
    db = g.pop('db_conn', None)
    if db is not None:
        db.close()

# Authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            monitor.log_error(
                "AUTHENTICATION_ERROR",
                "Missing API key",
                f.__name__,
                level="WARNING"
            )
            return jsonify({'error': 'API key required'}), 401
        
        if not monitor.db.validate_api_key(api_key):
            monitor.log_error(
                "AUTHENTICATION_ERROR",
                "Invalid API key",
                f.__name__,
                level="WARNING"
            )
            return jsonify({'error': 'Invalid API key'}), 401
        
        g.api_key = api_key
        return f(*args, **kwargs)
    
    return decorated_function

# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint - no auth required"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0'
    })

@app.route('/api/metrics', methods=['GET'])
@require_api_key
@limiter.limit("60 per minute")
def get_metrics():
    """Get current system metrics"""
    with monitor.monitor_function('get_metrics', g.api_key):
        metrics = monitor._get_system_metrics()
        return jsonify({
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/errors', methods=['GET'])
@require_api_key
@limiter.limit("60 per minute")
def get_errors():
    """Get error history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        level = request.args.get('level', None)
        
        errors = monitor.db.get_errors(limit=limit, level=level, api_key=g.api_key)
        
        return jsonify({
            'errors': errors,
            'total_count': len(errors),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        monitor.log_error("API_ERROR", str(e), "get_errors", api_key=g.api_key)
        return jsonify({'error': 'Failed to retrieve errors'}), 500

@app.route('/api/performance', methods=['GET'])
@require_api_key
@limiter.limit("60 per minute")
def get_performance_history():
    """Get performance metrics history"""
    with monitor.monitor_function('get_performance_history', g.api_key):
        limit = request.args.get('limit', 100, type=int)
        metrics = monitor.db.get_metrics(limit=limit, api_key=g.api_key)
        
        return jsonify({
            'metrics': metrics,
            'total_count': len(metrics),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/thresholds', methods=['GET', 'POST'])
@require_api_key
def manage_thresholds():
    """Get or update performance thresholds"""
    with monitor.monitor_function('manage_thresholds', g.api_key):
        if request.method == 'GET':
            return jsonify(monitor.thresholds)
        
        elif request.method == 'POST':
            try:
                new_thresholds = request.json
                monitor.thresholds.update(new_thresholds)
                return jsonify({
                    'message': 'Thresholds updated successfully',
                    'thresholds': monitor.thresholds
                })
            except Exception as e:
                monitor.log_error("THRESHOLD_UPDATE_ERROR", str(e), "manage_thresholds", api_key=g.api_key)
                return jsonify({'error': 'Failed to update thresholds'}), 400

@app.route('/api/test-error', methods=['POST'])
@require_api_key
def test_error():
    """Test endpoint to generate sample errors"""
    try:
        error_type = request.json.get('type', 'TEST_ERROR')
        message = request.json.get('message', 'This is a test error')
        
        monitor.log_error(error_type, message, 'test_error', level="INFO", api_key=g.api_key)
        
        return jsonify({'message': 'Test error logged successfully'})
    except Exception as e:
        monitor.log_error("TEST_ERROR_FAILURE", str(e), "test_error", api_key=g.api_key)
        return jsonify({'error': 'Failed to log test error'}), 500

@app.route('/api/simulate-load', methods=['POST'])
@require_api_key
@limiter.limit("10 per hour")
def simulate_load():
    """Simulate high load to test monitoring"""
    with monitor.monitor_function('simulate_load', g.api_key):
        try:
            duration = min(request.json.get('duration', 5), 10)  # Max 10 seconds
            cpu_intensive = request.json.get('cpu_intensive', True)
            
            start_time = time.time()
            data = []
            
            while time.time() - start_time < duration:
                if cpu_intensive:
                    [x**2 for x in range(10000)]
                else:
                    data.extend(range(100000))
                time.sleep(0.01)
            
            return jsonify({
                'message': 'Load simulation completed',
                'duration': duration,
                'type': 'cpu_intensive' if cpu_intensive else 'memory_intensive'
            })
        except Exception as e:
            monitor.log_error("LOAD_SIMULATION_ERROR", str(e), "simulate_load", api_key=g.api_key)
            return jsonify({'error': 'Load simulation failed'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    monitor.log_error("RATE_LIMIT_EXCEEDED", str(e), "rate_limiter", level="WARNING")
    return jsonify({'error': 'Rate limit exceeded. Please slow down your requests.'}), 429

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    monitor.log_error("INTERNAL_SERVER_ERROR", str(error), "flask_app")
    return jsonify({'error': 'Internal server error'}), 500

# Background monitoring
def background_monitoring():
    """Background thread for continuous monitoring"""
    while True:
        try:
            metrics = monitor._get_system_metrics()
            
            if metrics.get('cpu_usage', 0) > monitor.thresholds['cpu']:
                monitor.log_error(
                    "HIGH_CPU_USAGE",
                    f"System CPU: {metrics['cpu_usage']:.2f}%",
                    "background_monitor",
                    level="WARNING"
                )
            
            if metrics.get('memory_usage', 0) > monitor.thresholds['memory']:
                monitor.log_error(
                    "HIGH_MEMORY_USAGE",
                    f"System Memory: {metrics['memory_usage']:.2f}%",
                    "background_monitor",
                    level="WARNING"
                )
            
            # Cleanup old metrics periodically
            # This is more efficient than cleaning after every insert
            with app.app_context():
                monitor.db._cleanup_old_metrics()
                logger.info("Periodic database cleanup completed.")

            time.sleep(30)
        except Exception as e:
            monitor.log_error("BACKGROUND_MONITOR_ERROR", str(e), "background_monitoring")
            time.sleep(60)

if __name__ == '__main__':
    print("=" * 60)
    print("Enhanced Performance Monitoring API v2.0")
    print("=" * 60)
    print("\n🔧 Initialization:")
    print(f"  Database: {Config.DATABASE_PATH}")
    print(f"  Rate Limit: {Config.RATE_LIMIT}")
    print(f"  Debug Mode: {Config.DEBUG}")
    
    # Create initial API key if none exist
    print("\n🔑 Generating initial API key...")
    try:
        initial_key = monitor.db.create_api_key("initial_key")
        print(f"  ✓ API Key created: {initial_key}")
        print(f"  ⚠️  SAVE THIS KEY - You won't see it again!")
    except Exception as e:
        print(f"  ℹ️  API keys may already exist: {e}")
    
    print("\n📡 Available endpoints:")
    print("  GET    /api/health          - Health check (no auth)")
    print("  GET    /api/metrics         - Current system metrics")
    print("  GET    /api/errors          - Error history")
    print("  GET    /api/performance     - Performance history")
    print("  GET/POST /api/thresholds    - Manage thresholds")
    print("  POST   /api/test-error      - Generate test error")
    print("  POST   /api/simulate-load   - Simulate system load")
    
    print("\n🔒 Authentication:")
    print("  All endpoints (except /health) require X-API-Key header")
    print("  Example: curl -H 'X-API-Key: your_key_here' http://localhost:5000/api/metrics")
    
    print("\n🚀 Starting services...")
    
    # Start background monitoring
    monitoring_thread = threading.Thread(target=background_monitoring, daemon=True)
    monitoring_thread.start()
    print("  ✓ Background monitoring started")
    
    # Start Flask app
    print("  ✓ API server starting on http://0.0.0.0:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)