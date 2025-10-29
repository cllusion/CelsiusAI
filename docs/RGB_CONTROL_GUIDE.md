# 🎨 Celsius AI RGB Control Guide

## 🚀 Quick Start

Your Celsius AI now has **full RGB and hardware control** integrated! 

### 💻 How to Use:

1. **Launch Celsius AI:**
   ```bash
   python src\core\main.py
   ```

2. **Use RGB Commands at the Celsius AI prompt:**
   ```
   Celsius AI> red           # Turn motherboard red
   Celsius AI> blue          # Turn motherboard blue  
   Celsius AI> lights off    # Turn off all RGB
   Celsius AI> rgb purple    # Set RGB to purple
   Celsius AI> fan high      # Set fans to high speed
   ```

## 🎨 RGB Commands

### **Single Color Commands:**
- `red` - Set motherboard RGB to red
- `blue` - Set motherboard RGB to blue
- `green` - Set motherboard RGB to green
- `purple` - Set motherboard RGB to purple
- `yellow` - Set motherboard RGB to yellow
- `orange` - Set motherboard RGB to orange
- `white` - Set motherboard RGB to white

### **Advanced RGB Commands:**
- `lights off` - Turn off all RGB lights
- `rgb [color]` - Set RGB to any color
- `lights [color]` - Alternative RGB syntax

### **Specific Device Control:**
- `rgb motherboard red` - Control motherboard specifically
- `rgb all blue` - Control all RGB devices

## 🌪️ Fan Control Commands

- `fan high` - Set fans to high speed (80%)
- `fan low` - Set fans to low/quiet speed (30%)
- `fan max` - Set fans to maximum speed (100%)
- `fan auto` - Enable automatic temperature-based control

## 🎯 Example Session

```
Celsius AI> help
[Shows command menu with all options]

Celsius AI> red
🎨 Motherboard RGB set to RED

Celsius AI> fan high  
💨 CPU fan set to HIGH speed

Celsius AI> lights off
🔴 All RGB lights turned OFF

Celsius AI> rgb purple
🎨 Motherboard RGB set to PURPLE

Celsius AI> status
[Shows system status including hardware]
```

## 🔧 Hardware Status

Your system controls:
- **373 RGB LEDs** across 3 devices:
  - ASRock B650M-C motherboard (241 LEDs)
  - Logitech G815 Gaming Keyboard (117 LEDs)
  - Corsair Nightsword Mouse (15 LEDs)
- **CPU fans** with speed control
- **Temperature monitoring** with automatic adjustments

## 🚀 Advanced Features

### **Ultimate Hub GUI:**
- Launch: `hub` command in Celsius AI
- Hardware tab with sliders and controls
- Real-time temperature monitoring

### **Direct Python Control:**
```python
# In Python console
from openrgb import OpenRGBClient, RGBColor
client = OpenRGBClient()
client.devices[2].set_color(RGBColor(255, 0, 0))  # Red motherboard
```

### **Web API Control:**
- Hardware API available on port 5001 when running
- REST endpoints for programmatic control

## 🎉 Integration Complete!

Celsius AI now provides:
- ✅ Natural language RGB control
- ✅ Real hardware fan control  
- ✅ Temperature-based automation
- ✅ Multi-device RGB coordination
- ✅ Web learning capabilities
- ✅ Security monitoring
- ✅ Complete cybersecurity defense

**Your RGB lights are now part of the Celsius AI ecosystem!** 🌈