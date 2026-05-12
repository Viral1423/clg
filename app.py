from flask import Flask , request , redirect , render_template , url_for ,flash ,session
import bcrypt
from flask_sqlalchemy import SQLAlchemy 
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
app = Flask(__name__)

# app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:Veer4220H@localhost:5432/farewell_user"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
# app.secret_key = "Veer4220H"
app.secret_key = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "static/uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)
class User(db.Model):
    id = db.Column(db.Integer , primary_key =True)
    username = db.Column(db.String(100) , unique = True ,nullable =False)
    password = db.Column(db.LargeBinary ,nullable =False)
    posts = db.relationship("ImgDb",backref="author" , cascade = "all,delete")

class ImgDb(db.Model):
    id = db.Column(db.Integer , primary_key = True)
    image = db.Column(db.String(300) , nullable=False)
    caption = db.Column(db.String(200))
    user_id = db.Column(db.Integer , db.ForeignKey("user.id"),nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.relationship('Like' , backref='post' ,lazy=True)

class Like(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    user_id = db.Column(db.Integer , db.ForeignKey("user.id"))
    post_id = db.Column(db.Integer , db.ForeignKey("img_db.id"))


with app.app_context():
    db.drop_all()
    db.create_all()


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login" , methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"].strip()
    user = User.query.filter_by(username=username).first()
    if user and bcrypt.checkpw(password.encode("utf-8"), user.password):
        session["username"]=username
        session["user_id"]=user.id
        return redirect(url_for("dashboard"))
    else:
        flash ("Invalid username or password")
        return redirect(url_for("home"))

@app.route("/signup-pg")
def signup_pg():
    return render_template("signup.html")

@app.route("/signup", methods=["POST"])
def signup():
    user = request.form["user"].strip()
    spass = request.form["spass"].strip()
    hashed = bcrypt.hashpw(spass.encode("utf-8"),bcrypt.gensalt())
    new_user = User(username= user , password = hashed)

    check_user= User.query.filter_by(username = user).first()
    if check_user:
        flash ("Username Already Exists!")
        return redirect (url_for("home"))
    else:
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("home"))
    

@app.route("/dashboard" )
def dashboard():
    if "username" not in session:
        return redirect(url_for("home"))
    username = session["username"]
    posts = ImgDb.query.order_by(ImgDb.created_at.desc()).limit(20).all()
    return render_template ("dashboard.html" , username = username , posts = posts)

@app.route("/upload" , methods=["POST"])
def upload():
    if "username" not in session:
        return redirect(url_for("home"))
    file = request.files["photo"]
    caption = request.form["caption"].strip()
    ALLOWED_EXTENSIONS = {"png" , "jpg" , "jpeg" ,"gif"}
    def allowed_file(filename):
        return "." in filename and \
            filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    if file and allowed_file(file.filename):
        filename =str(uuid.uuid4()) + "_" + secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"],filename)
        file.save(file_path)
        current_user = User.query.filter_by(username=session["username"]).first()
        new_post = ImgDb(image=filename,caption=caption,user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("dashboard"))
    else:
        flash ("Only png, jpg , jpeg , gif files are allowed")
        return redirect(url_for("dashboard"))


@app.route("/delete/<int:post_id>" , methods=["POST"])
def delete(post_id):
    if "username" not in session:
        return redirect(url_for("home"))
    post = ImgDb.query.get_or_404(post_id)
    current_user = User.query.filter_by(username=session["username"]).first()

    if post.user_id != current_user.id:
        flash ("Unauthorized Action")
        return redirect(url_for("dashboard"))
    image_path = os.path.join(app.config["UPLOAD_FOLDER"],post.image)
    if os.path.exists(image_path):
        os.remove(image_path)
    db.session.delete(post)
    db.session.commit()
    flash ("Post Deleted Successfully")
    return redirect(url_for("dashboard"))

@app.route("/profile/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first()
    posts = ImgDb.query.filter_by(user_id=user.id)\
        .order_by(ImgDb.created_at.desc()).all()
    total_post =len(posts)

    return render_template("profile.html",user=user ,posts=posts,total_post = total_post)




@app.route("/like/<int:post_id>" , methods=["POST"])
def like(post_id):
    if 'user_id' not in session:
        return render_template("index.html")
    
    existing_like= Like.query.filter_by(user_id=session["user_id"],post_id=post_id).first()
    if existing_like:
        db.session.delete(existing_like)
    else:
        new_likes = Like(user_id=session['user_id']  ,post_id=post_id)
        db.session.add(new_likes)

    db.session.commit()
    return redirect(url_for("dashboard"))



@app.route("/logout")
def logout():
    session.pop("username",None)
    session.pop("user_id",None)
    return redirect(url_for("home"))




if __name__ == "__main__":
    app.run(debug=True)