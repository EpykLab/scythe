# Scythe Use Cases and Examples

This document provides comprehensive examples of how to use Scythe for various adverse conditions testing scenarios. From security assessments to load testing and complex workflow validation, these examples demonstrate the full range of Scythe's capabilities.

## Table of Contents

- [Security Testing](#security-testing)
- [Load and Performance Testing](#load-and-performance-testing)
- [Functional Workflow Testing](#functional-workflow-testing)
- [Distributed and Geographic Testing](#distributed-and-geographic-testing)
- [Complex Integration Testing](#complex-integration-testing)
- [Industry-Specific Examples](#industry-specific-examples)
- [Advanced Testing Patterns](#advanced-testing-patterns)

## Security Testing

### 1. Web Application Security Assessment

Test security controls and validate protection mechanisms:

```python
from scythe.core.ttp import TTP
from scythe.core.executor import TTPExecutor
from scythe.auth.basic import BasicAuth
from scythe.orchestrators.scale import ScaleOrchestrator

# SQL Injection Testing
class SQLInjectionTTP(TTP):
    def __init__(self, injection_payloads, expected_result=False):
        super().__init__(
            name="SQL Injection Test",
            description="Test SQL injection protection",
            expected_result=expected_result
        )
        self.payloads = injection_payloads
    
    def get_payloads(self):
        for payload in self.payloads:
            yield payload
    
    def execute_step(self, driver, payload):
        search_field = driver.find_element_by_css_selector("#search")
        search_field.clear()
        search_field.send_keys(payload)
        driver.find_element_by_css_selector("#search-button").click()
    
    def verify_result(self, driver):
        # Check for SQL error messages or unexpected data
        page_source = driver.page_source.lower()
        error_indicators = ["sql error", "mysql_fetch", "ora-", "postgresql error"]
        return any(indicator in page_source for indicator in error_indicators)

# Authentication bypass testing
auth = BasicAuth(
    username="security_tester",
    password="test_password",
    login_url="http://app.com/login"
)

sql_injection_test = SQLInjectionTTP(
    injection_payloads=[
        "' OR 1=1--",
        "'; DROP TABLE users;--",
        "' UNION SELECT * FROM admin--",
        "admin'--",
        "' OR 'a'='a"
    ],
    expected_result=False  # Security should prevent these
)

# Run comprehensive SQL injection assessment
executor = TTPExecutor(
    ttp=sql_injection_test,
    target_url="http://app.com",
    authentication=auth
)
executor.run()
```

### 2. Authentication Security Testing

Validate authentication controls and session management:

```python
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import NavigateAction, FillFormAction, ClickAction, AssertAction

# Multi-factor authentication bypass testing
mfa_security_journey = Journey(
    name="MFA Security Assessment",
    description="Test multi-factor authentication controls"
)

# Step 1: Standard login attempt
login_step = Step("Initial Login", "Test basic authentication")
login_step.add_action(NavigateAction(url="http://app.com/login"))
login_step.add_action(FillFormAction(field_data={
    "#username": "testuser",
    "#password": "testpassword"
}))
login_step.add_action(ClickAction(selector="#login-button"))

# Step 2: MFA bypass attempt
mfa_bypass_step = Step("MFA Bypass Test", "Attempt to bypass MFA", expected_result=False)
mfa_bypass_step.add_action(NavigateAction(url="http://app.com/dashboard"))  # Direct access attempt
mfa_bypass_step.add_action(AssertAction(
    assertion_type="url_contains",
    expected_value="mfa"  # Should redirect to MFA, not dashboard
))

# Step 3: Session manipulation
session_test_step = Step("Session Security Test", "Test session handling")
session_test_step.add_action(TTPAction(ttp=SessionManipulationTTP(expected_result=False)))

mfa_security_journey.add_step(login_step)
mfa_security_journey.add_step(mfa_bypass_step)
mfa_security_journey.add_step(session_test_step)

# Execute security assessment
from scythe.journeys.executor import JourneyExecutor
executor = JourneyExecutor(journey=mfa_security_journey, target_url="http://app.com")
result = executor.run()
```

### 3. File Upload Security Testing

Test file upload controls and malicious file handling:

```python
class MaliciousFileUploadTTP(TTP):
    def __init__(self, malicious_files, expected_result=False):
        super().__init__(
            name="Malicious File Upload Test",
            description="Test file upload security controls",
            expected_result=expected_result
        )
        self.files = malicious_files
    
    def get_payloads(self):
        for file_info in self.files:
            yield file_info
    
    def execute_step(self, driver, file_info):
        file_input = driver.find_element_by_css_selector("input[type='file']")
        file_input.send_keys(file_info['path'])
        driver.find_element_by_css_selector("#upload-button").click()
    
    def verify_result(self, driver):
        # Check if malicious file was accepted
        success_indicators = ["upload successful", "file uploaded", "upload complete"]
        page_source = driver.page_source.lower()
        return any(indicator in page_source for indicator in success_indicators)

# Test various malicious file types
malicious_files = [
    {'path': '/tmp/test.php', 'type': 'PHP script'},
    {'path': '/tmp/malware.exe', 'type': 'Executable'},
    {'path': '/tmp/script.js', 'type': 'JavaScript'},
    {'path': '/tmp/payload.svg', 'type': 'SVG with script'},
    {'path': '/tmp/../../etc/passwd', 'type': 'Path traversal'}
]

file_security_test = MaliciousFileUploadTTP(
    malicious_files=malicious_files,
    expected_result=False  # Security should block these uploads
)
```

## Load and Performance Testing

### 1. High-Concurrency User Simulation

Test system performance under heavy user load:

```python
from scythe.orchestrators.scale import ScaleOrchestrator
from scythe.behaviors import HumanBehavior, MachineBehavior

# Create realistic user journey
user_shopping_journey = Journey("E-commerce Shopping Flow")

# Browse products
browse_step = Step("Product Browsing")
browse_step.add_action(NavigateAction(url="http://shop.com/products"))
browse_step.add_action(ClickAction(selector=".product-item:nth-child(1)"))
browse_step.add_action(WaitAction(wait_type="element_present", selector="#product-details"))

# Add to cart
cart_step = Step("Add to Cart")
cart_step.add_action(ClickAction(selector="#add-to-cart"))
cart_step.add_action(WaitAction(wait_type="element_present", selector=".cart-notification"))

# Checkout process
checkout_step = Step("Checkout Process")
checkout_step.add_action(ClickAction(selector="#cart-icon"))
checkout_step.add_action(ClickAction(selector="#checkout-button"))
checkout_step.add_action(FillFormAction(field_data={
    "#shipping-address": "123 Test Street",
    "#city": "Test City",
    "#zip": "12345"
}))

user_shopping_journey.add_step(browse_step)
user_shopping_journey.add_step(cart_step)
user_shopping_journey.add_step(checkout_step)

# Configure load test with human-like behavior
human_behavior = HumanBehavior(
    base_delay=2.0,
    delay_variance=1.0,
    error_probability=0.05  # 5% chance of user errors
)

# Run load test with 1000 concurrent users
load_orchestrator = ScaleOrchestrator(
    name="E-commerce Load Test",
    strategy=OrchestrationStrategy.PARALLEL,
    max_workers=50,
    ramp_up_delay=0.2
)

result = load_orchestrator.orchestrate_journey(
    journey=user_shopping_journey,
    target_url="http://shop.com",
    replications=1000,
    behavior=human_behavior
)

print(f"Load Test Results:")
print(f"  Concurrent Users: 1000")
print(f"  Success Rate: {result.success_rate:.1f}%")
print(f"  Average Response Time: {result.average_execution_time:.2f}s")
print(f"  Total Test Duration: {result.execution_time:.2f}s")
```

### 2. API Stress Testing

Test API endpoints under extreme load:

```python
class APIStressTTP(TTP):
    def __init__(self, endpoints, requests_per_second, expected_result=True):
        super().__init__(
            name="API Stress Test",
            description=f"Test API performance at {requests_per_second} RPS",
            expected_result=expected_result
        )
        self.endpoints = endpoints
        self.rps = requests_per_second
    
    def get_payloads(self):
        import time
        start_time = time.time()
        for i in range(self.rps * 60):  # Run for 1 minute
            endpoint = self.endpoints[i % len(self.endpoints)]
            yield {'endpoint': endpoint, 'request_id': i}
            
            # Control request rate
            elapsed = time.time() - start_time
            expected_time = i / self.rps
            if elapsed < expected_time:
                time.sleep(expected_time - elapsed)
    
    def execute_step(self, driver, payload):
        driver.get(f"http://api.app.com{payload['endpoint']}")
    
    def verify_result(self, driver):
        # Check for successful API response
        return driver.page_source and "error" not in driver.page_source.lower()

# Test multiple API endpoints
api_endpoints = [
    "/api/users",
    "/api/products", 
    "/api/orders",
    "/api/analytics",
    "/api/reports"
]

api_stress_test = APIStressTTP(
    endpoints=api_endpoints,
    requests_per_second=100,
    expected_result=True  # API should handle this load
)

# Use machine behavior for consistent timing
machine_behavior = MachineBehavior(delay=0.01, fail_fast=False)

executor = TTPExecutor(
    ttp=api_stress_test,
    target_url="http://api.app.com",
    behavior=machine_behavior
)
executor.run()
```

### 3. Database Connection Pool Testing

Test database performance under concurrent load:

```python
class DatabaseConnectionTTP(TTP):
    def __init__(self, concurrent_connections, expected_result=True):
        super().__init__(
            name="Database Connection Pool Test",
            description=f"Test {concurrent_connections} concurrent database connections",
            expected_result=expected_result
        )
        self.connections = concurrent_connections
    
    def get_payloads(self):
        for i in range(self.connections):
            yield f"connection_{i}"
    
    def execute_step(self, driver, connection_id):
        # Navigate to database-intensive page
        driver.get(f"http://app.com/reports?connection={connection_id}")
    
    def verify_result(self, driver):
        # Check that page loaded without database errors
        error_indicators = [
            "database connection failed",
            "connection pool exhausted",
            "too many connections",
            "database timeout"
        ]
        page_source = driver.page_source.lower()
        return not any(error in page_source for error in error_indicators)

# Test connection pool limits
db_test = DatabaseConnectionTTP(
    concurrent_connections=200,
    expected_result=True  # Should handle 200 connections
)

# Use parallel orchestration for true concurrency
parallel_orchestrator = ScaleOrchestrator(
    name="Database Concurrency Test",
    strategy=OrchestrationStrategy.PARALLEL,
    max_workers=200  # One worker per connection
)

result = parallel_orchestrator.orchestrate_ttp(
    ttp=db_test,
    target_url="http://app.com",
    replications=1
)
```

## Functional Workflow Testing

### 1. Complete User Registration Flow

Test complex multi-step user workflows:

```python
# Comprehensive user registration and onboarding
registration_journey = Journey(
    name="User Registration and Onboarding",
    description="Complete new user workflow from registration to first use"
)

# Step 1: Registration form
registration_step = Step("Account Registration", "Create new user account")
registration_step.add_action(NavigateAction(url="http://app.com/register"))
registration_step.add_action(FillFormAction(field_data={
    "#email": "test_{execution_id}@example.com",
    "#password": "SecurePassword123!",
    "#confirm_password": "SecurePassword123!",
    "#first_name": "Test",
    "#last_name": "User",
    "#terms_accepted": True
}))
registration_step.add_action(ClickAction(selector="#register-button"))
registration_step.add_action(AssertAction(
    assertion_type="page_contains",
    expected_value="registration successful"
))

# Step 2: Email verification simulation
verification_step = Step("Email Verification", "Verify email address")
verification_step.add_action(WaitAction(wait_type="time", duration=2))  # Simulate email delay
verification_step.add_action(NavigateAction(url="http://app.com/verify?token=auto_generated"))
verification_step.add_action(AssertAction(
    assertion_type="url_contains",
    expected_value="verified"
))

# Step 3: Profile completion
profile_step = Step("Profile Setup", "Complete user profile")
profile_step.add_action(NavigateAction(url="http://app.com/profile/setup"))
profile_step.add_action(FillFormAction(field_data={
    "#company": "Test Company",
    "#job_title": "Software Engineer",
    "#phone": "+1-555-0123",
    "#preferences": "email_notifications"
}))
profile_step.add_action(ClickAction(selector="#save-profile"))

# Step 4: First application use
first_use_step = Step("First Application Use", "Test initial user experience")
first_use_step.add_action(NavigateAction(url="http://app.com/dashboard"))
first_use_step.add_action(ClickAction(selector="#welcome-tour-start"))
first_use_step.add_action(WaitAction(wait_type="element_present", selector=".tour-complete"))

registration_journey.add_step(registration_step)
registration_journey.add_step(verification_step)
registration_journey.add_step(profile_step)
registration_journey.add_step(first_use_step)

# Execute with realistic timing
executor = JourneyExecutor(
    journey=registration_journey,
    target_url="http://app.com",
    behavior=HumanBehavior(base_delay=3.0, delay_variance=2.0)
)
result = executor.run()
```

### 2. File Upload and Processing Workflow

Test file handling capabilities:

```python
# File upload and processing journey
file_workflow_journey = Journey(
    name="File Upload and Processing Workflow",
    description="Test complete file upload, processing, and management"
)

# Step 1: Authentication
auth_step = Step("User Authentication")
auth_step.add_action(NavigateAction(url="http://app.com/login"))
auth_step.add_action(FillFormAction(field_data={
    "#username": "file_test_user",
    "#password": "testpassword"
}))
auth_step.add_action(ClickAction(selector="#login-button"))

# Step 2: File selection and upload
upload_step = Step("File Upload", "Upload various file types")
upload_step.add_action(NavigateAction(url="http://app.com/files/upload"))

# Test different file types
file_types = [
    "/tmp/document.pdf",
    "/tmp/image.jpg", 
    "/tmp/spreadsheet.xlsx",
    "/tmp/presentation.pptx",
    "/tmp/large_dataset.csv"
]

for file_path in file_types:
    upload_step.add_action(FillFormAction(field_data={"input[type='file']": file_path}))
    upload_step.add_action(ClickAction(selector="#upload-button"))
    upload_step.add_action(WaitAction(wait_type="element_present", selector=".upload-success"))

# Step 3: File processing verification
processing_step = Step("File Processing", "Verify files are processed correctly")
processing_step.add_action(NavigateAction(url="http://app.com/files/list"))
processing_step.add_action(WaitAction(wait_type="element_present", selector=".file-processed"))
processing_step.add_action(AssertAction(
    assertion_type="element_count",
    expected_value="5",  # All 5 files should be processed
    selector=".file-item.processed"
))

# Step 4: File download and sharing
download_step = Step("File Management", "Test download and sharing features")
download_step.add_action(ClickAction(selector=".file-item:first-child .download-btn"))
download_step.add_action(ClickAction(selector=".file-item:first-child .share-btn"))
download_step.add_action(FillFormAction(field_data={
    "#share-email": "colleague@example.com",
    "#share-message": "Here's the file you requested"
}))
download_step.add_action(ClickAction(selector="#send-share"))

file_workflow_journey.add_step(auth_step)
file_workflow_journey.add_step(upload_step)
file_workflow_journey.add_step(processing_step)
file_workflow_journey.add_step(download_step)
```

### 3. E-commerce Checkout Process

Test complete purchase workflow:

```python
# Complete e-commerce purchase flow
ecommerce_journey = Journey(
    name="E-commerce Purchase Flow",
    description="Complete customer purchase journey"
)

# Step 1: Product discovery
discovery_step = Step("Product Discovery", "Browse and search for products")
discovery_step.add_action(NavigateAction(url="http://shop.com"))
discovery_step.add_action(FillFormAction(field_data={"#search": "laptop computer"}))
discovery_step.add_action(ClickAction(selector="#search-button"))
discovery_step.add_action(WaitAction(wait_type="element_present", selector=".product-results"))

# Step 2: Product selection
selection_step = Step("Product Selection", "Select and configure product")
selection_step.add_action(ClickAction(selector=".product-item:first-child"))
selection_step.add_action(WaitAction(wait_type="element_present", selector="#product-details"))
selection_step.add_action(ClickAction(selector="#color-option-black"))
selection_step.add_action(ClickAction(selector="#memory-option-16gb"))
selection_step.add_action(ClickAction(selector="#add-to-cart"))

# Step 3: Cart management
cart_step = Step("Cart Management", "Review and modify cart")
cart_step.add_action(ClickAction(selector="#cart-icon"))
cart_step.add_action(WaitAction(wait_type="element_present", selector=".cart-items"))
cart_step.add_action(FillFormAction(field_data={"#quantity": "2"}))
cart_step.add_action(ClickAction(selector="#update-cart"))
cart_step.add_action(ClickAction(selector="#proceed-to-checkout"))

# Step 4: Checkout and payment
checkout_step = Step("Checkout Process", "Complete purchase")
checkout_step.add_action(FillFormAction(field_data={
    "#shipping-address": "123 Main Street",
    "#city": "Anytown",
    "#state": "CA",
    "#zip": "90210",
    "#card-number": "4111111111111111",
    "#expiry": "12/25",
    "#cvv": "123"
}))
checkout_step.add_action(ClickAction(selector="#place-order"))
checkout_step.add_action(WaitAction(wait_type="element_present", selector=".order-confirmation"))
checkout_step.add_action(AssertAction(
    assertion_type="page_contains",
    expected_value="order confirmed"
))

ecommerce_journey.add_step(discovery_step)
ecommerce_journey.add_step(selection_step)
ecommerce_journey.add_step(cart_step)
ecommerce_journey.add_step(checkout_step)
```

## Distributed and Geographic Testing

### 1. Global User Base Simulation

Test application performance from multiple geographic locations:

```python
from scythe.orchestrators.distributed import DistributedOrchestrator, NetworkProxy, CredentialSet

# Define global testing infrastructure
global_proxies = [
    NetworkProxy("US-West", proxy_url="proxy-us-west.example.com:8080", location="US-West"),
    NetworkProxy("US-East", proxy_url="proxy-us-east.example.com:8080", location="US-East"),
    NetworkProxy("Canada", proxy_url="proxy-canada.example.com:8080", location="Canada"),
    NetworkProxy("UK", proxy_url="proxy-uk.example.com:8080", location="UK"),
    NetworkProxy("Germany", proxy_url="proxy-germany.example.com:8080", location="Germany"),
    NetworkProxy("Japan", proxy_url="proxy-japan.example.com:8080", location="Japan"),
    NetworkProxy("Australia", proxy_url="proxy-australia.example.com:8080", location="Australia"),
    NetworkProxy("Brazil", proxy_url="proxy-brazil.example.com:8080", location="Brazil")
]

# Regional user profiles with different characteristics
regional_users = [
    CredentialSet("us_user", "user.us@example.com", "USPassword123", 
                  metadata={"timezone": "PST", "language": "en-US"}),
    CredentialSet("uk_user", "user.uk@example.com", "UKPassword123",
                  metadata={"timezone": "GMT", "language": "en-GB"}),
    CredentialSet("de_user", "user.de@example.com", "DEPassword123",
                  metadata={"timezone": "CET", "language": "de-DE"}),
    CredentialSet("jp_user", "user.jp@example.com", "JPPassword123",
                  metadata={"timezone": "JST", "language": "ja-JP"}),
    CredentialSet("au_user", "user.au@example.com", "AUPassword123",
                  metadata={"timezone": "AEST", "language": "en-AU"}),
    CredentialSet("br_user", "user.br@example.com", "BRPassword123",
                  metadata={"timezone": "BRT", "language": "pt-BR"})
]

# Create global performance test
global_performance_journey = Journey(
    name="Global Performance Assessment",
    description="Test application performance from multiple global locations"
)

# Common user workflow
global_workflow_step = Step("Global User Workflow")
global_workflow_step.add_action(NavigateAction(url="http://app.com/login"))
global_workflow_step.add_action(FillFormAction(field_data={
    "#username": "{credential.username}",
    "#password": "{credential.password}"
}))
global_workflow_step.add_action(ClickAction(selector="#login-button"))
global_workflow_step.add_action(NavigateAction(url="http://app.com/dashboard"))
global_workflow_step.add_action(WaitAction(wait_type="element_present", selector="#dashboard-content"))

global_performance_journey.add_step(global_workflow_step)

# Execute distributed test
global_orchestrator = DistributedOrchestrator(
    name="Global Performance Test",
    proxies=global_proxies,
    credentials=regional_users,
    proxy_rotation_strategy="geographic",  # Match users to nearby proxies
    credential_rotation_strategy="round_robin"
)

result = global_orchestrator.orchestrate_journey(
    journey=global_performance_journey,
    target_url="http://app.com",
    replications=200  # 200 tests distributed globally
)

# Analyze results by location
print("Global Performance Results:")
print(f"Total Executions: {result.total_executions}")
print(f"Overall Success Rate: {result.success_rate:.1f}%")

distribution_stats = result.metadata.get('distribution_stats', {})
for location, stats in distribution_stats.get('location_performance', {}).items():
    print(f"{location}:")
    print(f"  Tests: {stats['executions']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    print(f"  Avg Response Time: {stats['avg_response_time']:.2f}s")
```

### 2. CDN Performance Testing

Test Content Delivery Network performance across regions:

```python
class CDNPerformanceTTP(TTP):
    def __init__(self, test_resources, expected_result=True):
        super().__init__(
            name="CDN Performance Test",
            description="Test CDN resource loading performance",
            expected_result=expected_result
        )
        self.resources = test_resources
    
    def get_payloads(self):
        for resource in self.resources:
            yield resource
    
    def execute_step(self, driver, resource):
        import time
        start_time = time.time()
        driver.get(f"http://cdn.app.com/{resource['path']}")
        load_time = time.time() - start_time
        resource['actual_load_time'] = load_time
    
    def verify_result(self, driver):
        # Check if resource loaded successfully and within acceptable time
        return (driver.page_source and 
                len(driver.page_source) > 100 and  # Resource has content
                hasattr(self, 'current_resource') and
                self.current_resource.get('actual_load_time', 999) < 5.0)  # Under 5 seconds

# Test various CDN resources
cdn_resources = [
    {'path': 'images/hero-banner.jpg', 'type': 'image', 'expected_size': '2MB'},
    {'path': 'js/app.bundle.js', 'type': 'javascript', 'expected_size': '500KB'},
    {'path': 'css/styles.css', 'type': 'stylesheet', 'expected_size': '100KB'},
    {'path': 'videos/demo.mp4', 'type': 'video', 'expected_size': '10MB'},
    {'path': 'fonts/custom-font.woff2', 'type': 'font', 'expected_size': '50KB'}
]

cdn_test = CDNPerformanceTTP(
    test_resources=cdn_resources,
    expected_result=True  # CDN should deliver resources quickly
)

# Test from multiple locations
distributed_cdn_test = DistributedOrchestrator(
    name="CDN Performance Assessment",
    proxies=global_proxies[:4],  # Test from 4 regions
    credentials=regional_users[:4]
)

result = distributed_cdn_test.orchestrate_ttp(
    ttp=cdn_test,
    target_url="http://cdn.app.com",
    replications=len(cdn_resources)  # Test each resource once per location
)
```

## Complex Integration Testing

### 1. Microservices Integration Testing

Test complex microservices interactions:

```python
# Test complete microservices workflow
microservices_journey = Journey(
    name="Microservices Integration Test",
    description="Test interaction between multiple microservices"
)

# Step 1: User service authentication
auth_step = Step("User Service Authentication")
auth_step.add_action(TTPAction(ttp=UserServiceAuthTTP(
    service_url="http://user-service.app.com/auth",
    expected_result=True
)))

# Step 2: Product catalog service
catalog_step = Step("Product Catalog Service")
catalog_step.add_action(TTPAction(ttp=ProductCatalogTTP(
    service_url="http://catalog-service.app.com/products",
    expected_result=True
)))

# Step 3: Inventory service
inventory_step = Step("Inventory Service")
inventory_step.add_action(TTPAction(ttp=InventoryServiceTTP(
    service_url="http://inventory-service.app.com/check",
    expected_result=True
)))

# Step 4: Order processing service
order_step = Step("Order Processing Service")
order_step.add_action(TTPAction(ttp=OrderProcessingTTP(
    service_url="http://order-service.app.com/process",
    expected_result=True
)))

# Step 5: Payment service
payment_step = Step("Payment Service")
payment_step.add_action(TTPAction(ttp=PaymentServiceTTP(
    service_url="http://payment-service.app.com/charge",
    expected_result=True
)))

# Step 6: Notification service
notification_step = Step("Notification Service")
notification_step.add_action(TTPAction(ttp=NotificationServiceTTP(
    service_url="http://notification-service.app.com/send",
    expected_result=True
)))

microservices_journey.add_step(auth_step)
microservices_journey.add_step(catalog_step)
microservices_journey.add_step(inventory_step)
microservices_journey.add_step(order_step)
microservices_journey.add_step(payment_step)
microservices_journey.add_step(notification_step)

# Test microservices under load
scale_test = ScaleOrchestrator(
    name="Microservices Load Test",
    strategy=OrchestrationStrategy.PARALLEL,
    max_workers=20
)

result = scale_test.orchestrate_journey(
    journey=microservices_journey,
    target_url="http://app.com",
    replications=100
)
```

### 2. Third-Party Integration Testing

Test integrations with external services:

```python
class ThirdPartyIntegrationTTP(TTP):
    def __init__(self, integration_configs, expected_result=True):
        super().__init__(
            name="Third-Party Integration Test",
            description="Test external service integrations",
            expected_result=expected_result
        )
        self.integrations = integration_configs
    
    def get_payloads(self):
        for integration in self.integrations:
            yield integration
    
    def execute_step(self, driver, integration):
        # Test specific integration
        driver.get(f"http://app.com/integrations/{integration['name']}/test")
        
        # Fill integration-specific test data
        if integration['type'] == 'payment':
            driver.find_element_by_css_selector("#test-payment-amount").send_keys("10.00")
        elif integration['type'] == 'email':
            driver.find_element_by_css_selector("#test-email").send_keys("test@example.com")
        elif integration['type'] == 'analytics':
            driver.find_element_by_css_selector("#test-event").send_keys("page_view")
        
        driver.find_element_by_css_selector("#test-integration").click