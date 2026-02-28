# 🩸 LifeLink AI – Intelligent Blood Emergency Response System

Innobot 2.0 | Healthcare Domain | IEEE RAS Kerala Chapter

---

##  Problem Statement

Hospitals frequently face critical blood shortages due to inefficient manual tracking systems, delayed coordination between donors and hospitals, and the absence of predictive mechanisms.

In emergency situations such as accidents, surgeries, and trauma cases, identifying compatible donors and available blood units quickly is crucial. Traditional systems are reactive and depend heavily on manual calls and isolated record-keeping.

There is a need for a centralized, intelligent system that can:
- Track real-time blood inventory
- Classify emergency urgency automatically
- Allocate blood units efficiently
- Activate compatible donors instantly
- Predict shortages before they occur

---

## Solution Description

LifeLink AI is a web-based intelligent blood emergency management system that integrates database management with AI-powered decision support.
The system provides:
- Real-time blood inventory tracking
- Donor registration with eligibility calculation
- AI-based emergency severity classification (Critical / Urgent / Routine)
- Automatic blood allocation if stock is available
- Compatible donor matching during critical cases
- Automated donor activation alerts
- Shortage prediction based on recent request trends
- Live dashboard with emergency alerts and analytics

By combining automation with AI-driven insights, LifeLink AI reduces response time, minimizes human intervention, and improves emergency coordination efficiency.

---

## Technology Stack

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Flask Framework

### Database
- SQLite (Relational Database)
- Normalized schema with constraints

### AI Integration
- Google Gemini API
- Used for emergency classification and shortage prediction

### Architecture
Three-Tier Architecture:
Frontend → Flask Backend API → SQLite Database → AI Engine

---

## Setup Instructions

1. Clone the repository:

bash
git clone https://github.com/Abyyy-s/hackathon-team--Imposters-.git
cd hackathon-team--Imposters-

2. Install required dependencies:
   
bash
pip install -r requirements.txt

3. Create a .env file in the root directory and add your Gemini API key:

GEMINI_API_KEY=your_api_key_here

4. Run the application:

bash
python app.py

5. Open your browser and navigate to:

http://localhost:5000

---

##  Team Members

- Parvathi Rajan AV 
- Abinsha Shukoor
- Aby S Biju 
- Hena Mariam Abraham

  Team Imposters  
  Innobot 2.0 – IEEE RAS Kerala Chapter
