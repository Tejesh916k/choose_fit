from flask import Flask, render_template, request, redirect, session, url_for
from flask_pymongo import PyMongo
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib.pyplot as plt
import os
from matplotlib.figure import Figure
import io
import base64
from flask import session

app = Flask(__name__)
app.secret_key = 'secret_key'
client= MongoClient("mongodb+srv://tejeshkesanakurthy:tejesh916k@cluster0.cnrtsld.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db=client["fitness_db"]
users=db["users"]
workouts=db["workouts"]
meals=db["meals"]
bmi_records=db["bmi_records"]
meal_logs=db["meal_logs"]

@app.route('/')
def home():
    return redirect(url_for('login'))


from datetime import datetime

@app.route('/calculate_bmi', methods=['POST'])
def calculate_bmi():
    if 'email' not in session:
        return redirect(url_for('login'))

    height = float(request.form['height'])
    weight = float(request.form['weight'])
    email = session['email']

    bmi = round(weight / (height ** 2), 2)

   
    bmi_records.insert_one({
        'email': email,
        'height': height,
        'weight': weight,
        'bmi': bmi,
        'timestamp': datetime.now(),
        'name': users.find_one({'email': email})['name']  # If 'users' collection has name
    })

    return render_template('dashboard.html', bmi=bmi, message="BMI calculated and stored successfully!")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user = {
            "name": request.form['name'],
            "email": request.form['email'],
            "password": generate_password_hash(request.form['password'])
        }
        users.insert_one(user)
        return redirect('/login')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = users.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['email'] = email
            return redirect('/choose_log')
        return "Invalid credentials!"
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/choose_log')
def choose_log():
    if 'email' not in session:
        return redirect('/login')
    return render_template('choose_log.html')




@app.route('/progress', methods=['GET', 'POST'])
def progress():
    user_email = session['email']
    data = list(workouts.find({'email': user_email}))

    if not data:
        return render_template('dashboard.html', chart_url=None)

    dates = [entry['date'] for entry in data]
    durations = [int(entry['duration']) for entry in data]
    intensity_map = {'low': 1, 'medium': 2, 'high': 3}
    intensities = [intensity_map.get(entry['intensity'].lower(), 0) for entry in data]


    fig = Figure(figsize=(6, 4))
    ax = fig.subplots()
    ax.plot(dates, durations, marker='o', label='Duration (min)', color='blue')
    ax.plot(dates, intensities, marker='s', label='Intensity', color='orange')
    ax.set_title("Workout Progress Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Metric")
    ax.legend()
    fig.autofmt_xdate()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    chart_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')

    # Motivational quote or comment
    quote = "Keep grinding – every drop of sweat counts! 💪"

    return render_template('dashboard.html', chart_url=chart_url, quote=quote)


@app.route('/log_workout', methods=['GET', 'POST'])
def log_workout():
    if request.method == 'POST':
        workout = {
                "email": session['email'],
                "date": request.form['date'],
                "exercise_type": request.form['exercise_type'],
                "duration": request.form['duration'],
                "intensity": request.form['intensity'],
                "reps": request.form.get('reps'),
                "sets": request.form.get('sets'),
                "weight": request.form.get('weight')
        }

        workouts.insert_one(workout)
        return redirect('/progress') 
    return render_template('workout_log.html')


from datetime import datetime

@app.route('/log_meals', methods=['GET', 'POST'])
def log_meals():
    if 'email' not in session:
        return redirect('/login')

    if request.method == 'POST':
        juice = int(request.form.get('juices', 0))
        breakfast = int(request.form.get('breakfast', 0))
        dinner = int(request.form.get('dinner', 0))
        nuts = int(request.form.get('nuts', 0))
        dairy = int(request.form.get('dairy', 0))
        dessert = int(request.form.get('desserts', 0))

        total_calories = breakfast + juice + dessert + dinner + nuts + dairy

        user_email = session.get('email')
        user_bmi = bmi_records.find_one({'email': user_email})

        if user_bmi:
            height = float(user_bmi['height'])
            weight = float(user_bmi['weight'])
            recommended_calories = 25 * weight
        else:
            height = weight = recommended_calories = 0

        calorie_diff = recommended_calories - total_calories
        suggestion = (
            f"You're on track! 🎯 Eat {abs(calorie_diff):.1f} more calories."
            if calorie_diff > 0 else
            f"You've consumed {abs(calorie_diff):.1f} calories extra today! Consider a walk or workout. 🏃"
        )

        meal_logs.insert_one({
            'email': user_email,
            'breakfast': breakfast,
            'juice': juice,
            'dessert': dessert,
            'dinner': dinner,
            'nuts': nuts,
            'dairy': dairy,
            'total_calories': total_calories,
            'recommended_calories': recommended_calories,
            'timestamp': datetime.now(),
            'suggestion': suggestion
        })

        return render_template('meal_result.html',
                               total_calories=total_calories,
                               recommended_calories=recommended_calories,
                               suggestion=suggestion)

    return render_template('meal_log.html')



@app.route('/bmi', methods=['POST'])
def bmi():
    weight = float(request.form['weight'])
    height = float(request.form['height'])

    bmi_value = round(weight / (height ** 2), 2)

    if bmi_value < 18.5:
        status = "Underweight"
    elif 18.5 <= bmi_value < 24.9:
        status = "Normal weight"
    elif 25 <= bmi_value < 29.9:
        status = "Overweight"
    else:
        status = "Obesity"

    return render_template('dashboard.html', bmi=bmi_value, bmi_status=status)



# Route to generate a simple matplotlib chart (e.g., calorie intake)



if __name__ == '__main__':
    app.run(debug=True)
