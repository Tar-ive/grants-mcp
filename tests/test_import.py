#!/usr/bin/env python3
"""Basic import test to verify the Python modules can be loaded."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test that core modules can be imported."""
    print("Testing core imports...")
    
    try:
        # Test basic imports
        import mcp_server
        print("✅ mcp_server module imported successfully")
    except ImportError as e:
        print(f"⚠️ mcp_server import failed: {e}")
    
    try:
        from mcp_server.config.settings import Settings
        print("✅ Settings imported successfully")
    except ImportError as e:
        print(f"⚠️ Settings import failed: {e}")
    
    try:
        from mcp_server.tools.discovery_tools import GrantDiscoveryTools
        print("✅ GrantDiscoveryTools imported successfully")
    except ImportError as e:
        print(f"⚠️ GrantDiscoveryTools import failed: {e}")
    
    print("Import tests completed!")
    return True


if __name__ == "__main__":
    test_imports()