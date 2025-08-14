# HUB75 Optimization Guide for Adafruit HAT

## Current Settings (Good for Most Cases)

Your config is already set for Adafruit HAT:
```yaml
hardware_mapping: "adafruit-hat"  # Correct for Adafruit RGB Matrix HAT
gpio_slowdown: 2                   # Good starting point
pwm_bits: 11                       # High color depth
pwm_lsb_nanoseconds: 130          # Good for most panels
```

## Optimization Tips for Your 64x64 Panel

### 1. **GPIO Slowdown Tuning**
The `gpio_slowdown` parameter is crucial for stability vs performance:
- `1` = Fastest but may cause flickering
- `2` = Current setting, good balance (recommended)
- `3` = More stable but slower refresh
- `4` = Most stable but lowest performance

Test different values:
```bash
# Edit config/device.yml and try:
gpio_slowdown: 1  # If no flickering, keep it
gpio_slowdown: 3  # If you see glitches/flickering
```

### 2. **PWM Settings for Color Quality**
```yaml
pwm_bits: 11              # Current: 2048 color levels per channel
pwm_lsb_nanoseconds: 130  # Fine-tune for your panel
```

For smoother gradients on 64x64:
- Try `pwm_bits: 10` for better performance
- Or `pwm_bits: 12` for even better colors (may reduce refresh rate)

### 3. **Panel-Specific Optimizations**

Add these to your hub75 config for better quality:
```yaml
# Additional optimizations
led_rgb_sequence: "RGB"     # Match your panel's color order
pixel_mapper_config: ""     # For special panel arrangements
scan_mode: 0               # 0=progressive, 1=interlaced
row_address_type: 0        # 0=direct, 1=AB-addressed
multiplexing: 0            # Panel-specific multiplexing
```

### 4. **Performance vs Quality Trade-offs**

**For Maximum Performance:**
```yaml
pwm_bits: 9
gpio_slowdown: 1
pwm_dither_bits: 0
```

**For Maximum Quality:**
```yaml
pwm_bits: 12
gpio_slowdown: 3
pwm_dither_bits: 2
```

### 5. **Refresh Rate Optimization**

Add to config:
```yaml
limit_refresh_rate_hz: 120  # Limit max refresh rate
show_refresh_rate: true     # Display actual refresh rate
```

## Testing Your Optimization

1. **Check Refresh Rate**:
   ```bash
   # Add to config:
   show_refresh_rate: true
   ```

2. **Test Patterns**:
   - Use "Plasma" to check for smooth gradients
   - Use "Strobe" to check for flicker
   - Use "Rainbow Cycle" for color accuracy

3. **Common Issues & Solutions**:
   - **Flickering**: Increase `gpio_slowdown`
   - **Ghosting**: Decrease `pwm_bits`
   - **Poor colors**: Adjust `pwm_lsb_nanoseconds`
   - **Slow refresh**: Decrease `pwm_bits` or `gpio_slowdown`

## Recommended Settings for 64x64 on Pi 3B+

```yaml
hub75:
  rows: 64
  cols: 64
  chain_length: 1
  parallel: 1
  hardware_mapping: "adafruit-hat"
  gpio_slowdown: 2          # Start here, try 1 if stable
  brightness: 85
  pwm_bits: 10              # Good balance for 64x64
  pwm_lsb_nanoseconds: 130
  limit_refresh_rate_hz: 100
  show_refresh_rate: false  # Set true to monitor
```

## Monitor Performance

Add this temporarily to see actual performance:
```yaml
show_refresh_rate: true
```

Then watch the console output to see your actual refresh rate!