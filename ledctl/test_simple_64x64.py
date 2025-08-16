#!/usr/bin/env python3
"""
Simple test for 64x64 panel - based on Adafruit's basic example
"""

import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw

# Configuration for 64x64 matrix
options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'

# IMPORTANT: For Raspberry Pi 4, use higher gpio_slowdown
options.gpio_slowdown = 4

# Try different settings
print("Testing basic 64x64 configuration...")
print("If this doesn't work, try editing the script to change:")
print("  - gpio_slowdown (try 2, 3, 4, 5)")
print("  - row_address_type (try 0, 1, 2, 3)")
print("  - Remove or change panel_type")

# Uncomment ONE of these if basic doesn't work:
# options.row_address_type = 2  # Try this first
# options.panel_type = "FM6126A"  # Or this
# options.multiplexing = 1  # Or this

matrix = RGBMatrix(options=options)

# Create a test image
image = Image.new("RGB", (64, 64))
draw = ImageDraw.Draw(image)

# Draw test pattern
# Fill with dark background
draw.rectangle((0, 0, 63, 63), fill=(20, 20, 20))

# Draw colored rectangles in each corner
draw.rectangle((0, 0, 15, 15), fill=(255, 0, 0))  # Red top-left
draw.rectangle((48, 0, 63, 15), fill=(0, 255, 0))  # Green top-right
draw.rectangle((0, 48, 15, 63), fill=(0, 0, 255))  # Blue bottom-left
draw.rectangle((48, 48, 63, 63), fill=(255, 255, 0))  # Yellow bottom-right

# Draw grid lines every 16 pixels
for i in range(0, 64, 16):
    draw.line((i, 0, i, 63), fill=(100, 100, 100))
    draw.line((0, i, 63, i), fill=(100, 100, 100))

# Draw center cross
draw.line((32, 0, 32, 63), fill=(255, 255, 255))
draw.line((0, 32, 63, 32), fill=(255, 255, 255))

# Display the image
matrix.SetImage(image)

print("\nYou should see:")
print("- Dark gray background")
print("- Red square in top-left corner")
print("- Green square in top-right corner")
print("- Blue square in bottom-left corner")
print("- Yellow square in bottom-right corner")
print("- Gray grid lines every 16 pixels")
print("- White cross in the center")

input("\nPress Enter to exit...")
matrix.Clear()