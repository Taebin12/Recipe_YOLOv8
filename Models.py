from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy() 

class User(db.Model): 
    __tablename__ = 'user_table'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(32), unique=True, nullable=False)
    userid = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(8), nullable=False)

    def __init__(self, email, password):
        self.email = email
        self.set_password(password)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
 
    def check_password(self, password):
        return check_password_hash(self.password, password)