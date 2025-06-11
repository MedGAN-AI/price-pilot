#!/usr/bin/env python3
"""
Final Comprehensive Agent Verification
Tests ALL 6 agents with Core Framework v2
"""

import sys
import time
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_all_agents():
    """Test all 6 agents for Core Framework v2 compliance"""
    print("🎯 FINAL COMPREHENSIVE AGENT VERIFICATION")
    print("=" * 70)
    print(f"🕐 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # All 6 agents configuration
    agents_config = [
        {
            "name": "ChatAgent",
            "import_path": "src.agents.ChatAgent.agent",
            "class_name": "ChatAgent",
            "test_query": "Hello, can you help me?",
            "expected_pattern": "Structured Chat"
        },
        {
            "name": "InventoryAgent", 
            "import_path": "src.agents.InventoryAgent.agent",
            "class_name": "InventoryAgent",
            "test_query": "Check stock for SHOES-RED-001",
            "expected_pattern": "ReAct"
        },
        {
            "name": "LogisticsAgent",
            "import_path": "src.agents.LogisticsAgent.agent", 
            "class_name": "LogisticsAgent",
            "test_query": "Track shipment AR123456789SA",
            "expected_pattern": "ReAct"
        },
        {
            "name": "RecommendAgent",
            "import_path": "src.agents.RecommendAgent.agent",
            "class_name": "RecommendAgent", 
            "test_query": "Find red running shoes",
            "expected_pattern": "ReAct"
        },
        {
            "name": "ForecastAgent",
            "import_path": "src.agents.ForecastAgent.agent",
            "class_name": "ForecastAgent",
            "test_query": "Generate a 3-day forecast", 
            "expected_pattern": "Tool Calling"
        },
        {
            "name": "OrderAgent",
            "import_path": "src.agents.OrderAgent.agent",
            "class_name": "OrderAgent",
            "test_query": "Check order status",
            "expected_pattern": "ReAct"
        }
    ]
    
    results = {
        "total_agents": len(agents_config),
        "migrated_agents": 0,
        "working_agents": 0,
        "details": []
    }
    
    print(f"\n🔍 Testing {len(agents_config)} agents for Core Framework v2...")
    
    for agent_config in agents_config:
        agent_name = agent_config["name"]
        print(f"\n{'='*50}")
        print(f"🤖 Testing {agent_name}")
        print(f"{'='*50}")
        
        try:
            # Dynamic import
            module = __import__(agent_config["import_path"], fromlist=[agent_config["class_name"]])
            agent_class = getattr(module, agent_config["class_name"])
            
            # Create agent instance
            agent = agent_class()
            print(f"✅ {agent_name} imported and instantiated successfully")
            
            # Get status
            status = agent.get_status()
            framework_version = status.get("framework_version", "unknown")
            agent_status = status.get("status", "unknown")
            tools_count = status.get("tools_count", 0)
            
            print(f"📊 Status: {agent_status}")
            print(f"🔧 Framework Version: {framework_version}")
            print(f"🛠️ Tools Count: {tools_count}")
            
            # Check if using Core Framework v2
            is_migrated = framework_version == "core_v2"
            if is_migrated:
                print(f"✅ {agent_name} using Core Framework v2")
                results["migrated_agents"] += 1
            else:
                print(f"❌ {agent_name} NOT using Core Framework v2: {framework_version}")
            
            # Test basic functionality
            print(f"🧪 Testing functionality with query: {agent_config['test_query']}")
            start_time = time.time()
            response = agent.process_query(agent_config["test_query"])
            duration = time.time() - start_time
            
            print(f"⚡ Response time: {duration:.2f}s")
            print(f"🔄 Response length: {len(response)} characters")
            
            # Basic response validation
            is_working = response and len(response.strip()) > 0 and not "error" in response.lower()
            if is_working:
                print(f"✅ {agent_name} functionality test passed")
                results["working_agents"] += 1
            else:
                print(f"⚠️ {agent_name} functionality test questionable")
            
            # Store results
            results["details"].append({
                "name": agent_name,
                "migrated": is_migrated,
                "working": is_working,
                "framework_version": framework_version,
                "response_time": duration,
                "tools_count": tools_count,
                "pattern": agent_config["expected_pattern"]
            })
            
        except Exception as e:
            print(f"❌ {agent_name} failed: {e}")
            results["details"].append({
                "name": agent_name,
                "migrated": False,
                "working": False,
                "error": str(e),
                "pattern": agent_config["expected_pattern"]
            })
    
    # Generate final report
    print(f"\n{'='*70}")
    print("📊 FINAL MIGRATION REPORT")
    print(f"{'='*70}")
    
    migration_rate = (results["migrated_agents"] / results["total_agents"]) * 100
    functionality_rate = (results["working_agents"] / results["total_agents"]) * 100
    
    print(f"🎯 Total Agents: {results['total_agents']}")
    print(f"✅ Migrated to Core Framework v2: {results['migrated_agents']}/{results['total_agents']} ({migration_rate:.1f}%)")
    print(f"🧪 Working Functionality: {results['working_agents']}/{results['total_agents']} ({functionality_rate:.1f}%)")
    
    print(f"\n📋 Agent Details:")
    for detail in results["details"]:
        status_icon = "✅" if detail["migrated"] and detail.get("working", False) else "❌"
        pattern = detail.get("pattern", "Unknown")
        tools = detail.get("tools_count", 0)
        print(f"  {status_icon} {detail['name']}: {pattern} pattern, {tools} tools")
    
    # Success assessment
    if migration_rate == 100 and functionality_rate >= 85:
        print(f"\n🎉 MIGRATION COMPLETELY SUCCESSFUL!")
        print("✅ All agents migrated to Core Framework v2")
        print("✅ All agents are functioning correctly")
        print("🚀 Multi-agent system is ready for production!")
    elif migration_rate >= 80:
        print(f"\n🎊 MIGRATION MOSTLY SUCCESSFUL!")
        print(f"Most agents are using Core Framework v2")
        print(f"Minor issues may need attention")
    else:
        print(f"\n⚠️ MIGRATION NEEDS ATTENTION")
        print(f"Several agents still need migration work")
    
    print(f"\n🕐 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return migration_rate == 100

if __name__ == "__main__":
    success = test_all_agents()
    sys.exit(0 if success else 1)
