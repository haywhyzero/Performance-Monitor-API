/**
 * Performance Monitor Client Library for JavaScript/Node.js 
 * Author: Kelvin 
 * Swave IT Teams
 * 
 * Installation:
 *   npm install axios
 * 
 * Usage (Node.js):
 *   const { PerformanceMonitorClient } = require('./monitor-client');
 *   
 *   const client = new PerformanceMonitorClient({
 *     apiUrl: 'enter url here',
 *     apiKey: 'your_api_key_here'
 *   });
 *   
 *   // Get metrics
 *   const metrics = await client.getMetrics();
 *   console.log(metrics);
 * 
 * Usage (Browser):
 *   <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
 *   <script src="monitor-client.js"></script>
 *   <script>
 *     const client = new PerformanceMonitorClient({
 *       apiUrl: 'enter url here',
 *       apiKey: 'your_api_key_here'
 *     });
 *   </script>
 */

(function(global) {
  'use strict';

  const isNode = typeof module !== 'undefined' && module.exports;
  
  let httpClient;
  if (isNode) {
    try {
      httpClient = require('axios');
    } catch (e) {
      console.warn('Axios not found. Install with: npm install axios');
    }
  } else {
    httpClient = global.axios || createFetchClient();
  }

  /**
   * Simple fetch-based HTTP client for browsers without axios
   */
  function createFetchClient() {
    return {
      request: async (config) => {
        const response = await fetch(config.url, {
          method: config.method,
          headers: config.headers,
          body: config.data ? JSON.stringify(config.data) : undefined,
        });
        
        if (!response.ok) {
          const error = new Error(`HTTP ${response.status}`);
          error.response = {
            status: response.status,
            data: await response.json().catch(() => ({}))
          };
          throw error;
        }
        
        return { data: await response.json() };
      }
    };
  }

  /**
   * Main Performance Monitor Client Class
   */
  class PerformanceMonitorClient {
    /**
     * Initialize the client
     * @param {Object} options - Configuration options
     * @param {string} options.apiUrl - Base URL of the monitoring API
     * @param {string} options.apiKey - Your API key
     * @param {number} [options.timeout=30000] - Request timeout in milliseconds
     */
    constructor({ apiUrl, apiKey, timeout = 30000 }) {
      if (!apiUrl) throw new Error('apiUrl is required');
      if (!apiKey) throw new Error('apiKey is required');

      this.apiUrl = apiUrl.replace(/\/$/, '');
      this.apiKey = apiKey;
      this.timeout = timeout;
      this.headers = {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json'
      };
    }

    /**
     * Make HTTP request to the API
     * @private
     */
    async _makeRequest(method, endpoint, options = {}) {
      const url = `${this.apiUrl}${endpoint}`;
      
      try {
        const config = {
          method,
          url,
          headers: this.headers,
          timeout: this.timeout,
          ...options
        };

        const response = await httpClient.request(config);
        return response.data;

      } catch (error) {
        if (error.response) {
          const status = error.response.status;
          const data = error.response.data || {};
          
          if (status === 401) {
            throw new Error('Authentication failed. Check your API key.');
          } else if (status === 429) {
            throw new Error('Rate limit exceeded. Please slow down your requests.');
          } else {
            const errorMessage = data.error || JSON.stringify(data);
            throw new Error(`HTTP ${status}: ${errorMessage}`);
          }
        } else if (error.request) {
          // The request was made but no response was received
          throw new Error('Network error: No response received from server.');
        } else {
          // Something happened in setting up the request that triggered an Error
          throw new Error(`Request failed: ${error.message}`);
        }
      }
    }

    /**
     * Check API health status
     * @returns {Promise<Object>} Health status object
     */
    async healthCheck() {
      // Health check doesn't require API key, so we make a direct request
      const url = `${this.apiUrl}/api/health`;
      const response = await httpClient.request({
        method: 'get',
        url,
        timeout: this.timeout
      });
      return response.data;
    }

    /**
     * Get current system metrics
     * @returns {Promise<Object>} Current metrics
     */
    async getMetrics() {
      return this._makeRequest('get', '/api/metrics');
    }

    /**
     * Get error history
     * @param {Object} [options] - Filter options
     * @param {number} [options.limit=50] - Max number of errors
     * @param {string} [options.level] - Filter by level (e.g., 'ERROR')
     * @returns {Promise<Object>} List of errors
     */
    async getErrors({ limit = 50, level } = {}) {
      const params = { limit };
      if (level) params.level = level;
      return this._makeRequest('get', '/api/errors', { params });
    }

    /**
     * Get performance metrics history
     * @param {Object} [options] - Filter options
     * @param {number} [options.limit=100] - Max number of records
     * @returns {Promise<Object>} Metrics history
     */
    async getPerformanceHistory({ limit = 100 } = {}) {
      return this._makeRequest('get', '/api/performance', { params: { limit } });
    }

    /**
     * Get current performance thresholds
     * @returns {Promise<Object>} Threshold values
     */
    async getThresholds() {
      return this._makeRequest('get', '/api/thresholds');
    }

    /**
     * Update performance thresholds
     * @param {Object} thresholds - e.g., { cpu: 85.0 }
     * @returns {Promise<Object>} Updated thresholds
     */
    async updateThresholds(thresholds) {
      return this._makeRequest('post', '/api/thresholds', { data: thresholds });
    }

    /**
     * Log a test error
     * @param {Object} [options] - Error details
     * @param {string} [options.type='TEST_ERROR'] - Error type
     * @param {string} [options.message='Test error from client'] - Error message
     * @returns {Promise<Object>} Confirmation message
     */
    async logTestError({ type = 'TEST_ERROR', message = 'Test error from client' } = {}) {
      return this._makeRequest('post', '/api/test-error', { data: { type, message } });
    }

    /**
     * Simulate system load for testing
     * @param {Object} [options] - Simulation options
     * @param {number} [options.duration=5] - Duration in seconds (max 10)
     * @param {boolean} [options.cpuIntensive=true] - True for CPU, false for memory
     * @returns {Promise<Object>} Simulation results
     */
    async simulateLoad({ duration = 5, cpuIntensive = true } = {}) {
      const data = { duration: Math.min(duration, 10), cpu_intensive: cpuIntensive };
      return this._makeRequest('post', '/api/simulate-load', { data });
    }

    /**
     * Monitor an async function's execution.
     * @param {string} functionName - Name of the function being monitored.
     * @param {Function} func - The async function to execute and monitor.
     * @returns {Promise<any>} The result of the executed function.
     */
    async monitorFunction(functionName, func) {
      const startTime = Date.now();
      try {
        return await func();
      } catch (e) {
        try {
          await this.logTestError({
            type: e.constructor.name.toUpperCase(),
            message: `${functionName}: ${e.message}`
          });
        } catch (logError) {
          console.error('Failed to log error to monitor:', logError);
        }
        throw e; 
      } finally {
        const executionTime = (Date.now() - startTime) / 1000;
        console.log(`[Monitor] ${functionName} completed in ${executionTime.toFixed(2)}s`);
      }
    }
  }

  if (isNode) {
    module.exports = { PerformanceMonitorClient };
  } else {
    global.PerformanceMonitorClient = PerformanceMonitorClient;
  }

})(typeof self !== 'undefined' ? self : this);