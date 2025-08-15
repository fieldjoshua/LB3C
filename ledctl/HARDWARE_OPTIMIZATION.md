# HUB75 Hardware Optimization Guide

## CPU Isolation for Better Performance

The RGB matrix library performs best with dedicated CPU cores. Here's how to isolate CPU cores on your Raspberry Pi:

### 1. Enable CPU Isolation

Edit `/boot/cmdline.txt` and add `isolcpus=3` to isolate CPU core 3:

```bash
sudo nano /boot/cmdline.txt
```

Add to the end of the line (keep it all on one line):
```
isolcpus=3
```

This dedicates CPU core 3 exclusively to the LED matrix driver.

### 2. Reboot
```bash
sudo reboot
```

### 3. Verify Isolation
```bash
cat /sys/devices/system/cpu/isolated
# Should show: 3
```

## Adafruit HAT Quality Jumper

The Adafruit RGB Matrix HAT has a quality jumper that affects display quality:

### Location
The jumper is labeled "QUALITY" on the HAT PCB, usually near the GPIO header.

### Settings:

1. **Jumper CONNECTED (Default)**:
   - Better image quality
   - Slower GPIO speed
   - Use `gpio_slowdown: 2-4` in settings
   - Recommended for most setups

2. **Jumper REMOVED**:
   - Faster GPIO speed
   - May cause flickering or artifacts
   - Can use `gpio_slowdown: 1`
   - Only for experienced users

### How to Change:
1. Power off the Pi completely
2. Locate the QUALITY jumper (small 2-pin header)
3. Add/remove the jumper
4. Power on and test

### Testing Different Settings:

**With Jumper (Quality Mode):**
```yaml
gpio_slowdown: 2      # Start here
pwm_bits: 11         # Maximum quality
pwm_lsb_nanoseconds: 130
```

**Without Jumper (Speed Mode):**
```yaml
gpio_slowdown: 1      # Can go faster
pwm_bits: 9-10       # May need to reduce
pwm_lsb_nanoseconds: 100
```

## Optimal Settings for 64x64 on Pi 3B+

### Conservative (Stable):
- GPIO Slowdown: 3
- PWM Bits: 10
- PWM LSB: 130ns
- Quality Jumper: ON

### Balanced:
- GPIO Slowdown: 2
- PWM Bits: 11
- PWM LSB: 130ns
- Quality Jumper: ON

### Performance (May flicker):
- GPIO Slowdown: 1
- PWM Bits: 9
- PWM LSB: 100ns
- Quality Jumper: OFF

## Troubleshooting

### "Can't set realtime thread priority"
This warning is normal when not running as root. The display will still work but may have slight flicker.

To fix permanently:
```bash
sudo setcap 'cap_sys_nice=eip' /usr/bin/python3
```

### Segmentation Fault
Usually caused by:
- PWM bits > 11
- Invalid GPIO slowdown
- Hardware issues

### Poor Colors/Flickering
1. Increase GPIO slowdown
2. Decrease PWM bits
3. Ensure quality jumper is connected
4. Check power supply (use 5V 4A minimum)

## Performance Monitoring

Enable "Show Refresh Rate" in the web interface to see actual FPS. Target values:
- 64x64 with PWM 11: ~80-120 Hz
- 64x64 with PWM 10: ~120-180 Hz
- 64x64 with PWM 9: ~180-250 Hz