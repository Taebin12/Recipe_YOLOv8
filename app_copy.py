from flask import Flask, render_template, request, redirect,url_for, flash, session
from flask_login import login_user, logout_user, login_required,current_user,UserMixin,LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
from ultralytics import YOLO
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import argparse
import datetime
import io
import cv2
import numpy as np
import ast
import requests
import pandas as pd
from flask import session
from flask_wtf.csrf import CSRFProtect 
from Models import db
from Models import User
from Forms import RegisterForm, LoginForm
from flask_wtf.csrf import CSRFProtect
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

app.config['WTF_CSRF_ENABLED'] = False
csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = 'abcdef123456@#$'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + '/workspace/Flask_Team4/Web/user_db.sqlite'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

csrf = CSRFProtect()
csrf.init_app(app)
db.init_app(app)
db.app = app 
db.create_all()

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S-%f"

# Create User model
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(120))

    def __init__(self, username, password):
        self.username = username
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

# Create all tables in the database
db.create_all()


# YOLO model 
model = YOLO('/workspace/Flask_Team4/Web/models/CASE7.pt')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usertable = User.query.filter_by(username=userid).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('mainpage'))
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def mainpage():
    form = LoginForm()
    return render_template('index.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(form.username.data, generate_password_hash(form.password.data))
        db.session.add(new_user)
        try:
            db.session.commit()
            flash('Thanks for registering!')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('ERROR! Username ({}) already exists.'.format(form.username.data), 'error')
    return render_template('register.html', form=form)


recipes = pd.read_csv('/workspace/Flask_Team4/Web/datas/output_recipes.csv')

# Sample 1000 recipes to avoid memory issues
recipes = recipes.sample(1000, random_state=1)

def string_to_list(string):
    try:
        return ast.literal_eval(string)
    except ValueError:
        return []  # returns an empty list if the string cannot be parsed

def join_list(lst):
    if isinstance(lst, list):
        return ' '.join(lst)
    return ""

# convert the string representation of the list to an actual list
recipes['ingredients'] = recipes['ingredients'].apply(string_to_list)

# handle missing values
recipes['ingredients'] = recipes['ingredients'].fillna("")

# join all the items in the list with a space
recipes['ingredients_str'] = recipes['ingredients'].apply(join_list)
vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(recipes['ingredients_str'])
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

def valid_cuisine(cuisine):
    return cuisine in ['dish', 'dessert']

def valid_health(healthiness):
    return healthiness in [True, False]

def valid_vege_vegan(value):
    return value in [True, False]

def recommend_recipe_based_on_similarity_and_preferences(recipe_names, vege_vegan, food_type, healthiness, max_minutes):
    recipe_indices = []
    for recipe_name in recipe_names:
        if recipe_name not in recipes['name'].values:
            return (True, f"Error: {recipe_name} is not in our recipe database.")
        idx = recipes[recipes['name'] == recipe_name].index[0]
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = [score for score in sim_scores if recipes.iloc[score[0]]['vege/vegan'] == vege_vegan and recipes.iloc[score[0]]['food type'] == food_type and recipes.iloc[score[0]]['healthiness'] == healthiness and recipes.iloc[score[0]]['minutes'] <= max_minutes]
        sim_scores = sim_scores[1:11]
        recipe_indices.extend([i[0] for i in sim_scores])
    return (False, recipes.iloc[recipe_indices])

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


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

        return render_template("result_selected.html", img_url=img_savename, detections=detection_results, form=RegisterForm()) 

    return render_template("index.html", form=RegisterForm()) 

@app.route('/recipes', methods=['POST', 'GET'])
def root_page():
    if request.method == 'POST':
        if ('selected_ingredients' and 'usertime' and 'usercuisine' and 'userhealth' and 'user_vege_vegan') not in request.form:
            return "Missing form parameters", 400

        recipe_names = request.form.getlist('selected_ingredients')
        max_minutes = int(request.form.get('usertime'))
        food_type = request.form.get('usercuisine')
        healthiness = True if request.form.get('userhealth') == 'true' else False
        vege_vegan = True if request.form.get('user_vege_vegan') == 'true' else False

        if not valid_cuisine(food_type) or not valid_health(healthiness) or not valid_vege_vegan(vege_vegan):
            return "Invalid parameters", 400

        try:
            error, data = recommend_recipe_based_on_similarity_and_preferences(recipe_names, vege_vegan, food_type, healthiness, max_minutes)
            if error:
                return data, 500  # if an error occurred, `data` contains the error message
        except Exception as e:
            return f"Error occurred: {str(e)}", 500

        return render_template("recipe_copy.html", data=data.to_dict(orient='records'), form=RegisterForm())

    elif request.method == 'GET':
        return render_template("recipe_form.html", form=RegisterForm())



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flask app exposing yolov8 models")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    args = parser.parse_args()
    
    app.run(host="0.0.0.0", port=args.port, debug=True)
