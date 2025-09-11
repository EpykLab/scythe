# X-SCYTHE-TARGET-VERSION Header Guide

This guide explains how to use Scythe's automatic version detection feature through the `X-SCYTHE-TARGET-VERSION` HTTP response header.

## Overview

The `X-SCYTHE-TARGET-VERSION` header allows your web application to communicate its current version to Scythe during testing. This enables you to:

- Track test results by application version
- Verify which version is being tested
- Correlate issues with specific software releases
- Ensure consistency across test environments

## Quick Start

### 1. Set the Header in Your Application

Add the `X-SCYTHE-TARGET-VERSION` header to your web application's HTTP responses:

```python
# Python/Flask
@app.after_request
def add_version_header(response):
    response.headers['X-SCYTHE-TARGET-VERSION'] = '1.3.2'
    return response
```

### 2. Run Scythe Tests

No changes needed in your Scythe test code - version detection is automatic:

```python
from scythe.core.ttp import TTP
from scythe.core.executor import TTPExecutor

class MyTTP(TTP):
    def get_payloads(self):
        yield "test_payload"
    
    def execute_step(self, driver, payload):
        driver.get("http://your-app.com")
    
    def verify_result(self, driver):
        return "welcome" in driver.page_source

ttp = MyTTP("Test", "Description")
executor = TTPExecutor(ttp=ttp, target_url="http://your-app.com")
executor.run()
```

### 3. View Results with Version Info

Scythe will automatically display version information:

```
✓ EXPECTED SUCCESS: 'test_payload' | Version: 1.3.2

Target Version Summary:
  Results with version info: 1/1
  Version 1.3.2: 1 result(s)
```

## Server-Side Implementation

### Python/Flask

```python
from flask import Flask, g

app = Flask(__name__)
APP_VERSION = "1.3.2"

@app.after_request
def add_version_header(response):
    response.headers['X-SCYTHE-TARGET-VERSION'] = APP_VERSION
    return response

# Alternative: Per-route implementation
@app.route('/api/data')
def get_data():
    response = make_response(jsonify({"data": "example"}))
    response.headers['X-SCYTHE-TARGET-VERSION'] = APP_VERSION
    return response
```

### Node.js/Express

```javascript
const express = require('express');
const app = express();

const APP_VERSION = '1.3.2';

// Global middleware
app.use((req, res, next) => {
    res.set('X-SCYTHE-TARGET-VERSION', APP_VERSION);
    next();
});

// Alternative: Per-route implementation
app.get('/api/data', (req, res) => {
    res.set('X-SCYTHE-TARGET-VERSION', APP_VERSION);
    res.json({ data: 'example' });
});
```

### Java/Spring Boot

```java
// Global filter approach
@Component
public class VersionHeaderFilter implements Filter {
    
    @Value("${app.version:1.3.2}")
    private String appVersion;
    
    @Override
    public void doFilter(ServletRequest request, ServletResponse response, 
                        FilterChain chain) throws IOException, ServletException {
        
        HttpServletResponse httpResponse = (HttpServletResponse) response;
        httpResponse.setHeader("X-SCYTHE-TARGET-VERSION", appVersion);
        
        chain.doFilter(request, response);
    }
}

// Alternative: Controller-level implementation
@RestController
public class ApiController {
    
    @Value("${app.version}")
    private String appVersion;
    
    @GetMapping("/api/data")
    public ResponseEntity<Map<String, String>> getData() {
        Map<String, String> data = Map.of("data", "example");
        
        return ResponseEntity.ok()
                .header("X-SCYTHE-TARGET-VERSION", appVersion)
                .body(data);
    }
}
```

### ASP.NET Core

```csharp
// Global middleware
public class VersionHeaderMiddleware
{
    private readonly RequestDelegate _next;
    private readonly string _version;

    public VersionHeaderMiddleware(RequestDelegate next, IConfiguration config)
    {
        _next = next;
        _version = config["AppVersion"] ?? "1.3.2";
    }

    public async Task InvokeAsync(HttpContext context)
    {
        context.Response.Headers.Add("X-SCYTHE-TARGET-VERSION", _version);
        await _next(context);
    }
}

// Register in Startup.cs
public void Configure(IApplicationBuilder app)
{
    app.UseMiddleware<VersionHeaderMiddleware>();
    // ... other middleware
}
```

### PHP

```php
// Global header (at the top of your main PHP file)
header('X-SCYTHE-TARGET-VERSION: 1.3.2');

// Or in a framework like Laravel (middleware)
class VersionHeaderMiddleware
{
    public function handle($request, Closure $next)
    {
        $response = $next($request);
        $response->headers->set('X-SCYTHE-TARGET-VERSION', '1.3.2');
        return $response;
    }
}
```

## Advanced Usage

### Dynamic Version Detection

You can dynamically set the version based on your deployment:

```python
import os
import subprocess

def get_app_version():
    # From environment variable
    version = os.getenv('APP_VERSION')
    if version:
        return version
    
    # From git tag
    try:
        result = subprocess.run(['git', 'describe', '--tags'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    # From package.json, setup.py.bak, etc.
    try:
        with open('package.json', 'r') as f:
            import json
            data = json.load(f)
            return data.get('version', 'unknown')
    except:
        pass
    
    return 'unknown'

APP_VERSION = get_app_version()

@app.after_request
def add_version_header(response):
    response.headers['X-SCYTHE-TARGET-VERSION'] = APP_VERSION
    return response
```

### Environment-Specific Versions

```python
import os

def get_version_with_env():
    base_version = "1.3.2"
    environment = os.getenv('ENVIRONMENT', 'development')
    
    if environment == 'development':
        return f"{base_version}-dev"
    elif environment == 'staging':
        return f"{base_version}-staging"
    elif environment == 'production':
        return base_version
    else:
        return f"{base_version}-{environment}"

APP_VERSION = get_version_with_env()
```

### Conditional Header Setting

Only set the header in specific environments:

```python
import os

ENABLE_VERSION_HEADER = os.getenv('ENABLE_SCYTHE_HEADERS', 'false').lower() == 'true'
APP_VERSION = "1.3.2"

@app.after_request
def add_version_header(response):
    if ENABLE_VERSION_HEADER:
        response.headers['X-SCYTHE-TARGET-VERSION'] = APP_VERSION
    return response
```

## Testing and Validation

### Test Server

Use the included test server to verify functionality:

```bash
# Start test server with version 1.3.2 on port 8080
python examples/test_server_with_version.py 8080 1.3.2

# Run Scythe tests against it
python examples/version_header_example.py http://localhost:8080
```

### Manual Verification

Check if your application sets the header correctly:

```bash
# Using curl
curl -I http://your-app.com/

# Look for:
# X-SCYTHE-TARGET-VERSION: 1.3.2

# Using browser developer tools
# 1. Open Network tab
# 2. Navigate to your application
# 3. Check response headers for X-SCYTHE-TARGET-VERSION
```

### Scythe Test Verification

Create a simple test to verify header detection:

```python
from scythe.core.headers import HeaderExtractor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Setup WebDriver with logging
options = Options()
options.add_argument("--headless")
HeaderExtractor.enable_logging_for_driver(options)

driver = webdriver.Chrome(options=options)
extractor = HeaderExtractor()

try:
    driver.get("http://your-app.com")
    version = extractor.extract_target_version(driver)
    
    if version:
        print(f"✓ Version detected: {version}")
    else:
        print("✗ No version header found")
        
finally:
    driver.quit()
```

## Troubleshooting

### No Version Information Appears

1. **Check header is set**: Use browser dev tools or curl to verify the header exists
2. **Verify header name**: Must be exactly `X-SCYTHE-TARGET-VERSION` (case-insensitive)
3. **Check WebDriver logging**: Ensure performance logging is enabled
4. **Test with example server**: Use the provided test server to isolate issues

### Inconsistent Version Detection

1. **Multiple versions**: Your application may serve different versions on different endpoints
2. **Caching**: Browser or proxy caching may serve stale responses
3. **Load balancers**: Different backend servers may have different versions

### Performance Impact

The header extraction feature:
- Uses Chrome's performance logging API
- Minimal performance overhead
- Only processes network logs when extracting headers
- Gracefully handles missing or malformed logs

## Best Practices

### Version String Format

Use semantic versioning for consistency:

```
1.2.3          # Release version
1.2.3-beta     # Beta version
1.2.3-rc1      # Release candidate
1.2.3-dev      # Development version
```

### Security Considerations

- Version information in headers is visible to clients
- Consider if version disclosure poses security risks
- Use environment variables to control header inclusion
- Avoid exposing internal build numbers or sensitive information

### CI/CD Integration

Automatically set version from your build process:

```yaml
# GitHub Actions example
- name: Set version header
  run: |
    VERSION=$(git describe --tags)
    echo "APP_VERSION=$VERSION" >> $GITHUB_ENV
    
- name: Deploy with version
  run: |
    export APP_VERSION=${{ env.APP_VERSION }}
    ./deploy.sh
```

### Monitoring and Alerting

Track version information in your monitoring:

```python
# Log version info for monitoring
import logging

@app.after_request
def add_version_header(response):
    version = get_app_version()
    response.headers['X-SCYTHE-TARGET-VERSION'] = version
    
    # Log for monitoring/alerting
    if request.headers.get('User-Agent', '').startswith('scythe'):
        logging.info(f"Scythe test against version {version}")
    
    return response
```

## API Reference

### HeaderExtractor

```python
from scythe.core.headers import HeaderExtractor

extractor = HeaderExtractor()

# Extract version header
version = extractor.extract_target_version(driver, target_url=None)

# Extract all headers
headers = extractor.extract_all_headers(driver, target_url=None)

# Get version summary from results
summary = extractor.get_version_summary(results)

# Enable logging (call during WebDriver setup)
HeaderExtractor.enable_logging_for_driver(chrome_options)
```

### Result Structure

Test results now include version information:

```python
{
    'payload': 'test_data',
    'url': 'http://example.com/page',
    'expected': True,
    'actual': True,
    'target_version': '1.3.2'  # New field
}
```

Version summary structure:

```python
{
    'total_results': 5,
    'results_with_version': 4,
    'unique_versions': ['1.3.2', '1.3.1'],
    'version_counts': {
        '1.3.2': 3,
        '1.3.1': 1
    }
}
```

## Examples

See the `examples/` directory for complete working examples:

- `version_header_example.py` - Demonstrates TTP and Journey version detection
- `test_server_with_version.py` - Test server that sets version headers

Run the examples:

```bash
# Start test server
python examples/test_server_with_version.py 8080 1.3.2

# Run example tests (in another terminal)
python examples/version_header_example.py http://localhost:8080
```



## Hybrid Version Extraction (New)

Starting with the API mode addition, HeaderExtractor includes a hybrid helper that first attempts a direct HTTP request to capture headers, then falls back to Selenium performance logs if a WebDriver is present.

- Method: HeaderExtractor.extract_target_version_hybrid(driver, target_url)
- Behavior:
  - If target_url is provided, performs a lightweight banner grab (HEAD by default) to look for X-SCYTHE-TARGET-VERSION.
  - If not found, or when no target_url is given, falls back to extract_target_version using Selenium network logs.

This approach improves reliability when you simply need headers (like target version) and are running in API mode without a browser.
