# Scythe Framework Documentation

Welcome to the comprehensive documentation for Scythe, an extensible framework for emulating attacker TTPs (Tactics, Techniques, and Procedures) using browser automation.

## 📚 Documentation Index

### Getting Started

- **[Getting Started Guide](GETTING_STARTED.md)** - Your first steps with Scythe
  - Installation and setup
  - Basic concepts and terminology
  - Your first TTP execution
  - Common patterns and examples

### Core Components

- **[TTPs Framework](TTPS.md)** - Complete guide to Tactics, Techniques, and Procedures
  - Understanding TTPs
  - Built-in TTPs (Login Brute Force, SQL Injection, UUID Guessing)
  - Creating custom TTPs
  - Advanced patterns and best practices

- **[Payload Generators](PAYLOAD_GENERATORS.md)** - Comprehensive payload generation guide
  - Built-in generators (Static, Wordlist)
  - Creating custom generators
  - Performance optimization
  - Advanced patterns

- **[TTP Executor](EXECUTOR.md)** - The execution engine
  - Configuration options
  - Advanced usage patterns
  - Error handling and recovery
  - Performance optimization

- **[Behaviors Framework](BEHAVIORS.md)** - Control execution patterns
  - Built-in behaviors (Human, Machine, Stealth, Default)
  - Creating custom behaviors
  - Integration with TTPs
  - Best practices

### Reference

- **[API Reference](API_REFERENCE.md)** - Complete API documentation
  - Class definitions
  - Method signatures
  - Type hints
  - Examples for all components

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/YourOrg/scythe.git
cd scythe
pip install -r requirements.txt
```

### Basic Example

```python
from scythe.core.executor import TTPExecutor
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.payloads.generators import StaticPayloadGenerator
from scythe.behaviors import HumanBehavior

# Create components
passwords = StaticPayloadGenerator(["password", "admin", "123456"])
login_ttp = LoginBruteforceTTP(
    payload_generator=passwords,
    username="admin",
    username_selector="#username",
    password_selector="#password",
    submit_selector="#submit"
)
human_behavior = HumanBehavior(base_delay=2.0, mouse_movement=True)

# Execute
executor = TTPExecutor(
    ttp=login_ttp,
    target_url="http://example.com/login",
    behavior=human_behavior
)
executor.run()
```

## 🏗️ Framework Architecture

```
Scythe Framework
├── Core Engine
│   ├── TTP (Abstract Base Class)
│   └── TTPExecutor (Execution Engine)
├── TTPs (Attack Implementations)
│   ├── Web TTPs
│   │   ├── Login Brute Force
│   │   ├── SQL Injection
│   │   └── UUID Guessing
│   └── Custom TTPs
├── Payload Generators
│   ├── Static Payloads
│   ├── Wordlist Payloads
│   └── Custom Generators
└── Behaviors (Execution Control)
    ├── Human Behavior
    ├── Machine Behavior
    ├── Stealth Behavior
    └── Custom Behaviors
```

## 📖 Documentation Roadmap

### For Beginners

1. **Start with [Getting Started](GETTING_STARTED.md)**
   - Learn the basic concepts
   - Run your first TTP
   - Understand the results

2. **Explore [TTPs Framework](TTPS.md)**
   - Understand built-in TTPs
   - Learn to create custom TTPs
   - Follow best practices

3. **Read [Behaviors Framework](BEHAVIORS.md)**
   - Add realism to your tests
   - Choose the right behavior
   - Create custom behaviors

### For Intermediate Users

1. **Deep dive into [Payload Generators](PAYLOAD_GENERATORS.md)**
   - Create sophisticated payload strategies
   - Optimize for performance
   - Handle large datasets

2. **Master [TTP Executor](EXECUTOR.md)**
   - Advanced configuration
   - Error handling
   - Integration patterns

3. **Reference [API Documentation](API_REFERENCE.md)**
   - Complete method signatures
   - Type hints and examples
   - Best practices

### For Advanced Users

1. **Framework Extension**
   - Create complex custom TTPs
   - Build specialized behaviors
   - Integrate with CI/CD

2. **Performance Optimization**
   - Large-scale testing
   - Memory management
   - Parallel execution

3. **Contributing**
   - Code standards
   - Testing guidelines
   - Documentation updates

## 🎯 Use Cases by Documentation

### Security Testing
- **Primary:** [TTPs Framework](TTPS.md)
- **Supporting:** [Getting Started](GETTING_STARTED.md), [Payload Generators](PAYLOAD_GENERATORS.md)

### Red Team Operations
- **Primary:** [Behaviors Framework](BEHAVIORS.md) (Stealth Behavior)
- **Supporting:** [TTPs Framework](TTPS.md), [TTP Executor](EXECUTOR.md)

### Automated Testing / CI/CD
- **Primary:** [TTP Executor](EXECUTOR.md) (Machine Behavior)
- **Supporting:** [API Reference](API_REFERENCE.md), [TTPs Framework](TTPS.md)

### Research and Development
- **Primary:** [API Reference](API_REFERENCE.md)
- **Supporting:** All documentation for comprehensive understanding

### Training and Education
- **Primary:** [Getting Started](GETTING_STARTED.md)
- **Supporting:** [TTPs Framework](TTPS.md), [Behaviors Framework](BEHAVIORS.md)

## 🔍 Finding What You Need

### I want to...

**...get started quickly**
→ [Getting Started Guide](GETTING_STARTED.md)

**...understand TTPs**
→ [TTPs Framework](TTPS.md)

**...create realistic attack simulations**
→ [Behaviors Framework](BEHAVIORS.md)

**...generate custom payloads**
→ [Payload Generators](PAYLOAD_GENERATORS.md)

**...integrate with automation**
→ [TTP Executor](EXECUTOR.md)

**...look up specific methods**
→ [API Reference](API_REFERENCE.md)

**...see code examples**
→ Any documentation file + `examples/` directory

## 📋 Common Tasks

### Task: Test a Login Form

1. Read: [Getting Started](GETTING_STARTED.md) - "Your First TTP"
2. Reference: [TTPs Framework](TTPS.md) - "LoginBruteforceTTP"
3. Enhance: [Behaviors Framework](BEHAVIORS.md) - "HumanBehavior"

### Task: Create Custom Attack

1. Read: [TTPs Framework](TTPS.md) - "Creating Custom TTPs"
2. Reference: [API Reference](API_REFERENCE.md) - "TTP Class"
3. Support: [Payload Generators](PAYLOAD_GENERATORS.md)

### Task: Automate Security Testing

1. Read: [TTP Executor](EXECUTOR.md) - "CI/CD Integration"
2. Reference: [Behaviors Framework](BEHAVIORS.md) - "MachineBehavior"
3. Support: [API Reference](API_REFERENCE.md)

### Task: Evade Detection

1. Read: [Behaviors Framework](BEHAVIORS.md) - "StealthBehavior"
2. Reference: [TTP Executor](EXECUTOR.md) - "Advanced Patterns"
3. Support: [TTPs Framework](TTPS.md) - "Best Practices"

## 🛠️ Development Resources

### Code Organization

```
scythe/
├── scythe/                 # Core framework code
│   ├── core/              # TTP and Executor classes
│   ├── ttps/              # TTP implementations
│   ├── payloads/          # Payload generators
│   └── behaviors/         # Behavior implementations
├── docs/                  # Documentation (you are here)
├── examples/              # Example scripts and demos
└── tests/                 # Test suite
```

### Example Scripts

- `examples/behavior_demo.py` - Comprehensive behavior examples
- `examples/custom_ttp.py` - Custom TTP implementation
- `examples/payload_patterns.py` - Advanced payload generation
- `examples/ci_integration.py` - CI/CD integration example

### Testing

```bash
# Run tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_ttps.py

# Run with coverage
python -m pytest tests/ --cov=scythe
```

## 📄 Documentation Standards

### Writing Guidelines

- **Clarity:** Write for your intended audience level
- **Examples:** Include practical, working examples
- **Structure:** Use consistent formatting and organization
- **Cross-references:** Link to related documentation
- **Updates:** Keep documentation in sync with code

### Documentation Types

- **Tutorials:** Step-by-step learning (Getting Started)
- **How-to Guides:** Solution-oriented (TTPs, Behaviors)
- **Reference:** Information-oriented (API Reference)
- **Explanation:** Understanding-oriented (Architecture, Concepts)

## 🤝 Contributing to Documentation

### Quick Fixes

- Fix typos, broken links, or outdated information
- Improve examples or add missing details
- Update code samples to match current API

### Major Contributions

- Add new sections for new features
- Create additional examples and use cases
- Improve organization and navigation
- Add diagrams and visual aids

### Documentation Workflow

1. **Identify needs** - What's missing or unclear?
2. **Plan structure** - How does it fit with existing docs?
3. **Write content** - Follow style guidelines
4. **Review examples** - Ensure code works
5. **Cross-reference** - Link to related content
6. **Test navigation** - Verify user experience

## 📞 Getting Help

### Documentation Issues

- **Unclear instructions:** Create an issue describing the confusion
- **Missing information:** Request specific additions
- **Outdated content:** Report what needs updating
- **Broken examples:** Provide error details and environment info

### Support Channels

- **GitHub Issues:** Bug reports and feature requests
- **Discussions:** Questions and community help
- **Wiki:** Community-contributed examples and tips

## 🚀 What's Next?

After reading the documentation:

1. **Try the examples** in the `examples/` directory
2. **Experiment** with different TTPs and behaviors
3. **Create custom implementations** for your specific needs
4. **Contribute back** improvements and new features
5. **Share your experience** with the community

## 📈 Documentation Metrics

We track documentation effectiveness through:

- **Completeness:** Coverage of all framework features
- **Accuracy:** Code examples that work as shown
- **Usability:** Clear navigation and helpful organization
- **Currency:** Regular updates with code changes

---

**Ready to get started?** Begin with the [Getting Started Guide](GETTING_STARTED.md) and explore the powerful capabilities of the Scythe framework!

For questions, improvements, or contributions, please engage with our community through GitHub issues and discussions.