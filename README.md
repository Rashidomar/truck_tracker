# 📦 ELD Hours of Service (HOS) Log Generator

A full-stack app (Django + React) that generates **FMCSA Hours of Service-compliant electronic logs (ELDs)** for property-carrying drivers.  

- Backend: **Django REST Framework**  
- Frontend: **React (TypeScript + Tailwind)**  
- Features:  
  - Generate driver logs based on trip inputs (miles, legs, cycle hours)  
  - Enforce key FMCSA HOS rules (11-hour driving, 14-hour shift window, 30-min break, 70-hour/8-day cycle, fueling stops, pickup/dropoff time)  
  - Output JSON logs & trip summary  
  - Visualize logs in a **24-hour ELD grid**  
  - Map route using free APIs (Leaflet/OpenStreetMap or Google Directions)  

---

## 🚀 Quick Start

### 1. Clone Repo
```bash
git clone clone https://github.com/Rashidomar/hos.git
cd hos
