#!/usr/bin/env python3
"""
Behavior Demo Script for Scythe Framework

This script demonstrates how to use different behaviors with TTPs to emulate
various attack patterns and execution styles.
"""

import sys
import os

# Add the parent directory to the path so we can import scythe
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.core.executor import TTPExecutor
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.payloads.generators import StaticPayloadGenerator
from scythe.behaviors import HumanBehavior, MachineBehavior, StealthBehavior, DefaultBehavior

def demo_human_behavior():
    """
    Demonstrate human-like behavior during a login bruteforce attack.
    """
    print("\n" + "="*60)
    print("DEMO: Human Behavior")
    print("="*60)
    print("This demo shows human-like interaction patterns:")
    print("- Variable delays with realistic timing")
    print("- Mouse movements and page scanning")
    print("- Slower startup and gradual acceleration")
    print("- Natural pauses and result checking")
    
    # Create a payload generator with common passwords
    payload_generator = StaticPayloadGenerator([
        "password123",
        "admin",
        "123456",
        "password",
        "letmein"
    ])
    
    # Create the TTP
    login_ttp = LoginBruteforceTTP(
        payload_generator=payload_generator,
        username="admin",
        username_selector="#username",
        password_selector="#password",
        submit_selector="#submit"
    )
    
    # Create human behavior
    human_behavior = HumanBehavior(
        base_delay=3.0,          # Slower base timing
        delay_variance=1.5,      # High variance for realism
        typing_delay=0.15,       # Human-like typing speed
        mouse_movement=True,     # Enable mouse movements
        max_consecutive_failures=3  # Give up after 3 failures like a human
    )
    
    # Create executor with human behavior
    executor = TTPExecutor(
        ttp=login_ttp,
        target_url="http://localhost:8080/login",  # Replace with your test target
        headless=False,  # Show browser for demo
        behavior=human_behavior
    )
    
    print("Starting human behavior demo...")
    print("Watch for:")
    print("- Random delays between actions")
    print("- Mouse movements and scrolling")
    print("- Variable typing speeds")
    
    # Uncomment to run the demo
    # executor.run()
    print(f"Demo configured with {executor.ttp.name} (uncomment executor.run() to execute)")

def demo_machine_behavior():
    """
    Demonstrate machine-like behavior during a login bruteforce attack.
    """
    print("\n" + "="*60)
    print("DEMO: Machine Behavior")
    print("="*60)
    print("This demo shows machine-like interaction patterns:")
    print("- Consistent, predictable timing")
    print("- No unnecessary movements or delays")
    print("- Systematic approach with retries")
    print("- Fail-fast on critical errors")
    
    # Create a payload generator
    payload_generator = StaticPayloadGenerator([
        "admin123",
        "root",
        "password1",
        "test123",
        "demo"
    ])
    
    # Create the TTP
    login_ttp = LoginBruteforceTTP(
        payload_generator=payload_generator,
        username="admin",
        username_selector="#username",
        password_selector="#password",
        submit_selector="#submit"
    )
    
    # Create machine behavior
    machine_behavior = MachineBehavior(
        delay=0.5,              # Fast, consistent timing
        max_retries=3,          # Limited retries
        retry_delay=1.0,        # Fixed retry delay
        fail_fast=True          # Stop on critical errors
    )
    
    # Create executor with machine behavior
    executor = TTPExecutor(
        ttp=login_ttp,
        target_url="http://localhost:8080/login",  # Replace with your test target
        headless=True,  # Machines typically run headless
        behavior=machine_behavior
    )
    
    print("Starting machine behavior demo...")
    print("Watch for:")
    print("- Consistent timing between requests")
    print("- No unnecessary actions")
    print("- Quick failure recovery")
    
    # Uncomment to run the demo
    # executor.run()
    print(f"Demo configured with {executor.ttp.name} (uncomment executor.run() to execute)")

def demo_stealth_behavior():
    """
    Demonstrate stealth behavior during a login bruteforce attack.
    """
    print("\n" + "="*60)
    print("DEMO: Stealth Behavior")
    print("="*60)
    print("This demo shows stealth interaction patterns:")
    print("- Highly variable timing to avoid detection")
    print("- Session resets and user agent rotation")
    print("- Reconnaissance and cleanup activities")
    print("- Conservative failure handling")
    
    # Create a payload generator
    payload_generator = StaticPayloadGenerator([
        "secret123",
        "hidden",
        "stealth1"
    ])
    
    # Create the TTP
    login_ttp = LoginBruteforceTTP(
        payload_generator=payload_generator,
        username="user",
        username_selector="#username",
        password_selector="#password",
        submit_selector="#submit"
    )
    
    # Create stealth behavior
    stealth_behavior = StealthBehavior(
        min_delay=5.0,                    # Longer minimum delays
        max_delay=15.0,                   # High maximum delays
        burst_probability=0.05,           # Low chance of bursts
        long_pause_probability=0.2,       # Higher chance of long pauses
        long_pause_duration=45.0,         # Longer pauses
        max_requests_per_session=10,      # Fewer requests per session
        session_cooldown=120.0            # Longer cooldown periods
    )
    
    # Create executor with stealth behavior
    executor = TTPExecutor(
        ttp=login_ttp,
        target_url="http://localhost:8080/login",  # Replace with your test target
        headless=False,  # Show browser to see stealth actions
        behavior=stealth_behavior
    )
    
    print("Starting stealth behavior demo...")
    print("Watch for:")
    print("- Long, variable delays")
    print("- Reconnaissance activities")
    print("- Session resets and cleanup")
    print("- Conservative approach")
    
    # Uncomment to run the demo
    # executor.run()
    print(f"Demo configured with {executor.ttp.name} (uncomment executor.run() to execute)")

def demo_default_behavior():
    """
    Demonstrate default behavior (original TTPExecutor functionality).
    """
    print("\n" + "="*60)
    print("DEMO: Default Behavior")
    print("="*60)
    print("This demo shows the original TTPExecutor behavior:")
    print("- Fixed delay between actions")
    print("- No special behaviors or patterns")
    print("- Backward compatibility with existing code")
    
    # Create a payload generator
    payload_generator = StaticPayloadGenerator([
        "default123",
        "original",
        "legacy"
    ])
    
    # Create the TTP
    login_ttp = LoginBruteforceTTP(
        payload_generator=payload_generator,
        username="test",
        username_selector="#username",
        password_selector="#password",
        submit_selector="#submit"
    )
    
    # Create default behavior (or use None for same effect)
    default_behavior = DefaultBehavior(delay=1.0)
    
    # Create executor with default behavior
    executor = TTPExecutor(
        ttp=login_ttp,
        target_url="http://localhost:8080/login",  # Replace with your test target
        headless=True,
        behavior=default_behavior  # Could also use behavior=None
    )
    
    print("Starting default behavior demo...")
    print("This should behave exactly like the original implementation")
    
    # Uncomment to run the demo
    # executor.run()
    print(f"Demo configured with {executor.ttp.name} (uncomment executor.run() to execute)")

def demo_no_behavior():
    """
    Demonstrate running without any behavior (original functionality).
    """
    print("\n" + "="*60)
    print("DEMO: No Behavior (Original)")
    print("="*60)
    print("This demo shows running without any behavior parameter:")
    print("- Maintains original TTPExecutor functionality")
    print("- No behavior-specific features")
    print("- Backward compatible")
    
    # Create a payload generator
    payload_generator = StaticPayloadGenerator([
        "nobehavior123",
        "vanilla"
    ])
    
    # Create the TTP
    login_ttp = LoginBruteforceTTP(
        payload_generator=payload_generator,
        username="test",
        username_selector="#username",
        password_selector="#password",
        submit_selector="#submit"
    )
    
    # Create executor WITHOUT behavior parameter
    executor = TTPExecutor(
        ttp=login_ttp,
        target_url="http://localhost:8080/login",  # Replace with your test target
        headless=True
        # Note: no behavior parameter - uses original logic
    )
    
    print("Starting no-behavior demo...")
    print("This uses the original TTPExecutor implementation")
    
    # Uncomment to run the demo
    # executor.run()
    print(f"Demo configured with {executor.ttp.name} (uncomment executor.run() to execute)")

def demo_custom_behavior():
    """
    Demonstrate creating and using a custom behavior.
    """
    print("\n" + "="*60)
    print("DEMO: Custom Behavior")
    print("="*60)
    print("This demo shows how to create a custom behavior class")
    
    from scythe.behaviors.base import Behavior
    
    class CustomBehavior(Behavior):
        """Custom behavior that prints messages at each step."""
        
        def __init__(self):
            super().__init__(
                name="Custom Demo Behavior",
                description="A custom behavior that demonstrates the behavior framework"
            )
            
        def pre_execution(self, driver, target_url):
            print(f"🚀 Custom: Starting execution on {target_url}")
            
        def pre_step(self, driver, payload, step_number):
            print(f"⚡ Custom: About to try payload '{payload}' (step {step_number})")
            
        def post_step(self, driver, payload, step_number, success):
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"📊 Custom: Step {step_number} result: {status}")
            
        def post_execution(self, driver, results):
            print(f"🎯 Custom: Execution complete. Found {len(results)} successes")
            
        def get_step_delay(self, step_number):
            # Gradually decrease delay as we gain confidence
            return max(0.5, 2.0 - (step_number * 0.1))
    
    # Create a payload generator
    payload_generator = StaticPayloadGenerator([
        "custom123",
        "behavior",
        "demo"
    ])
    
    # Create the TTP
    login_ttp = LoginBruteforceTTP(
        payload_generator=payload_generator,
        username="custom",
        username_selector="#username",
        password_selector="#password",
        submit_selector="#submit"
    )
    
    # Create custom behavior
    custom_behavior = CustomBehavior()
    
    # Create executor with custom behavior
    executor = TTPExecutor(
        ttp=login_ttp,
        target_url="http://localhost:8080/login",  # Replace with your test target
        headless=True,
        behavior=custom_behavior
    )
    
    print("Starting custom behavior demo...")
    print("Watch for custom messages at each step")
    
    # Uncomment to run the demo
    # executor.run()
    print(f"Demo configured with {executor.ttp.name} (uncomment executor.run() to execute)")

def main():
    """
    Main function to run all behavior demos.
    """
    print("Scythe Framework - Behavior Demo")
    print("="*60)
    print("This script demonstrates the new behavior system in Scythe.")
    print("\nIMPORTANT: Update the target_url in each demo function")
    print("to point to your test application before running.")
    print("\nTo actually execute the demos, uncomment the executor.run()")
    print("lines in each demo function.")
    
    # Run all demos
    demo_default_behavior()
    demo_no_behavior()
    demo_human_behavior()
    demo_machine_behavior()
    demo_stealth_behavior()
    demo_custom_behavior()
    
    print("\n" + "="*60)
    print("All demos completed!")
    print("To run a specific demo, call the individual demo function.")
    print("\nExample usage:")
    print("  python behavior_demo.py")
    print("  # Or import and call specific demos:")
    print("  from behavior_demo import demo_human_behavior")
    print("  demo_human_behavior()")

if __name__ == "__main__":
    main()