"""
Display Constants for Price Pilot
Unicode emojis and symbols for beautiful console output
Safe approach: Define emojis as constants to avoid import-time encoding issues
"""

# Status Emojis
SUCCESS = "✅"
ERROR = "❌" 
WARNING = "⚠️"
INFO = "ℹ️"

# Agent Emojis  
ROBOT = "🤖"
TRUCK = "🚚"
PACKAGE = "📦"
SEARCH = "🔍"
CHART = "📊"
REFRESH = "🔄"
CLOCK = "⏰"
ANALYTICS = "📈"
CLIPBOARD = "📋"
CELEBRATION = "🎉"

# UI Elements
BULLET = "•"
ARROW_RIGHT = "→"
ARROW_LEFT = "←"
ARROW_UP = "↑"
ARROW_DOWN = "↓"

# Alternative ASCII versions (fallback)
SUCCESS_ASCII = "[OK]"
ERROR_ASCII = "[ERROR]"
WARNING_ASCII = "[WARN]"
ROBOT_ASCII = "[ROBOT]"
TRUCK_ASCII = "[TRUCK]"
PACKAGE_ASCII = "[PACKAGE]"

def get_emoji(name: str, use_ascii: bool = False) -> str:
    """Get emoji or ASCII fallback based on environment"""
    emoji_map = {
        'success': SUCCESS_ASCII if use_ascii else SUCCESS,
        'error': ERROR_ASCII if use_ascii else ERROR,
        'warning': WARNING_ASCII if use_ascii else WARNING,
        'robot': ROBOT_ASCII if use_ascii else ROBOT,
        'truck': TRUCK_ASCII if use_ascii else TRUCK,
        'package': PACKAGE_ASCII if use_ascii else PACKAGE,
    }
    return emoji_map.get(name, name)

# Test function
def test_unicode_support():
    """Test if current environment supports Unicode display"""
    try:
        print(f"{SUCCESS} Unicode test passed")
        return True
    except UnicodeEncodeError:
        print(f"{SUCCESS_ASCII} Unicode not supported, using ASCII fallback")
        return False

if __name__ == "__main__":
    print("Testing display constants...")
    test_unicode_support()
    print(f"{ROBOT} Robot emoji")
    print(f"{TRUCK} Truck emoji") 
    print(f"{PACKAGE} Package emoji")
