from flask import Flask, render_template, request, redirect
from PIL import Image
from ultralytics import YOLO
import argparse
import datetime
import io
import cv2
import numpy as np
import requests
import pandas as pd
from flask import session
from flask_wtf.csrf import CSRFProtect 
from Models import db
from Models import User
from Forms import RegisterForm, LoginForm
from flask_wtf.csrf import CSRFProtect


app = Flask(__name__)

app.config['WTF_CSRF_ENABLED'] = False
csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = 'abcdef123456@#$'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + 'path-to-your-database'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

csrf = CSRFProtect()
csrf.init_app(app)
db.init_app(app)
db.app = app 
db.create_all()


DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S-%f"

# YOLO model 
model = YOLO('/workspace/Flask_Team4/Web/models/CASE7.pt')

@app.route('/home')
def mainpage():
    form = LoginForm()  
    userid = session.get('userid', None)
    return render_template('index.html', userid=userid, form=form)

@app.route('/register', methods=['GET', 'POST']) 
def register():
    form = RegisterForm()
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET','POST'])  
def login():
    form = LoginForm()
    return render_template('login.html', form=form)

@app.route('/logout', methods=['GET'])
def logout():
    return redirect('/')


def valid_cuisine(cuisine):
    valid_cuisines = ['American', 'Asian', 'British', 'Caribbean', 'Central Europe', 'Chinese', 'Eastern Europe', 'French', 'Indian', 'Italian', 'Japanese', 'Kosher', 'Mediterranean', 'Mexican', 'Middle Eastern', 'Nordic', 'South America', 'South East Asian']
    return cuisine in valid_cuisines

def valid_health(health):
    valid_healths = ['vegan', 'vegetarian', 'sugar-conscious', 'peanut-free', 'tree-nut-free', 'alcohol-free']
    return health in valid_healths or health == 'none'

@app.route("/", methods=["GET", "POST"])    
def predict():
    if request.method == "POST":
        if "file" not in request.files:
            return redirect(request.url)

        file = request.files["file"]
        if not file:
            print("No file uploaded")
            return

        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes))
        img = img.resize((400, 400))  

        results = model(img)
        res_plotted = results[0].plot(show_conf=True)
        
        res_plotted = cv2.cvtColor(np.array(res_plotted), cv2.COLOR_BGR2RGB)

        now_time = datetime.datetime.now().strftime(DATETIME_FORMAT)
        img_savename = f"static/{now_time}.png"
        Image.fromarray(res_plotted).save(img_savename)

        detection_results = []
        for box in results[0].boxes:
            class_id = box.cls[0].item()
            object_type = model.names[class_id]
            prob = round(box.conf[0].item(), 2)
            detection_results.append({
                "object_type": object_type,
                "probability": prob
            })

        return render_template("result_copy.html", img_url=img_savename, detections=detection_results, form=RegisterForm()) 

    return render_template("index.html", form=RegisterForm()) 

@app.route('/recipes', methods=['POST', 'GET'])
def root_page():
    if request.method == 'POST':
        if ('selected_ingredients' and 'usertime' and 'usercuisine' and 'userhealth') not in request.form:
            return "Missing form parameters", 400
        
        ingredient = request.form.get('selected_ingredients')
        max_time = int(request.form.get('usertime'))
        cuisine = request.form.get('usercuisine')
        health = request.form.get('userhealth')

        
        if not valid_cuisine(cuisine) or not valid_health(health):
            return "Invalid cuisine or health parameter", 400

        try:
            data = recipe_search(ingredient, max_time, cuisine, health)
        except Exception as e:
            return f"Error occurred: {str(e)}", 500

        return render_template("recipe_results.html", data=data, form=RegisterForm()) 

    elif request.method == 'GET':
        return render_template("recipe_form.html", form=RegisterForm()) 

def recipe_search(ingredient, max_time, cuisine, health):
    app_id = 'f9be7661'
    app_key = 'ba280bf55340084f4c976d4d54216a82'

    if health == 'none':
        result = requests.get('https://api.edamam.com/search?q={}&app_id={}&app_key={}&time=1-{}'.format(ingredient, app_id, app_key, max_time))
    else:
        result = requests.get('https://api.edamam.com/search?q={}&app_id={}&app_key={}&time=1-{}&health={}'.format(ingredient, app_id, app_key, max_time, health))
    
    if result.status_code != 200:
        raise Exception("API request failed with status code {}".format(result.status_code))
    
    data = result.json()
    
    if 'hits' not in data:
        raise Exception("Invalid API response")
    
    return data['hits']

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flask app exposing yolov8 models")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    args = parser.parse_args()
    
    app.run(host="0.0.0.0", port=args.port, debug=True)
