from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import datetime
import os
from dotenv import load_dotenv
import openai
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


load_dotenv()

PHQ9_QUESTIONS = [
    "Little interest or pleasure in doing things?",
    "Feeling down, depressed, or hopeless?",
    "Trouble falling/staying asleep, or sleeping too much?",
    "Feeling tired or having little energy?",
    "Poor appetite or overeating?",
    "Feeling bad about yourself - worthlessness?",
    "Trouble concentrating on things?",
    "Moving/speaking slowly or being fidgety?",
    "Thoughts of self-harm or suicide?"
]

GAD7_QUESTIONS = [
    "Feeling nervous, anxious, or on edge?",
    "Not being able to stop worrying?",
    "Worrying too much about different things?",
    "Trouble relaxing?",
    "Being so restless it's hard to sit still?",
    "Becoming easily annoyed/irritable?",
    "Feeling afraid of something awful happening?"
]

def get_phq9_recommendation(score):
    if score <= 4:
        return {
            "severity": "Minimal Depression",
            "recommendations": [
                "Daily Practice: Maintain mood journaling with focus on positive experiences",
                "Behavioral Activation: Schedule 1 pleasurable activity daily (e.g., 15-min walk, creative hobby)",
                "Sleep Hygiene: Consistent sleep schedule (7-9 hours), no screens 1 hour before bed",
                "Social Connection: Weekly social activity with friends/family",
                "Monitoring: Retake PHQ-9 in 2 weeks or if symptoms worsen"
            ]
        }
    elif score <= 9:
        return {
            "severity": "Mild Depression",
            "recommendations": [
                "Structured Program: 6-week online CBT program (30 mins/day) focusing on cognitive restructuring",
                "Behavioral Activation: Graded task scheduling starting with small achievable goals",
                "Physical Activity: 150 mins/week moderate exercise (e.g., brisk walking, yoga)",
                "Social Prescription: Join local peer support group meeting weekly",
                "Professional Check-in: Consult GP for baseline health check within 2 weeks"
            ]
        }
    elif score <= 14:
        return {
            "severity": "Moderate Depression",
            "recommendations": [
                "Therapist Referral: Weekly CBT sessions for 8-12 weeks (45 mins/session)",
                "Medication Options: Discuss SSRI antidepressants with psychiatrist",
                "Safety Plan: Create crisis plan including emergency contacts",
                "Workplace Support: Request occupational health assessment",
                "Monitoring: Weekly PHQ-9 tracking with automatic alerts to designated contact"
            ]
        }
    elif score <= 19:
        return {
            "severity": "Moderately Severe Depression",
            "recommendations": [
                "Urgent Care: Same-day mental health team assessment",
                "Combination Therapy: SSRI medication + twice-weekly therapy sessions",
                "Daily Check-ins: Automated safety check system with crisis team",
                "Functional Support: Apply for temporary disability accommodations",
                "Crisis Plan: 24/7 access to crisis hotline and emergency contacts"
            ]
        }
    else:
        return {
            "severity": "Severe Depression",
            "recommendations": [
                "Immediate Care: Emergency psychiatric evaluation within 24 hours",
                "Intensive Treatment: Consider day program or inpatient care",
                "Medication Management: Daily monitoring of antidepressant regimen",
                "Social Support: Activate caregiver support network",
                "Safety Protocol: Remove access to potential self-harm means"
            ]
        }

def get_gad7_recommendation(score):
    if score <= 4:
        return {
            "severity": "Minimal Anxiety",
            "recommendations": [
                "Preventive Practice: Daily 10-min mindfulness breathing exercises",
                "Worry Management: Scheduled 15-min 'worry time' with journaling",
                "Stress Reduction: Progressive muscle relaxation before bed",
                "Lifestyle Balance: Maintain consistent work/leisure ratio",
                "Education: Complete online anxiety psychoeducation course"
            ]
        }
    elif score <= 9:
        return {
            "severity": "Mild Anxiety",
            "recommendations": [
                "CBT Tools: 8-week anxiety workbook with weekly exercises",
                "Exposure Therapy: Gradual hierarchy practice for top 3 fears",
                "Sleep Protocol: Implement strict caffeine curfew (none after 2pm)",
                "Physical Regulation: Daily diaphragmatic breathing (4-7-8 technique)",
                "Social Support: Bi-weekly anxiety management workshop"
            ]
        }
    elif score <= 14:
        return {
            "severity": "Moderate Anxiety",
            "recommendations": [
                "Specialist Referral: Weekly therapy (CBT or ACT) for 12 weeks",
                "Medication Options: Consider short-term anxiolytic use",
                "Workplace Adjustments: Flexible hours during treatment phase",
                "Sensory Regulation: Daily weighted blanket use (20 mins)",
                "Crisis Prevention: Install panic button app with GPS alerts"
            ]
        }
    else:
        return {
            "severity": "Severe Anxiety",
            "recommendations": [
                "Immediate Intervention: Daily therapist check-ins for 1 week",
                "Medication Plan: SSRI/SNRI trial with weekly psychiatrist reviews",
                "Functional Support: Temporary medical leave authorization",
                "Safety Measures: 24/7 crisis text line integration",
                "Intensive Program: 4-week anxiety disorder day treatment"
            ]
        }

app = Flask(__name__)

# Ensure we have a secure key or create a temporary one for development
if os.getenv("SECRET_KEY"):
    app.secret_key = os.getenv("SECRET_KEY")
else:
    # For development only - do not use in production
    app.secret_key = 'dev-temporary-key-for-testing-only'
    print("WARNING: Using temporary development key. Set SECRET_KEY in .env for production.")

app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", 'dev-key'),
    SESSION_COOKIE_SECURE=False,  # True in production
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600  # 1 hour
)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["300 per minute"]
)

@app.after_request
def add_rate_limit_headers(response):
    if limiter.current_limit:
        response.headers["X-RateLimit-Limit"] = str(limiter.current_limit.limit)
        response.headers["X-RateLimit-Remaining"] = str(limiter.current_limit.remaining)
        response.headers["X-RateLimit-Reset"] = str(limiter.current_limit.reset_at)
    return response

DATABASE = 'mental_health.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                assessment_type TEXT CHECK(assessment_type IN ('phq9', 'gad7')) NOT NULL,
                score INTEGER NOT NULL CHECK(score >= 0),
                recommendation TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS mood_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mood INTEGER NOT NULL CHECK(mood BETWEEN 1 AND 5),
                notes TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        error = None

        if not username or not email or not password:
            error = 'All fields are required.'
        
        with get_db_connection() as conn:
            try:
                if error is None:
                    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                    conn.execute('''
                        INSERT INTO users (username, email, password)
                        VALUES (?, ?, ?)
                    ''', (username, email, hashed_password))
                    conn.commit()
                    flash('Account created successfully! Please log in.')
                    return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                error = 'Username or email already exists.'
            finally:
                if error:
                    flash(error)
    return render_template('signup.html')

@app.route('/debug/login-form')
def debug_login_form():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None
        
        with get_db_connection() as conn:
            user = conn.execute(
                'SELECT * FROM users WHERE username = ?', 
                (username,)
            ).fetchone()

        if user is None:
            error = 'Invalid username.'
        elif not check_password_hash(user['password'], password):
            error = 'Invalid password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('home'))
        
        flash(error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('home'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_username = request.form['username']
        new_email = request.form['email']
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        error = None

        with get_db_connection() as conn:
            user = conn.execute(
                'SELECT * FROM users WHERE id = ?', (session['user_id'],)
            ).fetchone()

            if not check_password_hash(user['password'], old_password):
                error = 'Current password is incorrect.'
            
            existing_user = conn.execute(
                'SELECT id FROM users WHERE username = ? AND id != ?',
                (new_username, session['user_id'])
            ).fetchone()
            if existing_user:
                error = 'Username already taken.'

            if not error:
                update_fields = []
                params = []
                
                if new_username != user['username']:
                    update_fields.append('username = ?')
                    params.append(new_username)
                
                if new_email != user['email']:
                    update_fields.append('email = ?')
                    params.append(new_email)
                
                if new_password:
                    update_fields.append('password = ?')
                    params.append(generate_password_hash(new_password))
                
                if update_fields:
                    query = 'UPDATE users SET ' + ', '.join(update_fields) + ' WHERE id = ?'
                    params.append(session['user_id'])
                    conn.execute(query, params)
                    conn.commit()
                    session['username'] = new_username
                    flash('Profile updated successfully!')

            if error:
                flash(error)

    with get_db_connection() as conn:
        user = conn.execute(
            'SELECT * FROM users WHERE id = ?', (session['user_id'],)
        ).fetchone()
    
    return render_template('profile.html', user=user)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/assessment', methods=['GET', 'POST'])
@app.route('/assessment/<assessment_type>', methods=['GET', 'POST'])
@login_required
def assessment(assessment_type=None):
    if not assessment_type:
        return render_template('assessment.html')
    
    try:
        assessment_type = assessment_type.lower()
        
        if request.method == 'POST':
            if assessment_type not in ['phq9', 'gad7']:
                flash('Invalid assessment type')
                return redirect(url_for('assessment'))
            
            questions = PHQ9_QUESTIONS if assessment_type == 'phq9' else GAD7_QUESTIONS
            
            # Validate and calculate score
            total = 0
            for i in range(1, len(questions)+1):
                answer = request.form.get(f'q{i}', '0')
                total += max(0, min(3, int(answer)))  # Ensure score stays 0-3 per question
            
            # Store assessment in session for chat context
            session['last_assessment'] = {
                'type': assessment_type,
                'score': total,
                'timestamp': datetime.datetime.now().isoformat()
            }

            with get_db_connection() as conn:
                recommendation_func = get_phq9_recommendation if assessment_type == 'phq9' else get_gad7_recommendation
                conn.execute('''
                    INSERT INTO assessments (user_id, assessment_type, score, recommendation)
                    VALUES (?, ?, ?, ?)
                ''', (session['user_id'], assessment_type, total, str(recommendation_func(total))))
                conn.commit()

            return redirect(url_for('assessment_result', type=assessment_type, score=total))

        if assessment_type not in ['phq9', 'gad7']:
            flash('Invalid assessment type')
            return redirect(url_for('assessment'))
            
        questions = PHQ9_QUESTIONS if assessment_type == 'phq9' else GAD7_QUESTIONS
        return render_template('assessment.html',
                            assessment_type=assessment_type,
                            questions=enumerate(questions, 1))

    except Exception as e:
        flash(f'Error processing assessment: {str(e)}')
        return redirect(url_for('assessment'))

@app.route('/assessment/result')
@login_required
def assessment_result():
    try:
        assessment_type = request.args.get('type', '').lower()
        score = int(request.args.get('score', 0))
        
        # Validate score ranges
        max_score = 27 if assessment_type == 'phq9' else 21
        score = max(0, min(score, max_score))
        
        if assessment_type not in ['phq9', 'gad7']:
            flash('Invalid assessment type')
            return redirect(url_for('home'))
        
        recommendation_data = (get_phq9_recommendation(score) 
                            if assessment_type == 'phq9' 
                            else get_gad7_recommendation(score))
        
        # Store in session for chat context
        session['current_recommendations'] = recommendation_data['recommendations']
        
        return render_template('assessment_result.html',
                            assessment_type=assessment_type,
                            score=score,
                            max_score=max_score,
                            recommendation=recommendation_data)

    except ValueError:
        flash('Invalid score parameter')
        return redirect(url_for('home'))

@app.route('/mood', methods=['GET', 'POST'])
@login_required
def mood():
    try:
        conn = get_db_connection()
        
        if request.method == 'POST':
            mood = request.form.get('mood')
            notes = request.form.get('notes', '')
            
            if not mood or not mood.isdigit() or not (1 <= int(mood) <= 5):
                flash('Please select a valid mood value (1-5)')
                return redirect(url_for('mood'))
            
            conn.execute('''
                INSERT INTO mood_entries (user_id, mood, notes)
                VALUES (?, ?, ?)
            ''', (session['user_id'], int(mood), notes))
            conn.commit()

        entries = conn.execute('''
            SELECT * FROM mood_entries 
            WHERE user_id = ?
            ORDER BY timestamp DESC
        ''', (session['user_id'],)).fetchall()
        
        chart_data = conn.execute('''
            SELECT timestamp, mood FROM mood_entries
            WHERE user_id = ?
            ORDER BY timestamp
        ''', (session['user_id'],)).fetchall()
        
        dates = []
        moods = []
        for entry in chart_data:
            try:
                dt = datetime.datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S")
                dates.append(dt.strftime("%Y-%m-%d"))
                moods.append(entry['mood'])
            except Exception as e:
                print(f"Date processing error: {str(e)}")

        return render_template('mood.html',
                            mood_entries=entries,
                            dates=dates,
                            moods=moods)

    except Exception as e:
        flash(f'Error accessing mood tracker: {str(e)}')
        return redirect(url_for('home'))
    finally:
        if conn:
            conn.close()

@app.route('/delete_mood/<int:entry_id>', methods=['POST'])
@login_required
def delete_mood(entry_id):
    try:
        with get_db_connection() as conn:
            conn.execute('DELETE FROM mood_entries WHERE id = ? AND user_id = ?',
                       (entry_id, session['user_id']))
            conn.commit()
        flash('Entry deleted successfully')
    except Exception as e:
        flash('Error deleting entry')
    return redirect(url_for('mood'))

@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/chat', methods=['POST'])
@limiter.limit("10/minute")
@login_required
def handle_chat():
    try:
        # Validate session existence
        if 'user_id' not in session or 'last_assessment' not in session:
            return jsonify({'error': 'Please complete an assessment first!'}), 401

        # Validate request structure
        data = request.json
        if not data or 'message' not in data or 'context' not in data:
            return jsonify({'error': 'Invalid request format'}), 400

        # Get session data
        user_id = session['user_id']
        last_assessment = session['last_assessment']

        # Validate session consistency (FIXED LINE)
        if (str(data['context'].get('user_id')) != str(user_id) or 
            data['context'].get('type') != last_assessment['type']):
            return jsonify({'error': 'Session mismatch. Please restart assessment.'}), 403

        # Content safety check
        unsafe_terms = ['suicide', 'self-harm', 'kill myself', 'end it all']
        if any(term in data['message'].lower() for term in unsafe_terms):
            return jsonify({
                'response': '❗ Emergency Resources:\n'
                            '1. National Suicide Prevention Lifeline: 1-800-273-8255\n'
                            '2. Crisis Text Line: Text HOME to 741741\n'
                            '3. Local Emergency Services: 911'
            })

        # Initialize OpenAI client
        client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=10  # 10 second timeout
        )

        # Prepare system prompt
        assessment_type = last_assessment['type']
        score = last_assessment['score']
        max_score = 27 if assessment_type == 'phq9' else 21
        
        system_prompt = f"""You are a mental health support assistant. Context:
- User ID: {user_id}
- Assessment: {assessment_type.upper()} ({score}/{max_score})
- Recommendations: {", ".join(data['context']['recommendations'][:3])}

Guidelines:
1. Provide practical, non-medical advice
2. Focus on implementing recommendations
3. Use simple language (8th grade level)
4. Keep responses under 150 words
5. Include concrete examples
6. End with encouragement
7. Never suggest medications"""

        # Create messages array
        messages = [
            {"role": "system", "content": system_prompt},
            *data.get('history', []),
            {"role": "user", "content": data['message']}
        ]

        # Get AI response
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=250,
            top_p=0.9
        )

        return jsonify({
            'response': response.choices[0].message.content.strip()
        })

    except openai.APIConnectionError as e:
        app.logger.error(f"OpenAI connection error: {str(e)}")
        return jsonify({'error': 'Connection failed. Check internet.'}), 503
    except openai.RateLimitError as e:
        app.logger.error(f"OpenAI rate limit: {str(e)}")
        return jsonify({'error': 'Too many requests. Wait 1 minute.'}), 429
    except openai.APIError as e:
        app.logger.error(f"OpenAI API error: {str(e)}")
        return jsonify({'error': 'AI service unavailable'}), 503
    except Exception as e:
        app.logger.error(f"General error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 
    

if __name__ == '__main__':
    init_db()
    app.run(debug=True)