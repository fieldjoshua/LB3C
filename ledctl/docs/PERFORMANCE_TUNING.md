# Performance Tuning Guide for LB3C

## Overview

This guide covers various performance optimizations for the LB3C LED Control System, particularly for HUB75 matrices on Raspberry Pi.

## CPU Optimization

### 1. CPU Isolation

Isolating a CPU core for LED control can significantly improve timing stability:

```bash
# Edit /boot/cmdline.txt and add:
isolcpus=3  # Isolates core 3 on Pi 3B+/4

# Verify after reboot:
cat /sys/devices/system/cpu/isolated
```

The setup.sh script now automatically offers to configure this.

### 2. CPU Governor

Set CPU to performance mode for consistent timing:

```bash
# Install cpufrequtils
sudo apt-get install cpufrequtils

# Set performance governor
sudo cpufreq-set -g performance

# Make persistent
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
```

### 3. Process Priority

Run the LED control with real-time priority:

```bash
# In systemd service (already configured):
Nice=-20
CPUSchedulingPolicy=fifo
CPUSchedulingPriority=99
```

## HUB75 Hardware Settings

### Optimal Settings by Use Case

#### Maximum Quality (Static displays, art):
```yaml
hub75:
  gpio_slowdown: 3
  pwm_bits: 11
  pwm_lsb_nanoseconds: 130
  show_refresh_rate: true
  dithering: 1
```

#### Balanced (General use):
```yaml
hub75:
  gpio_slowdown: 2
  pwm_bits: 11
  pwm_lsb_nanoseconds: 130
  disable_hardware_pulsing: true
```

#### High Performance (Fast animations):
```yaml
hub75:
  gpio_slowdown: 1
  pwm_bits: 9
  pwm_lsb_nanoseconds: 100
  limit_refresh_rate_hz: 120
```

### Hardware Quality Jumper

The Adafruit RGB Matrix HAT has a quality jumper that affects timing:

- **Jumper ON (default)**: Better quality, requires higher gpio_slowdown
- **Jumper OFF**: Faster updates, may cause artifacts

To change:
1. Power off completely
2. Locate the QUALITY jumper near GPIO header
3. Add/remove jumper
4. Adjust gpio_slowdown accordingly

## Animation Optimization

### Frame Rate Considerations

- 64x64 matrix can handle 60-120 FPS depending on settings
- Use `fps_cap` in config to limit unnecessary updates:

```yaml
render:
  fps_cap: 60  # Limit to 60 FPS
```

### Memory Optimization

The enhanced animations now use:
- Pre-calculated position arrays
- Vectorized numpy operations
- Reduced memory allocations
- Frame skipping on slow systems

### Procedural vs File Animations

Procedural animations are more CPU efficient:
- No file I/O
- No decoding overhead
- Predictable memory usage
- Can be optimized per-frame

## Network Optimization

### WebSocket Overhead

The system now reduces WebSocket messages:
- Frame info sent every 100ms instead of per-frame
- Bulk parameter updates
- Client-side throttling

### API Rate Limiting

Configure appropriate limits in .env:
```bash
RATE_LIMIT_DEFAULT="60 per minute"
RATE_LIMIT_UPLOAD="10 per hour"
```

## System Optimization

### Disable Unnecessary Services

```bash
# Disable bluetooth if not needed
sudo systemctl disable bluetooth
sudo systemctl disable hciuart

# Disable WiFi power management
sudo iwconfig wlan0 power off
```

### Memory Settings

Add to /boot/config.txt:
```
gpu_mem=128  # Minimum GPU memory
```

### Storage Optimization

Use faster SD card (Class 10/A2) and enable trim:
```bash
sudo fstrim -v /
```

## Monitoring Performance

### Built-in Monitoring

Enable refresh rate display:
```python
hub75:
  show_refresh_rate: true
```

### System Monitoring

```bash
# CPU usage by core
htop

# Temperature
vcgencmd measure_temp

# Check for throttling
vcgencmd get_throttled
```

### Performance Testing

Use the included test script:
```bash
cd /home/pi/LB3C/ledctl
python tests/performance_test.py
```

## Troubleshooting Performance Issues

### Symptoms and Solutions

**Flickering:**
- Increase gpio_slowdown
- Reduce pwm_bits
- Check power supply (use 5V 4A+)
- Enable quality jumper

**Low Frame Rate:**
- Reduce pwm_bits
- Decrease resolution if chained
- Check CPU throttling
- Disable unnecessary features

**Color Artifacts:**
- Increase pwm_lsb_nanoseconds
- Enable dithering
- Check ribbon cable connections
- Use shorter ribbon cables

**Timing Issues:**
- Enable CPU isolation
- Set performance governor
- Disable hardware pulsing
- Use scan_mode=1 (interlaced)

## Best Practices

1. **Start Conservative**: Begin with stable settings and optimize gradually
2. **Monitor Temperature**: Keep Pi below 80°C
3. **Use Good Power**: 5V 4A minimum for 64x64 matrix
4. **Test Thoroughly**: Run for extended periods before production
5. **Document Changes**: Keep notes on what settings work best

## Advanced Tuning

### Custom Pixel Mappers

For non-standard layouts, implement custom mapping in `core/mapper.py`

### Hardware Modifications

- Add heatsinks to Pi CPU/GPU
- Use active cooling for enclosed installations
- Consider Pi 4 for demanding applications
- Use quality ribbon cables (< 30cm)

### Compiler Optimizations

Rebuild rgb-matrix library with optimizations:
```bash
cd rpi-rgb-led-matrix
make clean
make HARDWARE_DESC=adafruit-hat CXXFLAGS="-O3 -march=native"
```

## Conclusion

Performance tuning is iterative. Start with recommended settings and adjust based on your specific hardware and requirements. The new optimizations in LB3C should provide significant improvements out of the box.