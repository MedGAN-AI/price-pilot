#!/usr/bin/env python3
"""
Test script for RecommendAgent migration
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_recommend_agent():
    """Test RecommendAgent with core framework"""
    print("🎯 Testing RecommendAgent Migration")
    print("=" * 50)
    
    try:
        # Test import
        print("📦 Importing RecommendAgent...")
        from src.agents.RecommendAgent.agent_new import RecommendAgent
        
        # Test instantiation
        print("🔧 Creating RecommendAgent instance...")
        agent = RecommendAgent()
        
        # Test status
        print("📊 Getting agent status...")
        status = agent.get_status()
        print(f"✅ Agent Name: {status['agent_name']}")
        print(f"✅ Framework Version: {status['framework_version']}")
        print(f"✅ Status: {status['status']}")
        print(f"✅ Tools Count: {status['tools_count']}")
        
        # Test basic functionality
        print("\n🧪 Testing basic functionality...")
        test_query = "I'm looking for red shoes"
        print(f"Query: {test_query}")
        
        response = agent.process_query(test_query)
        print(f"Response: {response[:200]}{'...' if len(response) > 200 else ''}")
        
        # Check if response contains expected elements
        if response and len(response.strip()) > 0:
            print("✅ Basic functionality test passed")
            return True
        else:
            print("⚠️ Basic functionality test questionable")
            return False
            
    except Exception as e:
        print(f"❌ RecommendAgent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_recommend_agent()
    print(f"\n{'🎉 TEST PASSED' if success else '❌ TEST FAILED'}")
    sys.exit(0 if success else 1)
