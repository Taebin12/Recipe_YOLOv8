from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms import PasswordField
from wtforms.validators import DataRequired, EqualTo
from Models import User #Models.py 가져옴

class RegisterForm(FlaskForm):
    userid = StringField('userid', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    password_2 = PasswordField('password_2', validators=[DataRequired(), EqualTo('password', message='비밀번호가 일치하지 않습니다.')])

    def validate_userid(self, field):
        if User.query.filter_by(userid=field.data).first():
            raise ValidationError('이미 사용 중인 아이디입니다.')

class LoginForm(FlaskForm):
    class UserPassword(object):
        def __init__(self, message=None):
            self.message = message

        def __call__(self, form, field):
            userid = form['userid'].data
            password = field.data

            usertable = User.query.filter_by(userid=userid).first()
            if not usertable or not usertable.check_password(password):
                raise ValueError('비밀번호 틀림')

    userid = StringField('userid', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired(), UserPassword()])