# Testing Guide for UI Fixes

## On your Raspberry Pi:

```bash
cd ~/LB3C
git pull
cd ledctl
sudo ./start.sh
```

## Test these features:

### 1. Transform Controls
- [ ] Toggle Mirror X checkbox - display should flip horizontally
- [ ] Toggle Mirror Y checkbox - display should flip vertically  
- [ ] Move Rotation slider - display should rotate (0°, 90°, 180°, 270°)

### 2. Plasma Animation
- [ ] Select Plasma from automations dropdown
- [ ] Check that parameter is now called "plasma speed" not "speed"
- [ ] Verify no duplicate speed controls appear
- [ ] Test that both global speed and plasma speed work independently

### 3. Color Parameters
- [ ] Select Strobe automation
- [ ] Color parameter should show a color picker
- [ ] Pick a color and verify it applies correctly
- [ ] Select Checkerboard animation  
- [ ] Both color1 and color2 should show color pickers

### 4. Dropdown Parameters
- [ ] Select Sparkle automation
- [ ] Color mode should show a dropdown with "white" and "rainbow" options
- [ ] Test both options work

### 5. Parameter Ranges
- [ ] Check Fire animation - cooling should range 0-100, sparking 0-255
- [ ] Check Matrix animation - trail length should range 1-50
- [ ] Verify sliders respect their min/max values

### 6. Parameter Validation
- [ ] Try to manually enter invalid values in number inputs
- [ ] Should see error messages for out-of-range values

## Expected Results:
- No JavaScript errors in browser console
- All transforms apply to animations correctly
- Color pickers work and show hex values
- Parameter ranges are enforced
- No duplicate controls or naming conflicts

## If issues occur:
- Check browser console for errors
- Check `sudo journalctl -u ledctl -f` for backend errors
- Verify all files were updated with `git status`