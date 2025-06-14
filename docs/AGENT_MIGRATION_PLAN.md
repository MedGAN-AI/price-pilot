# 🚀 Agent Migration to Core Framework - Implementation Plan

## 📊 Migration Priority & Timeline

### **PHASE 2A: High Priority Agents (Week 1)**

#### **1. ChatAgent Migration** 🎯
**Current Issues:**
- Uses custom structured chat implementation
- Partial core usage
- Complex delegation system needs standardization

**Migration Steps:**
```python
# Before: Custom implementation in ChatAgent/agent.py
agent = create_structured_chat_agent(llm, tools, prompt)

# After: Using core framework
from src.core import build_agent, AgentType
agent_graph = build_agent(
    llm=llm,
    tools=tools, 
    prompt_template=prompt,
    agent_type=AgentType.STRUCTURED_CHAT
)
```

**Files to Update:**
- `src/agents/ChatAgent/agent.py` - Main migration
- `src/agents/ChatAgent/config.yaml` - Standardize format
- Update delegation tools to use core error handling

---

#### **2. LogisticsAgent Migration** 🚚
**Current Issues:**
- Complex custom state management (shipment_context, user_preferences, active_operations)
- Custom LLM initialization with safety settings
- Complex assistant function

**Migration Benefits:**
- Standardized error handling for logistics operations
- Better configuration management
- Consistent state handling

**Special Considerations:**
- Preserve complex context management
- Maintain safety settings for production
- Keep tracking number extraction logic

---

### **PHASE 2B: Medium Priority Agents (Week 2)**

#### **3. InventoryAgent Migration** 📦
**Current State:** Custom ReAct implementation
**Migration Complexity:** MEDIUM
**Key Changes:**
- Replace custom AgentState with enhanced core version
- Use core LLM creation
- Standardize error messages

#### **4. RecommendAgent Migration** 🎯
**Current State:** Custom ReAct implementation  
**Migration Complexity:** MEDIUM
**Key Changes:**
- Maintain ReAct pattern but use core framework
- Standardize configuration
- Improve error handling

#### **5. ForecastAgent Migration** 📈
**Current State:** Tool calling agent implementation
**Migration Complexity:** MEDIUM  
**Key Changes:**
- Use `AgentType.TOOL_CALLING` in core framework
- Standardize ChatPromptTemplate usage
- Maintain specialized forecasting logic

---

## 🛠️ **Implementation Strategy**

### **Step 1: Create Migration Utilities**
Create helper functions to make migration smooth:

```python
def migrate_agent_config(old_config_path: str, new_config_path: str):
    """Convert old config format to standardized format"""
    
def validate_migrated_agent(agent_path: str):
    """Verify migrated agent follows core patterns"""
    
def generate_migration_report(agent_name: str):
    """Generate before/after comparison"""
```

### **Step 2: Gradual Migration Process**
1. **Backup Original**: Copy current agent to `_backup` folder
2. **Config Migration**: Update `config.yaml` to standard format
3. **Code Migration**: Update `agent.py` imports and structure
4. **Testing**: Verify functionality with existing tests
5. **Integration**: Test with orchestrator
6. **Documentation**: Update agent documentation

### **Step 3: Quality Assurance**
- All agents must pass the same test suite
- Consistent error handling across agents
- Unified configuration format
- Performance benchmarking

---

## 📋 **Per-Agent Migration Checklists**

### **ChatAgent Migration Checklist:**
- [ ] Update imports to use core framework
- [ ] Convert structured chat to use `build_agent()`
- [ ] Standardize configuration format
- [ ] Update delegation tools error handling
- [ ] Test conversation flows
- [ ] Verify orchestrator integration

### **LogisticsAgent Migration Checklist:**
- [ ] Preserve custom state fields (shipment_context, etc.)
- [ ] Maintain safety settings and configurations
- [ ] Use core error handling for logistics operations
- [ ] Keep tracking number extraction logic
- [ ] Test carrier integrations
- [ ] Verify webhook handling

### **InventoryAgent Migration Checklist:**
- [ ] Replace custom state with enhanced core state
- [ ] Use `create_llm_from_config()`
- [ ] Update prompt loading
- [ ] Standardize stock checking responses
- [ ] Test SKU validation
- [ ] Verify Supabase integration

### **RecommendAgent Migration Checklist:**
- [ ] Maintain ReAct pattern with core framework
- [ ] Standardize recommendation responses
- [ ] Update product search logic
- [ ] Test recommendation quality
- [ ] Verify connector integrations

### **ForecastAgent Migration Checklist:**
- [ ] Use `AgentType.TOOL_CALLING`
- [ ] Maintain ChatPromptTemplate usage
- [ ] Preserve ARIMA forecasting logic
- [ ] Test forecast accuracy
- [ ] Verify MLflow integration

---

## 🎯 **Expected Benefits Post-Migration**

### **Consistency Benefits:**
✅ All agents follow same patterns
✅ Standardized error handling
✅ Unified configuration format
✅ Consistent state management

### **Maintainability Benefits:**
✅ Single source of truth for agent logic
✅ Easier to add new agents
✅ Consistent debugging experience
✅ Better code reusability

### **Quality Benefits:**
✅ Standardized error messages
✅ Better user experience
✅ Easier testing and validation
✅ Improved monitoring and logging

### **Development Benefits:**
✅ Faster agent development
✅ Reduced code duplication
✅ Better documentation
✅ Easier onboarding for new developers

---

## 🚨 **Risk Mitigation**

### **Backup Strategy:**
- Create `_backup` folders for each agent before migration
- Maintain git branches for rollback capability
- Document any breaking changes

### **Testing Strategy:**
- Comprehensive unit tests for each migrated agent
- Integration tests with orchestrator
- Performance regression testing
- User acceptance testing

### **Rollback Plan:**
- Keep original agent implementations as backup
- Gradual rollout with feature flags
- Monitor error rates and performance
- Quick rollback procedures documented

---

This migration will transform your multi-agent system into a truly professional, maintainable, and scalable architecture! 🚀
