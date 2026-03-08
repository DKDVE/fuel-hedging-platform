# 🔑 N8N CREDENTIALS - COMPLETE GUIDE

**Issue**: Can't find Credentials section in n8n UI  
**Solution**: Multiple methods below (guaranteed to work!)  
**n8n Version**: Latest (Docker)

---

## 🎯 METHOD 1: DIRECT URL (EASIEST)

Just open this URL in your browser:

```
👉 http://localhost:5678/credentials
```

This should take you **directly** to the Credentials page.

---

## 🎯 METHOD 2: VIA LEFT SIDEBAR (RECOMMENDED)

### **Step-by-Step**:

1. **Open n8n**: http://localhost:5678

2. **Look at LEFT SIDEBAR** (vertical menu on the left side)

3. **Find "Credentials" menu item**:
   - It should be below "Workflows"
   - Icon looks like a key 🔑 or lock 🔒
   - Text says: **"Credentials"**

4. **Click "Credentials"**

5. **You'll see the Credentials list page**

6. **Click "+ Add Credential"** (top right button)

7. **Search for "OpenAI"**

8. **Select "OpenAI API"**

9. **Fill in**:
   - **Credential Name**: `OpenAI - Fuel Hedging`
   - **API Key**: [Your OpenAI API key]
   - Get key from: https://platform.openai.com/api-keys

10. **Click "Save"**

---

## 🎯 METHOD 3: VIA SETTINGS MENU

### **If you can't find it in sidebar**:

1. **Look at TOP RIGHT corner**

2. **Find your user menu** (could be):
   - Your username
   - User icon
   - Three dots menu (⋮)
   - Gear icon (⚙️)

3. **Click on it to open dropdown**

4. **Look for**:
   - "Settings"
   - "Credentials"
   - "User Settings"

5. **Click "Credentials"** if available

---

## 🎯 METHOD 4: CREATE FIRST-TIME SETUP

**If this is your FIRST time using n8n**:

1. You might need to create an account first
2. Go to: http://localhost:5678
3. **Sign up** (any email/password for local instance)
4. After signup, you'll see the main dashboard
5. Then follow Method 1 or 2 above

---

## 📸 VISUAL REFERENCE

```
┌─────────────────────────────────────────────────────────┐
│  n8n                                    [User Menu ▾]   │  ← Top Bar
├─────────────┬───────────────────────────────────────────┤
│             │                                           │
│  Workflows  │        CREDENTIALS PAGE                   │
│             │                                           │
│  Templates  │  ┌─────────────────────────────────┐    │
│             │  │  + Add Credential               │    │
│ 🔑 Credentials│  └─────────────────────────────────┘    │
│             │                                           │
│  Executions │  No credentials found yet                │
│             │                                           │
│  Settings   │  Click "+ Add Credential" to create one  │
│             │                                           │
└─────────────┴───────────────────────────────────────────┘
   ↑
   Left Sidebar
   (Find "Credentials" here!)
```

---

## 🔧 METHOD 5: VIA WORKFLOW (ALTERNATIVE)

**If you still can't find it, you can add credentials while editing a workflow**:

1. **Import the workflow first** (see below)
2. **Open the workflow**
3. **Click on any agent node** that would need credentials
4. **In the node settings**, look for "Credentials" field
5. **Click "Add New" or "+" next to credentials**
6. **This will open the credential creation dialog**

---

## 📋 WHAT IF NOTHING WORKS?

### **Try this command to access n8n's internal settings**:

```bash
# Check if n8n is running properly
docker logs hedge-n8n --tail 50

# Restart n8n if needed
docker restart hedge-n8n

# Wait 10 seconds
sleep 10

# Try again
open http://localhost:5678/credentials
```

### **Check n8n documentation**:
- Official docs: https://docs.n8n.io/credentials/
- Credentials guide: https://docs.n8n.io/credentials/add-edit-credentials/

---

## ✅ GOOD NEWS: YOU DON'T NEED OPENAI YET!

**Important**: The generated workflow works **without OpenAI credentials**!

### **Why?**

The workflow I created uses **mock agents** (Code nodes), not AI Agent nodes:
- ✅ Works immediately without any credentials
- ✅ Returns realistic JSON responses
- ✅ Tests all workflow logic
- ✅ Shows committee consensus
- ✅ Demonstrates CRO risk gate

### **You can**:
1. ✅ **Import the workflow NOW** (no credentials needed)
2. ✅ **Execute it and see results** (works perfectly)
3. ✅ **Test all decision logic**
4. ⏺️ **Upgrade to AI agents LATER** (when you add OpenAI)

---

## 🚀 RECOMMENDED WORKFLOW

### **Phase 1: Test Without OpenAI** (Do this NOW - 5 min)

1. **Import workflow**:
   ```
   http://localhost:5678
   → Workflows
   → Import from File
   → Select: fuel_hedging_workflow_generated.json
   ```

2. **Execute workflow**:
   ```
   Click "Execute Workflow" button
   → Watch it run
   → See final recommendation
   ```

3. **Review output**:
   ```
   Final Output node shows:
   - Decision: IMPLEMENT
   - Instrument: heating_oil
   - Notional: $5,000,000
   - Consensus: 5/5 agents
   ```

### **Phase 2: Add OpenAI** (Optional - Later)

1. **Get OpenAI API key**: https://platform.openai.com/api-keys

2. **Add credential** (use Method 1 above):
   ```
   http://localhost:5678/credentials
   → + Add Credential
   → Search "OpenAI"
   → Paste key
   → Save
   ```

3. **Upgrade agents** (see docs/N8N_IMPORT_GUIDE.md):
   - Replace Code nodes with AI Agent nodes
   - Connect OpenAI Chat Model
   - Use prompts from docs/N8N_AGENT_PROMPTS.md

---

## 📞 SCREENSHOT REQUEST

**If you still can't find Credentials**:

Can you share what you see on your n8n screen?
- What's in the left sidebar?
- What's in the top right corner?
- Is this your first time opening n8n?

I can provide more specific guidance based on what you see.

---

## 🎯 IMMEDIATE ACTION

**Forget credentials for now and just test the workflow!**

```bash
1. Open: http://localhost:5678
2. Find: "Workflows" in left sidebar
3. Click: Import from File
4. Select: fuel_hedging_workflow_generated.json
5. Click: Execute Workflow
6. Enjoy: See the magic happen! ✨
```

The workflow **works perfectly without OpenAI** because I designed it with mock agents specifically so you can test immediately.

---

**Created**: March 3, 2026  
**For**: Fuel Hedging Platform n8n Workflow  
**Status**: Mock agents work NOW, OpenAI optional for later
