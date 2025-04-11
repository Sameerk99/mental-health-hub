# mental-health-hub
A Flask web application for mental health assessments and mood tracking



A web application for mental health assessments and mood tracking, built with Flask and SQLite.

## Features

- User authentication and profile management
- Standardized mental health assessments (PHQ-9 and GAD-7)
- Personalized recommendations based on assessment results
- Daily mood tracking with visualization
- AI-powered support chat using OpenAI's GPT-3.5

## Built With

- Flask - Web framework
- SQLite - Database
- Chart.js - Data visualization
- Bootstrap - Frontend styling
- OpenAI API - Chat support feature


Installation Instructions:
## Installation

1. Clone the repository
git clone https://github.com/Sameerk99/mental-health-hub.git
cd mental-health-hub

2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies
pip install -r requirements.txt

4. Create a .env file with your OpenAI API key
OPENAI_API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here

5. Initialize the database
python init_db.py

6. Run the application
python app.py

7. Visit http://127.0.0.1:5000 in your browser
   
## Usage

1. Create an account or log in
2. Complete a PHQ-9 or GAD-7 assessment
3. Review your personalized recommendations
4. Track your daily mood using the mood tracker
5. Use the AI chat feature for additional support

## Note

This application is for educational purposes only and is not a substitute for professional mental health care. If you're experiencing a mental health crisis, please contact emergency services or a mental health professional.

flask==2.2.3
werkzeug==2.2.3
openai==0.27.0
flask-limiter==3.3.0
python-dotenv==1.0.0
