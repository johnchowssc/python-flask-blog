## Web display
from flask import Flask, render_template, redirect, url_for, flash, abort, send_from_directory
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor

## Database
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy_utils import database_exists
import psycopg2

## Authentication
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps ## For admin_only decorator functions

from forms import CommentForm, CreatePostForm, LoginUserForm, RegisterUserForm
from flask_gravatar import Gravatar

from datetime import date

import sys
import logging

## Environment variables
import os
from dotenv import load_dotenv
load_dotenv()

## Markdown
import markdown

####################

##Initialise Flask
app = Flask(__name__)

app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)

# Run in terminal to generate secret key
# python -c 'import secrets; print(secrets.token_hex())'
app.config['SECRET_KEY'] = os.getenv("APP_SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)

##INITIALISE DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///blog.db") ## Use Heroku Postgres, or if not found, e.g. local, SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

##CONFIGURE TABLES
## User Class
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    post = relationship("BlogPost", back_populates="comments")
    body = db.Column(db.Text, nullable=False)

## For Local SQLlite
# if database_exists('sqlite:///blog.db'):
#     print("Database exists")
# else:
#     ## Create Database and Admin User
#     db.create_all()
#     print("Database created")
#     try:
#         admin_user = User(
#         name = os.getenv("ADMIN_USER"),
#         email = os.getenv("ADMIN_EMAIL"),
#         password = generate_password_hash(os.getenv("ADMIN_PASSWORD"))    
#         )
#         db.session.add(admin_user)
#         db.session.commit()
#         print("Admin user created")
#     except:
#         print("Unable to create Admin user")

## Run once for Heroku Postgres
# db.create_all()
# admin_user = User(
#         name = os.getenv("ADMIN_USER"),
#         email = os.getenv("ADMIN_EMAIL"),
#         password = generate_password_hash(os.getenv("ADMIN_PASSWORD"))    
#         )
# db.session.add(admin_user)
# db.session.commit()
# print("Admin user created")

db.create_all()

## Admin-only decorator
def admin_only(function):
    wraps(function)
    def decorated_function(*args, **kwargs):
        try:
            if current_user.id != 1:
                return abort(403)
        except:
                return abort(403) # Anonymous user
        else:
            return function(*args, **kwargs)
    decorated_function.__name__ = function.__name__
    return decorated_function

##Initialise Flask Login
login_manager=LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

## Gravatar

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

## Routes
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterUserForm()
    if form.validate_on_submit():
        try:
            new_user = User(
            name = form.name.data,
            email = form.email.data,
            password = generate_password_hash(form.password.data)
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
        except:
            flash("Email already exists")
            return redirect(url_for("login"))
        return redirect(url_for("get_all_posts"))
        
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginUserForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash("User doesn't exist")
        elif not check_password_hash(user.password, form.password.data):
            flash("Password incorrect")
        else:
            login_user(user)
            return redirect(url_for("get_all_posts"))

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comments = Comment.query.all()
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            pass
        else:
            new_comment = Comment(
                body = form.body.data,
                author = current_user,
                post = requested_post
                ## TODO data stamp?
            )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))

    return render_template("post.html", post=requested_post, form=form, all_comments=comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author_id,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/addfile/<filename>")
# @admin_only
def add_file_post(filename):
    # print(filename)
    basedir = os.path.abspath(os.path.dirname(__file__))
    markdown_filepath = os.path.join(basedir, f"static/{filename}")
    # print(markdown_filepath)
    with open(markdown_filepath, "r") as file:
        md_text=file.read()
        print(md_text)
        html = markdown.markdown(md_text)
        print(html)
    try: ##TODO Figure out a way to pull out the title etc.
        new_post = BlogPost(
            title="Title",
            subtitle="Subtitle",
            body=html,
            img_url="",
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
    except:
        pass
    return redirect(url_for("get_all_posts"))
   

if __name__ == "__main__":
    app.run(debug=True)
