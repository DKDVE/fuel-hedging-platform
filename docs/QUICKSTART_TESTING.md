# 🎯 QUICK START - Testing Your Fuel Hedging Platform

## ✅ STATUS: BOTH SERVERS RUNNING!

```
✅ Frontend:  http://localhost:5173
✅ Backend:   http://localhost:8000
```

---

## 🚀 START TESTING NOW

### **Step 1: Open Frontend**
Open your browser and go to:
```
http://localhost:5173
```

### **Step 2: Login**
Use ANY credentials (mock backend accepts all):
```
Email: admin@airline.com
Password: password
```

### **Step 3: Navigate All 7 Pages**

1. **Dashboard** (http://localhost:5173/) - KPIs, live prices, forecast, agents
2. **Recommendations** (http://localhost:5173/recommendations) - Approval workflow
3. **Analytics** (http://localhost:5173/analytics) - Hypotheses, VaR, MAPE charts
4. **Positions** (http://localhost:5173/positions) - Hedge positions table
5. **Audit Log** (http://localhost:5173/audit) - Approval history & IFRS 9
6. **Settings** (http://localhost:5173/settings) - Constraints editor (Admin only)
7. **Sidebar Navigation** - Test all links

---

## 🎨 WHAT YOU'LL SEE

### **Dark Financial Dashboard Theme**
- Deep navy/slate backgrounds
- Glowing metric cards
- Professional Bloomberg-style UI
- Subtle animations
- Institutional-grade typography

### **Real-Time Features**
- Live price ticker (updates automatically)
- SLA countdown timer (ticks every second)
- Connection status indicators

### **Interactive Elements**
- Sortable tables (click headers)
- Expandable accordions
- Modal confirmations
- Chart tooltips on hover

---

## 📊 ALL PAGES AT A GLANCE

| Page | URL | Key Features |
|------|-----|--------------|
| Dashboard | / | 4 KPI cards, live ticker, forecast chart, agent grid |
| Recommendations | /recommendations | Approval workflow, SLA timer, donut chart, timeline |
| Analytics | /analytics | 4 hypothesis cards, VaR chart, MAPE chart |
| Positions | /positions | Sortable table, collateral meter |
| Audit Log | /audit | Tabbed interface, date filters, 2 tables |
| Settings | /settings | Constraint editor, API health panel (Admin only) |

---

## 🔧 IF YOU NEED TO RESTART

### **Restart Frontend**
```bash
cd /mnt/e/fuel_hedging_proj/frontend
npm run dev
```
Then open: http://localhost:5173

### **Restart Backend**
```bash
cd /mnt/e/fuel_hedging_proj
python_engine/venv/bin/python mock_backend.py
```
Then test: http://localhost:8000/api/v1/health

---

## 🐛 TROUBLESHOOTING

### **Port Already in Use**
```bash
# Kill port 8000 (backend)
lsof -i :8000 | grep -v COMMAND | awk '{print $2}' | xargs kill -9

# Kill port 5173 (frontend)
lsof -i :5173 | grep -v COMMAND | awk '{print $2}' | xargs kill -9
```

### **Check What's Running**
```bash
ps aux | grep -E 'mock_backend|vite'
```

---

## 📋 TESTING CHECKLIST

### **Basic Functionality**
- [ ] Login page loads
- [ ] Can login with any credentials
- [ ] Dashboard shows all 4 sections
- [ ] Sidebar navigation works
- [ ] All 7 pages accessible
- [ ] No console errors

### **Visual Design**
- [ ] Dark theme throughout
- [ ] Cards have hover effects
- [ ] Charts render correctly
- [ ] Tables formatted properly
- [ ] Typography clear and readable

### **Interactive Features**
- [ ] Tables can be sorted
- [ ] Accordions expand/collapse
- [ ] Modals open on button clicks
- [ ] Timers count down
- [ ] Charts show tooltips on hover

### **Responsive Design**
- [ ] Sidebar collapses on mobile
- [ ] Grids stack vertically on small screens
- [ ] Tables scroll horizontally if needed

---

## 🎉 YOU'RE READY!

**Everything is set up and running.**  
**Just open http://localhost:5173 in your browser!**

For detailed testing instructions, see: `TESTING_GUIDE.md`

---

**Current Status**: ✅ **READY FOR TESTING**  
**Date**: March 2, 2026  
**Servers**: Both frontend and backend running successfully!
