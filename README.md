# SailorShift – Smart Workforce Scheduler

<p align="center">
  <img src="https://github.com/user-attachments/assets/561cc48d-556a-4366-95c4-ab61ee0b11e1" alt="SailorShift Banner" width="400">
</p>


**SailorShift** is an AI-powered workforce scheduling solution designed for small and medium-sized enterprises (SMEs). It automates shift scheduling, leave and swap requests, and employee preference handling through intelligent algorithms and a conversational AI chatbot. The system features two integrated web portals — one for employers and another for employees — making workforce management intuitive, efficient, and scalable.

---

## Project Overview

SailorShift streamlines administrative tasks such as:

- Employee onboarding and shift scheduling
- Leave and shift swap approvals
- Real-time chatbot support
- Weekly preference-based optimization

It is built with a focus on automation, usability, and real-time interactivity to reduce managerial overhead and enhance employee satisfaction.

---

## Data Architecture

SailorShift uses Supabase (PostgreSQL) as its cloud database with the following core tables:

- `employees` – stores roles and skill ratings  
- `preferences` – employee workday preferences  
- `limits` – min/max hour constraints  
- `new_schedule` & `changed_schedule` – base and live schedules  
- `candidate_credentials` – login info and contact details

---

## Key Features

### Automated Scheduling
- Optimizes shifts based on preferences, role limits, and skill ratings
- Balances workloads while respecting contractual hour limits

### Leave & Swap Management
- Employees can request leaves/swaps via UI or chatbot
- Auto-identifies suitable replacements and updates schedules live

### AI Chatbot Integration
- Built using Gemini 2.0 Flash with RAG (Retrieval-Augmented Generation)
- Handles natural language queries and schedule actions
- Supports both text and voice input

---

## System Components

### Employer Portal
- Add employees and assign roles/skills
- Upload RAG documents for chatbot
- Set hour limits, send credentials, manage pay details

### Employee Portal
- View personalized schedule
- Request leaves or shift swaps
- Set weekly preferences
- Chat with AI assistant

---

## Core Algorithms

- **Leave Request Algorithm**: Finds highest-skill available replacement
- **Swap Request Algorithm**: Replaces shift with suitable low-skill peer
- **Schedule Optimizer**: Respects min/max hours and preferences to auto-generate balanced schedules

---

## Insights

- Improved admin efficiency and reduced manual errors
- Highly useful for SMEs with frequent scheduling changes
- Increased transparency and autonomy for employees

---

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript, React.js, Node.js  
- **Backend**: Python (Flask), PostgreSQL (Supabase)  
- **AI**: Google Gemini 2.0 Flash with RAG  
- **Cloud**: Supabase hosting and API integration

---

## Conclusion

SailorShift delivers an end-to-end solution for workforce scheduling by combining automation, user-friendly interfaces, and AI-powered support. While originally aimed at enterprise scalability, it proved highly effective for SMEs through real-world testing. Future upgrades will include mobile apps, analytics dashboards, and payroll integration.

---

## Live Demo

[ShiftSync Live Website](https://sailor-shift.lovable.app/)

