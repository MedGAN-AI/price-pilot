#!/usr/bin/env python3
"""
Simple Memory Debug Test
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.graphs.orchestrator import orchestrator, initialize_state, get_global_memory, reset_global_memory
from langchain_core.messages import HumanMessage

def test_memory_step_by_step():
    """Test memory step by step to debug issues"""
    print("🔍 Step-by-step Memory Debug Test")
    print("=" * 50)
    
    # Reset memory
    reset_global_memory()
    global_memory = get_global_memory()
    
    # Test 1: Simple introduction
    print("\n1. Testing name storage...")
    state = initialize_state()
    state["messages"] = [HumanMessage(content="Hi, I'm Mohammed")]
    
    result = orchestrator.invoke(state)
    print(f"   Intent: {result.get('intent')}")
    print(f"   Confidence: {result.get('confidence')}")
    print(f"   Response: {result.get('messages', [])[-1].content if result.get('messages') else 'No response'}")
    
    # Check memory
    memory_state = global_memory.get_user_context_summary()
    print(f"   Global Memory: {memory_state}")
    
    # Test 2: Ask for name
    print("\n2. Testing name retrieval...")
    state2 = initialize_state()
    state2["messages"] = [HumanMessage(content="What is my name?")]
    
    result2 = orchestrator.invoke(state2)
    print(f"   Intent: {result2.get('intent')}")
    print(f"   Confidence: {result2.get('confidence')}")
    print(f"   Response: {result2.get('messages', [])[-1].content if result2.get('messages') else 'No response'}")
    
    # Final memory check
    print(f"\n3. Final Memory State:")
    print(f"   Interactions: {len(global_memory.conversation_history)}")
    print(f"   User Context: {global_memory.user_context}")

if __name__ == "__main__":
    test_memory_step_by_step()
