#!/usr/bin/env python3
"""
Diagnose animation performance issues
"""

import time
import psutil
import subprocess
import sys

def check_cpu_isolation():
    """Check if CPU isolation is working"""
    print("=== CPU Isolation Check ===")
    try:
        # Check cmdline
        with open('/proc/cmdline', 'r') as f:
            cmdline = f.read()
            if 'isolcpus=3' in cmdline:
                print("✓ CPU 3 is isolated in kernel cmdline")
            else:
                print("✗ CPU 3 is NOT isolated")
        
        # Check CPU affinity
        p = psutil.Process()
        affinity = p.cpu_affinity()
        print(f"Current process CPU affinity: {affinity}")
        
    except Exception as e:
        print(f"Could not check CPU isolation: {e}")

def check_system_load():
    """Check system load and resources"""
    print("\n=== System Load ===")
    print(f"CPU Usage: {psutil.cpu_percent(interval=1)}%")
    print(f"Memory Usage: {psutil.virtual_memory().percent}%")
    
    # Per-CPU usage
    per_cpu = psutil.cpu_percent(percpu=True, interval=1)
    for i, usage in enumerate(per_cpu):
        print(f"  CPU {i}: {usage}%")

def check_process_priority():
    """Check process scheduling priority"""
    print("\n=== Process Priority ===")
    p = psutil.Process()
    print(f"Nice value: {p.nice()}")
    
    try:
        # Check if running with real-time priority
        import os
        policy = os.sched_getscheduler(0)
        policies = {0: 'SCHED_OTHER', 1: 'SCHED_FIFO', 2: 'SCHED_RR'}
        print(f"Scheduling policy: {policies.get(policy, policy)}")
        
        if policy in [1, 2]:  # Real-time policies
            priority = os.sched_getparam(0).sched_priority
            print(f"Real-time priority: {priority}")
    except Exception as e:
        print(f"Could not check scheduling: {e}")

def check_gpio_performance():
    """Check GPIO and hardware timing"""
    print("\n=== GPIO Performance ===")
    
    # Check if SPI is enabled
    try:
        subprocess.run(['ls', '/dev/spidev*'], shell=True, capture_output=True, text=True)
        print("✓ SPI devices found")
    except:
        print("✗ No SPI devices found")
    
    # Check GPIO chip
    try:
        result = subprocess.run(['gpiodetect'], capture_output=True, text=True)
        if result.returncode == 0:
            print("GPIO chips detected:")
            print(result.stdout)
    except:
        print("gpiodetect not available")

def analyze_ledctl_logs():
    """Check recent ledctl logs for timing issues"""
    print("\n=== Recent LED Controller Logs ===")
    try:
        result = subprocess.run(
            ['journalctl', '-u', 'ledctl', '-n', '50', '--no-pager'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            logs = result.stdout
            # Look for timing-related messages
            timing_keywords = ['fps', 'frame', 'timing', 'delay', 'refresh', 'rate']
            relevant_lines = []
            
            for line in logs.split('\n'):
                if any(keyword in line.lower() for keyword in timing_keywords):
                    relevant_lines.append(line)
            
            if relevant_lines:
                print("Timing-related log entries:")
                for line in relevant_lines[-10:]:  # Last 10 relevant entries
                    print(f"  {line}")
        else:
            print("Could not read systemd logs")
    except:
        print("systemd/journalctl not available")

def check_config_settings():
    """Check current configuration settings"""
    print("\n=== Configuration Analysis ===")
    try:
        import yaml
        with open('config/device.default.yml', 'r') as f:
            config = yaml.safe_load(f)
            
        device = config.get('device', {})
        params = device.get('parameters', {})
        
        print(f"Device type: {device.get('type')}")
        print(f"Hardware mapping: {params.get('hardware_mapping')}")
        print(f"GPIO slowdown: {params.get('gpio_slowdown')}")
        print(f"PWM bits: {params.get('pwm_bits')}")
        print(f"PWM LSB nanoseconds: {params.get('pwm_lsb_nanoseconds')}")
        print(f"Limit refresh rate: {params.get('limit_refresh_rate_hz')}")
        
        # Check if settings are optimal
        if params.get('gpio_slowdown', 0) < 2:
            print("⚠ GPIO slowdown might be too low for Pi 4")
        if params.get('pwm_bits', 0) > 11:
            print("⚠ High PWM bits can cause flickering")
            
    except Exception as e:
        print(f"Could not read config: {e}")

def suggest_optimizations():
    """Suggest optimizations based on findings"""
    print("\n=== Optimization Suggestions ===")
    
    suggestions = [
        "1. Run on the Raspberry Pi with: sudo python test_pattern.py",
        "2. Try different GPIO slowdown values (2-5): --gpio-slowdown 3",
        "3. Test with lower PWM bits for stability: --pwm-bits 7",
        "4. Ensure the process runs on isolated CPU 3",
        "5. Check for other processes using the GPIO",
        "6. Monitor actual refresh rate with show_refresh_rate option",
        "7. Try disabling pwm_dither_bits if flickering persists"
    ]
    
    for suggestion in suggestions:
        print(suggestion)

def main():
    print("LED Animation Performance Diagnostics")
    print("=" * 40)
    
    # Only run certain checks on Raspberry Pi
    if sys.platform.startswith('linux'):
        check_cpu_isolation()
        check_process_priority()
        check_gpio_performance()
        analyze_ledctl_logs()
    
    check_system_load()
    check_config_settings()
    suggest_optimizations()

if __name__ == "__main__":
    main()