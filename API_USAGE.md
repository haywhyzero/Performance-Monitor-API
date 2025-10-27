# Performance Monitor API - Usage Examples

This document provides examples of how to interact with the Performance Monitoring API using various programming languages.

## Prerequisites

Before you start, you will need:

1.  **API Base URL**: The URL where your API is hosted (e.g., `https://your-api.onrender.com`).
2.  **API Key**: Your unique API key (e.g., `pm_xxxxxxxxxxxx`).

All authenticated requests must include the `X-API-Key` header.

---

## Python (using `requests`)

This is the most common way to make HTTP requests in Python.

**Installation:**
```bash
pip install requests
```

**Code:**
```python
import requests
import json

API_URL = "https://your-api.onrender.com"
API_KEY = "pm_your_api_key_here"

def get_system_metrics():
    """Fetches current system metrics from the API."""
    endpoint = "/api/metrics"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{API_URL}{endpoint}", headers=headers, timeout=10)
        response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
        
        print("Successfully fetched metrics:")
        print(json.dumps(response.json(), indent=2))
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

if __name__ == "__main__":
    get_system_metrics()
```

---

## JavaScript (Node.js with `axios`)

A popular choice for making HTTP requests in Node.js and the browser.

**Installation:**
```bash
npm install axios
```

**Code:**
```javascript
const axios = require('axios');

const API_URL = 'https://your-api.onrender.com';
const API_KEY = 'pm_your_api_key_here';

async function getSystemMetrics() {
  try {
    const endpoint = '/api/metrics';
    const response = await axios.get(`${API_URL}${endpoint}`, {
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
      },
      timeout: 10000 // 10 seconds
    });

    console.log('Successfully fetched metrics:');
    console.log(JSON.stringify(response.data, null, 2));

  } catch (error) {
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error(`Error: ${error.response.status} - ${JSON.stringify(error.response.data)}`);
    } else if (error.request) {
      // The request was made but no response was received
      console.error('Network error: No response received from server.');
    } else {
      // Something happened in setting up the request
      console.error('Error:', error.message);
    }
  }
}

getSystemMetrics();
```

---

## PHP (using `cURL`)

The `cURL` extension is a standard way to handle HTTP requests in PHP.

**Code:**
```php
<?php

$apiUrl = "https://your-api.onrender.com/api/metrics";
$apiKey = "pm_your_api_key_here";

$headers = [
    "X-API-Key: " . $apiKey,
    "Content-Type: application/json",
];

$ch = curl_init();

curl_setopt($ch, CURLOPT_URL, $apiUrl);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

if (curl_errno($ch)) {
    echo 'cURL Error: ' . curl_error($ch);
} elseif ($httpCode >= 400) {
    echo "HTTP Error: " . $httpCode . " - " . $response;
} else {
    echo "Successfully fetched metrics:\n";
    $data = json_decode($response, true);
    echo json_encode($data, JSON_PRETTY_PRINT);
}

curl_close($ch);

?>
```

---

## Rust (using `reqwest`)

`reqwest` is a popular, ergonomic HTTP client for Rust.

**`Cargo.toml` dependencies:**
```toml
[dependencies]
reqwest = { version = "0.11", features = ["json"] }
tokio = { version = "1", features = ["full"] }
serde_json = "1.0"
```

**Code:**
```rust
use reqwest::Error;
use serde_json::Value;

#[tokio::main]
async fn main() -> Result<(), Error> {
    let api_url = "https://your-api.onrender.com";
    let api_key = "pm_your_api_key_here";
    let endpoint = "/api/metrics";

    let client = reqwest::Client::new();
    let response = client
        .get(format!("{}{}", api_url, endpoint))
        .header("X-API-Key", api_key)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await?;

    if response.status().is_success() {
        let metrics: Value = response.json().await?;
        println!("Successfully fetched metrics:");
        println!("{}", serde_json::to_string_pretty(&metrics).unwrap());
    } else {
        eprintln!("HTTP Error: {} - {}", response.status(), response.text().await?);
    }

    Ok(())
}
```

---

## C# (using `HttpClient`)

This uses the standard `.NET` library for making HTTP requests.

**Code:**
```csharp
using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;

public class ApiClient
{
    private static readonly HttpClient client = new HttpClient();

    public static async Task Main(string[] args)
    {
        const string apiUrl = "https://your-api.onrender.com";
        const string apiKey = "pm_your_api_key_here";
        
        client.DefaultRequestHeaders.Accept.Clear();
        client.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        client.DefaultRequestHeaders.Add("X-API-Key", apiKey);
        client.Timeout = TimeSpan.FromSeconds(10);

        try
        {
            HttpResponseMessage response = await client.GetAsync($"{apiUrl}/api/metrics");
            response.EnsureSuccessStatusCode();
            string responseBody = await response.Content.ReadAsStringAsync();

            Console.WriteLine("Successfully fetched metrics:");
            Console.WriteLine(responseBody); // For pretty printing, you'd use a JSON library like Newtonsoft.Json
        }
        catch (HttpRequestException e)
        {
            Console.WriteLine($"\nException Caught! Message: {e.Message}");
        }
    }
}
```

---

*More languages like C++, Go, and Java can be added here following a similar pattern.*

