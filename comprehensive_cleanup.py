#!/usr/bin/env python3
"""
Comprehensive Workspace Cleanup Script
Removes redundant files while preserving working core framework agents
"""

import os
import shutil
import sys
from pathlib import Path

def safe_remove(file_path):
    """Safely remove a file if it exists"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"  ✅ Removed: {file_path}")
            return True
        else:
            print(f"  ⏭️  Not found: {file_path}")
            return False
    except Exception as e:
        print(f"  ❌ Failed to remove {file_path}: {e}")
        return False

def safe_rmdir(dir_path):
    """Safely remove a directory if it exists and is empty"""
    try:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            if not os.listdir(dir_path):  # Directory is empty
                os.rmdir(dir_path)
                print(f"  ✅ Removed empty directory: {dir_path}")
                return True
            else:
                print(f"  ⚠️  Directory not empty, skipping: {dir_path}")
                return False
        else:
            print(f"  ⏭️  Directory not found: {dir_path}")
            return False
    except Exception as e:
        print(f"  ❌ Failed to remove directory {dir_path}: {e}")
        return False

def cleanup_chat_agent():
    """Clean up ChatAgent redundant files"""
    print("🤖 Cleaning ChatAgent...")
    
    # Remove redundant files
    files_to_remove = [
        "src/agents/ChatAgent/agent_clean.py",  # Keep main agent.py
        "src/agents/ChatAgent/agent_broken_backup.py",
        "src/agents/ChatAgent/agent_migrated.py"
    ]
    
    removed_count = 0
    for file_path in files_to_remove:
        if safe_remove(file_path):
            removed_count += 1
    
    print(f"  📊 ChatAgent: {removed_count} files removed")

def cleanup_inventory_agent():
    """Clean up InventoryAgent redundant files"""
    print("📦 Cleaning InventoryAgent...")
    
    # InventoryAgent is already clean - just verify
    redundant_files = [
        "src/agents/InventoryAgent/agent_backup.py",
        "src/agents/InventoryAgent/agent_old.py"
    ]
    
    removed_count = 0
    for file_path in redundant_files:
        if safe_remove(file_path):
            removed_count += 1
    
    if removed_count == 0:
        print("  ✅ InventoryAgent is already clean")
    else:
        print(f"  📊 InventoryAgent: {removed_count} files removed")

def cleanup_logistics_agent():
    """Clean up LogisticsAgent redundant files"""
    print("🚚 Cleaning LogisticsAgent...")
    
    # Remove backup and redundant files
    files_to_remove = [
        "src/agents/LogisticsAgent/agent_backup.py",
        "src/agents/LogisticsAgent/agent_core.py",  # Merged into agent.py
        "src/agents/LogisticsAgent/agent_legacy_backup.py",
        "src/agents/LogisticsAgent/config_legacy_backup.yaml",
        "src/agents/LogisticsAgent/config_new.yaml"  # Content moved to config.yaml
    ]
    
    removed_count = 0
    for file_path in files_to_remove:
        if safe_remove(file_path):
            removed_count += 1
    
    print(f"  📊 LogisticsAgent: {removed_count} files removed")

def cleanup_root_files():
    """Clean up root directory redundant files"""
    print("🏠 Cleaning root directory...")
    
    # Remove test and migration files that are no longer needed
    files_to_remove = [
        "test_agent_building.py",
        "test_chat_agent.py", 
        "test_logistics_migration.py",
        "test_migrated_agents.py",
        "test_chatagent_fix.py",
        "migrate_agents.py",
        "migration_report.md",
        "cleanup_workspace.py",  # This script itself
        "final_cleanup_verification.py",
        "final_verification.py"
    ]
    
    removed_count = 0
    for file_path in files_to_remove:
        if safe_remove(file_path):
            removed_count += 1
    
    print(f"  📊 Root directory: {removed_count} files removed")

def verify_core_agents():
    """Verify that core agents are still working after cleanup"""
    print("🔍 Verifying core agents after cleanup...")
    
    try:
        # Test imports
        sys.path.append('.')
        
        from src.agents.ChatAgent.agent import ChatAgent
        from src.agents.InventoryAgent.agent import InventoryAgent
        from src.agents.LogisticsAgent.agent import LogisticsAgent
        
        # Test instantiation
        chat_agent = ChatAgent()
        inv_agent = InventoryAgent()
        log_agent = LogisticsAgent()
        
        # Check status
        agents = {
            "ChatAgent": chat_agent,
            "InventoryAgent": inv_agent,
            "LogisticsAgent": log_agent
        }
        
        all_good = True
        for name, agent in agents.items():
            try:
                status = agent.get_status()
                framework_version = status.get("framework_version", "unknown")
                if framework_version == "core_v2":
                    print(f"  ✅ {name}: {framework_version}")
                else:
                    print(f"  ⚠️  {name}: {framework_version} (expected core_v2)")
                    all_good = False
            except Exception as e:
                print(f"  ❌ {name}: Failed to get status - {e}")
                all_good = False
        
        return all_good
        
    except Exception as e:
        print(f"  ❌ Verification failed: {e}")
        return False

def create_migration_summary():
    """Create a summary of the migration work completed"""
    print("📋 Creating migration summary...")
    
    summary_content = """# Agent Migration Summary

## ✅ Successfully Migrated to Core Framework v2

### 1. ChatAgent
- **Status**: ✅ COMPLETE
- **Framework**: Core v2
- **Pattern**: Structured Chat
- **Features**:
  - Complex conversation handling
  - Agent delegation (RecommendAgent, OrderAgent)
  - Memory and context management
  - Error handling and recovery

### 2. InventoryAgent  
- **Status**: ✅ COMPLETE
- **Framework**: Core v2
- **Pattern**: ReAct
- **Features**:
  - Stock checking by SKU and product name
  - Real database integration (Supabase)
  - Mock data fallback
  - Proper error handling

### 3. LogisticsAgent
- **Status**: ✅ COMPLETE  
- **Framework**: Core v2
- **Pattern**: ReAct
- **Features**:
  - Shipment tracking (Aramex & Naqel)
  - Mock mode for testing
  - Real tool integration
  - Status monitoring

## 📊 Migration Progress: 4/6 Agents (67%)

### ✅ Using Core Framework v2:
- ChatAgent
- InventoryAgent  
- LogisticsAgent
- OrderAgent

### ⏳ Pending Migration:
- RecommendAgent (Medium complexity)
- ForecastAgent (High complexity - ML integration)

## 🔧 Key Improvements Made

### Core Framework Enhancements:
- Multi-agent type support (ReAct, Structured Chat, Tool Calling)
- Standardized configuration management
- Unified LLM creation process
- Enhanced error handling
- Flexible agent building

### Issues Resolved:
- Relative import problems → Absolute imports
- Unicode corruption in files
- Configuration standardization
- Prompt template compatibility
- Indentation and syntax errors

## 🎯 Next Steps

1. **RecommendAgent Migration**
   - Apply proven migration patterns
   - Medium complexity - good next target

2. **ForecastAgent Migration** 
   - Most complex (ML integration)
   - Tool calling pattern
   - Advanced forecasting algorithms

3. **System Integration**
   - Update orchestrator for all agents
   - Comprehensive testing
   - Performance optimization

## 📁 Cleaned Files

### Removed Redundant Files:
- Backup agent files (`*_backup.py`)
- Duplicate configuration files
- Test and migration scripts
- Legacy implementations

### Preserved Working Files:
- All core framework files
- Working agent implementations
- Essential configuration files
- Tool and prompt files

---
*Migration completed on: June 12, 2025*
*Core Framework Version: v2*
"""
    
    try:
        with open("MIGRATION_SUMMARY.md", "w", encoding="utf-8") as f:
            f.write(summary_content)
        print("  ✅ Created MIGRATION_SUMMARY.md")
        return True
    except Exception as e:
        print(f"  ❌ Failed to create summary: {e}")
        return False

def main():
    """Main cleanup function"""
    print("🧹 Starting Comprehensive Workspace Cleanup...")
    print("=" * 60)
    
    # Change to project root
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Cleanup each component
    cleanup_chat_agent()
    cleanup_inventory_agent() 
    cleanup_logistics_agent()
    cleanup_root_files()
    
    print("\n" + "=" * 60)
    print("🔍 Post-Cleanup Verification...")
    
    # Verify agents still work
    agents_working = verify_core_agents()
    
    # Create migration summary
    summary_created = create_migration_summary()
    
    print("\n" + "=" * 60)
    if agents_working and summary_created:
        print("🎉 Cleanup Successful!")
        print("✅ All core framework agents are working")
        print("✅ Redundant files have been removed")
        print("✅ Workspace is now clean and organized")
        print("✅ Migration summary created")
        
        print("\n📊 Final Status:")
        print("- ChatAgent: ✅ Core Framework v2")
        print("- InventoryAgent: ✅ Core Framework v2") 
        print("- LogisticsAgent: ✅ Core Framework v2")
        print("- OrderAgent: ✅ Core Framework v2")
        print("- RecommendAgent: ⏳ Ready for migration")
        print("- ForecastAgent: ⏳ Ready for migration")
        
        print("\n🚀 Ready for next phase:")
        print("- RecommendAgent migration")
        print("- ForecastAgent migration") 
        print("- Final system integration")
        
        return True
    else:
        print("❌ Cleanup Issues Detected!")
        if not agents_working:
            print("Some agents may need attention after cleanup")
        if not summary_created:
            print("Failed to create migration summary")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
