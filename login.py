import os #디렉토리 절대 경로
from flask import Flask
from flask import render_template #template폴더 안에 파일을 쓰겠다
from flask import request #회원정보를 제출할 때 쓰는 request, post요청 처리
from flask import redirect #리다이렉트
#from flask_sqlalchemy import SQLAlchemy
from Models import db
from Models import User
from flask import session #세션
from flask_wtf.csrf import CSRFProtect #csrf
from Forms import RegisterForm, LoginForm
app = Flask(__name__)
from werkzeug.security import check_password_hash

@app.route('/')
def mainpage():
    userid = session.get('userid',None)
    return render_template('index.html', userid=userid)
    

@app.route('/register', methods=['GET', 'POST']) #GET(정보보기), POST(정보수정) 메서드 허용
def register():
    form = RegisterForm()
    if form.validate_on_submit(): #유효성 검사. 내용 채우지 않은 항목이 있는지까지 체크
        usertable = User(email=form.data.get('email'), password=form.data.get('password'))
        usertable.userid = form.data.get('userid')

        db.session.add(usertable) #DB저장
        db.session.commit() #변동사항 반영
        
        return "회원가입 성공" 
    return render_template('register.html', form=form) #form이 어떤 form인지 명시한다

def login_logic(email, password):
    user = User.query.filter_by(email=email).first()
    if user is not None and check_password_hash(user.password, password):
        return True
    else:
        return False

@app.route('/login', methods=['GET','POST'])  
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        success = login_logic(email, password)
        if success:
            session['userid'] = form.userid.data
            return redirect(url_for('mainpage'))
        else:
            flash('유효하지 않은 이메일 또는 비밀번호입니다')
    return render_template('login.html', form=form)



@app.route('/logout', methods=['GET'])
def logout():
    session.pop('userid', None)
    return redirect('/')

if __name__ == "__main__":
    #데이터베이스---------
    basedir = os.path.abspath(os.path.dirname("/workspace/Flask_Team4/Web/users")) #현재 파일이 있는 디렉토리 절대 경로
    dbfile = os.path.join(basedir, 'db.sqlite') #데이터베이스 파일을 만든다

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + dbfile
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True #사용자에게 정보 전달완료하면 teadown. 그 때마다 커밋=DB반영
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #추가 메모리를 사용하므로 꺼둔다
    app.config['SECRET_KEY']='asdfasdfasdfqwerty' #해시값은 임의로 적음

    csrf = CSRFProtect()
    csrf.init_app(app)

    db.init_app(app) #app설정값 초기화
    db.app = app #Models.py에서 db를 가져와서 db.app에 app을 명시적으로 넣는다
    db.create_all() #DB생성

    app.run(host="0.0.0.0", port=5000, debug=True)