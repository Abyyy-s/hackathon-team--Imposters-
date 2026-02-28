# 🩸 LifeLink AI – Intelligent Blood Emergency Response System

Innobot 2.0 | Healthcare Domain | IEEE RAS Kerala Chapter Hackathon 2026

---

## 📌 Problem Statement

Blood shortages and delayed coordination between hospitals and donors remain a major challenge in emergency healthcare systems.  

Hospitals often rely on manual communication, isolated databases, and reactive stock management. During critical emergencies such as accidents or surgeries, identifying available blood units and eligible donors can take valuable time.

There is a need for a centralized, intelligent system that can:
- Track real-time blood inventory
- Classify emergency urgency
- Automate allocation decisions
- Predict shortages before they occur

---

## 💡 Solution Description

LifeLink AI is a web-based Blood Emergency Management System that integrates structured database management with AI-powered decision support.

The system:

- Maintains donor records with eligibility tracking
- Tracks real-time blood inventory across all blood types
- Allows hospitals to submit emergency blood requests
- Uses AI to classify emergency severity (Critical / Urgent / Routine)
- Automatically allocates blood units if available
- Predicts potential shortages using recent request trends
- Generates real-time alerts for low stock and emergency cases
- Provides an interactive dashboard for monitoring and coordination

By combining automation with AI-driven insights, LifeLink AI reduces response time, minimizes human error, and improves emergency coordination efficiency.

---

## 🛠 Technology Stack

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Flask Framework

### Database
- SQLite (Relational Database)
- Normalized structure with proper constraints

### AI Integration
- Google Gemini API
- Used for emergency classification and shortage prediction

### Architecture
Three-Tier Architecture:
Frontend → Flask Backend API → SQLite Database → AI Engine

---

## ⚙️ Setup Instructions

1. Clone the repository:

```bash
git clone https://github.com/Abyyy-s/hackathon-team--Imposters-.git
cd hackathon-team--Imposters-
```

2. Install required dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory and add your Gemini API key:

```
GEMINI_API_KEY=your_api_key_here
```

4. Run the application:

```bash
python app.py
```

5. Open your browser and navigate to:

```
http://localhost:5000
```

---

## 👥 Team Members

- Parvathi Rajan AV 
- Abinsha Shukoor
- Aby S Biju 
- Hena Mariam Abraham

  Team Imposters  
  Innobot 2.0 – IEEE RAS Kerala Chapter
