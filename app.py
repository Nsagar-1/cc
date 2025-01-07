
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send, join_room, leave_room, emit
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
import os
import re
import random
from datetime import datetime
import smtplib
from uuid import uuid4


from datetime import date
import string
from werkzeug.utils import secure_filename
from flask import g
from flask import flash
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_socketio import SocketIO, emit, join_room, leave_room
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///advanced_platform.db'  # Update with your database URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['VIDEOS_FOLDER'] = "static/videos"
app.config['REEL_FOLDER'] = 'static/reels'
app.config['PROFILE_FOLDER'] = 'static/profile_pics'
app.config['COURSE_VIDEO_FOLDER'] = 'static/courses'
app.config['COURSE_RESOURCE_FOLDER'] = 'static/course_resources'
app.config['COURSE_ASSIGNMENT_FOLDER'] = 'static/course_assignments'
app.config['COURSE_INSTRUCTOR_FOLDER'] = 'static/course_instructors'
app.config['COURSE_THUMBNAIL_FOLDER'] = 'static/courses_thumbnail'
app.config['COURSE_VIDEO_FOLDER'] = 'static/courses'
app.config['UPLOAD_FOLDER'] = 'static/uploads/photos'
app.secret_key = 'super_secret_key'
app.config['ALLOWED_EXTENSIONS'] = set()  # Empty set allows all file types






db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app)

friends = db.Table('friends',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)
# Association table for likes
likes = db.Table('likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('reel_id', db.Integer, db.ForeignKey('reel.id'), primary_key=True)
)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    profile_pic = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(128))
    liked_reels = db.relationship('Reel', secondary=likes, backref='liked_by', lazy='dynamic')
    webinars = db.relationship('Webinar', backref='creator', lazy=True)
    courses_uploaded = db.relationship('Course', backref='uploader_user', lazy=True)  



    
    # New GPA fields for classes 9 to 12
    gpa_class_9 = db.Column(db.String(5), nullable=True)
    gpa_class_10 = db.Column(db.String(5), nullable=True)
    gpa_class_11 = db.Column(db.String(5), nullable=True)
    gpa_class_12 = db.Column(db.String(5), nullable=True)
    
    # Existing fields
    sat_score = db.Column(db.String(10), nullable=True)
    gpa = db.Column(db.String(5), nullable=True)
    eca = db.Column(db.String(120), nullable=True)
    essay = db.Column(db.Text, nullable=True)
    
    # New fields for university status
    universities_to_apply = db.Column(db.Text, nullable=True)  # Comma-separated list of universities
    universities_applied = db.Column(db.Text, nullable=True)   # Comma-separated list of universities
    universities_studying = db.Column(db.String(120), nullable=True)  # Currently studying at

    # New fields for Major and Minor
    major_subject = db.Column(db.String(100), nullable=True)
    minor_subject = db.Column(db.String(100), nullable=True)

    stars_received = db.Column(db.Integer, default=0)

    # Adding the friends relationship
    friends = db.relationship(
        'User', 
        secondary=friends,
        primaryjoin=(friends.c.user_id == id),
        secondaryjoin=(friends.c.friend_id == id),
        backref=db.backref('user_friends', lazy='dynamic'),
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_friends_with(self, user):
        return user in self.friends


class ChatMessage(db.Model):
    __tablename__ = 'chat_message'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(50), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)

    server = db.relationship('Server', backref='messages')



class Star(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    giver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # The user who gives the star
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # The user who receives the star

    giver = db.relationship('User', foreign_keys=[giver_id], backref='given_stars')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_stars')


class HelperRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    helper_type = db.Column(db.String(20), nullable=False)  # 'lor' or 'counsel'
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'accepted', 'declined'

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_helper_requests')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_helper_requests')


#class UserChallenge(db.Model):
 #   __tablename__ = 'user_challenge'
  #  id = db.Column(db.Integer, primary_key=True)
 #   user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
'''  course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    completion_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50))  # Add this if missing
    
    # Relationships (optional) '''


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Define the relationship
    user = db.relationship('User', backref='posts', lazy=True)


    



class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # This refers to the User model
    thumbnail = db.Column(db.String(120), nullable=True)  
    slug = db.Column(db.String(10), unique=True, nullable=False)  # Add slug field
    # New Fields
    introduction = db.Column(db.Text, nullable=True)  # Plain text field for Introduction
    course_outline = db.Column(db.Text, nullable=True)  # Plain text field for Course Outline
    # Relationships to the new tables
    resources = db.relationship('CourseResource', backref='course', lazy=True)  
    assignments = db.relationship('CourseAssignment', backref='course', lazy=True)  
    instructors = db.relationship('CourseInstructor', backref='course', lazy=True)
    videos = db.relationship('CourseVideo', backref='course_video', lazy=True)  
    course_length = db.Column(db.String(8), nullable=True)  # Format: HH:MM:SS
    upload_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    uploader = db.relationship('User', backref='uploaded_courses')  # Add this relationship



    def generate_slug(self):
        if not self.slug:
            self.slug = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            while Course.query.filter_by(slug=self.slug).first():
                self.slug = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    # Call this method when a new course instance is created
    def __init__(self, *args, **kwargs):
        super(Course, self).__init__(*args, **kwargs)
        self.generate_slug()


class CourseVideo(db.Model):
    __tablename__ = 'course_video'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    filename = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

    # Use a string reference for the relationship
    course = db.relationship('Course', backref='videos_list', lazy=True)

class CourseProgress(db.Model):
    __tablename__ = 'course_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    remaining_time = db.Column(db.String(8), nullable=False)  # Format: HH:MM:SS
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='progresses')
    course = db.relationship('Course', backref='progresses')


class CourseResource(db.Model):
    __tablename__ = 'course_resource'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

class CourseAssignment(db.Model):
    __tablename__ = 'course_assignment'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)


class CourseInstructor(db.Model):
    __tablename__ = 'course_instructor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    profile_link = db.Column(db.String(255), nullable=True)
    fb_link = db.Column(db.String(255), nullable=True)
    linkedin_link = db.Column(db.String(255), nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)  # Add this field
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)




#####################################################################                REEELS   START           #####################################################################

@app.route('/delete_course/<slug>', methods=['POST'])
def delete_course(slug):
    course = Course.query.filter_by(slug=slug).first()
    
    try:
        # Delete related course videos, resources, assignments, and instructors
        CourseVideo.query.filter_by(course_id=course.id).delete()
        CourseResource.query.filter_by(course_id=course.id).delete()
        CourseAssignment.query.filter_by(course_id=course.id).delete()
        CourseInstructor.query.filter_by(course_id=course.id).delete()

        # Delete the course itself
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully!', 'success')
    
    except IntegrityError:
        db.session.rollback()
        flash('An error occurred while deleting the course.', 'error')
    
    return redirect(url_for('made_courses'))


class Reel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(120), nullable=False)
    likes = db.Column(db.Integer, default=0)
    shares = db.Column(db.Integer, default=0)
    visibility = db.Column(db.String(20), nullable=False)  # 'Public', 'Friends', 'Private'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # The uploader
    tags = db.Column(db.String(120), nullable=True)
    comments = db.relationship('ReelComment', backref='reel', lazy=True)
    
    # Add slug field
    slug = db.Column(db.String(10), unique=True, nullable=False)

    # Ensure each reel has a unique slug
    def generate_slug(self):
        if not self.slug:
            self.slug = self._generate_unique_slug()

    def _generate_unique_slug(self):
        slug = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        while Reel.query.filter_by(slug=slug).first():
            slug = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        return slug





class ReelComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    reel_id = db.Column(db.Integer, db.ForeignKey('reel.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Adding a reference to the user












#####################################################################                REEELS   END           #####################################################################




























# Moved `db.create_all()` to the correct place inside the app context

class Webinar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    webinar_id = db.Column(db.String(50), nullable=True)  # Optional
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    meeting_type = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(20), nullable=False)  # Use proper date type if needed
    time = db.Column(db.String(10), nullable=False)
    link = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Establish relationship with User model

    def __repr__(self):
        return f'<Webinar {self.title}>'

    
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    filename = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    tags = db.Column(db.String(120), nullable=True)
    privacy = db.Column(db.String(50), nullable=False, default='public')
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved = db.Column(db.Boolean, default=False)
    unique_id = db.Column(db.String(10), unique=True, nullable=False)
    

    uploader = db.relationship('User', backref=db.backref('videos', lazy=True))

    
    def __init__(self, *args, **kwargs):
        super(Video, self).__init__(*args, **kwargs)
        if not self.unique_id:
            self.unique_id = self.generate_unique_id()

    @staticmethod
    def generate_unique_id(length=10):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    def get_reaction_counts(self):
        like_count = Reaction.query.filter_by(video_id=self.id, reaction_type='like').count()
        love_count = Reaction.query.filter_by(video_id=self.id, reaction_type='love').count()
        haha_count = Reaction.query.filter_by(video_id=self.id, reaction_type='haha').count()
        return {
            'like': like_count,
            'love': love_count,
            'haha': haha_count
        }

class Server(db.Model):
    __tablename__ = 'server'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)  # Ensure the code is unique
    
    owner = db.relationship('User', backref='servers')
    members = db.relationship('User', secondary='server_members', backref='joined_servers')

    def generate_unique_code(self):
        while True:
            # Generate a random string of length 10
            generated_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            
            # Check if the code already exists in the database
            existing_server = Server.query.filter_by(code=generated_code).first()
            
            if not existing_server:
                self.code = generated_code
                break





class ServerMembers(db.Model):
    __tablename__ = 'server_members'
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # For private messages between users
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # For group messages
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    group = db.relationship('Group', backref='group_messages')

    def __repr__(self):
        return f'<Message {self.content}>'


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    members = db.relationship('User', secondary='group_members', backref='groups')

# Association table for Group members
group_members = db.Table('group_members',
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


class Mentorship(db.Model):
    __tablename__ = 'mentorship'
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mentee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    mentor = db.relationship('User', foreign_keys=[mentor_id])
    mentee = db.relationship('User', foreign_keys=[mentee_id])


    @property
    def duration(self):
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            weeks = delta.days // 7
            days = delta.days % 7
            return f"{weeks} weeks" if weeks else f"{days} days"
        return None


class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reaction_type = db.Column(db.String(20))  # 'like', 'love', 'haha', 'wow', 'sad', 'angry'

    user = db.relationship('User', backref=db.backref('reactions', lazy=True))
    video = db.relationship('Video', backref=db.backref('reactions', lazy=True))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    
    video = db.relationship('Video', backref=db.backref('comments', lazy=True))
    user = db.relationship('User', backref=db.backref('comments', lazy=True))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)


class PrivateMessage(db.Model):
    __tablename__ = 'private_message'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_private_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_private_messages')


class VideoWatchTime(db.Model):
    __tablename__ = 'video_watch_time'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('course_video.id'), nullable=False)
    watch_time = db.Column(db.Integer, default=0)  # Time in seconds

    # Relationships
    user = db.relationship('User', backref='watched_videos')
    video = db.relationship('CourseVideo', backref='watch_times')


class ServerPost(db.Model):
    __tablename__ = 'server_posts'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(255))
    media_filename = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Use a unique backref name to avoid conflict
    user = db.relationship('User', backref='server_posts')
    server = db.relationship('Server', backref='posts')

class VideoAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    comments = db.Column(db.Integer, default=0)

class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # Default to 'pending'

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_requests')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_requests')

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)

# Chat rooms and users tracking
users_in_rooms = {}



# Routes

@app.context_processor
def inject_global_variables():
    user = User.query.filter_by(username=session['username']).first() if 'username' in session else None

    return {
        'user': user,
        'user_profile_pic': user.profile_pic if user and user.profile_pic else 'default.jpg',
        'notification': "notification.png",
        'inbox': "chaticon.png",
        'video': "videoicon.png",
        'search': "search.png",
        'myfriends': "friendsicon.png",
        'group': "servericon.png",
        'mycourses': "coursesicon.png",
        'notificationbell': "notificationbell.png",
        'webinar': "webinar.png",
        'mychat': "inbox.png",
        'myreels': "video.png",
        'homeicon': "homeicon.png",
        'profileicon': "profileicon.png",
        'helpersicon': "helpers.png",
        'ai': "ai.png",
        'scholarshipicon': "scholarshipicon.png",
        'photo': "photo.png",
        'livevideo': "live-video.png",
        'portfolioicon' : "portfolioicon.png",
        'resumeicon' : "resumeicon.png",
        'mylogo' : 'logo.jpg',
    }

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password'] 
        session['user_type']= "new_user"

        username = username.capitalize()

         #Validate password strength
        if len(password) < 8:
            return render_template('register.html', message ='Password must be at least 8 characters long')
        
             # Check if the email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            message = 'Email already exists. Please choose a different email.'
            return render_template('register.html', message=message, username=username, password=password)

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            message = 'Username already exists. Please choose a different username.'
            return render_template('register.html', message=message, username=username, password=password)
        
        emailVerify()

        # Create and save the new user
        new_user = User(username=username, email=email  )
        new_user.set_password(password)  # Hash the password
        db.session.add(new_user)

        
       
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            message = 'An error occurred while trying to register. Please try again.'
            return render_template('register.html', message=message, username=username, password=password)
         # Store both username and user_id in the session
        session['username'] = username
        session['user_id'] = new_user.id  # Store user ID in the session
        session['friends'] = []  # Initialize friends list as empty for a new user
        return render_template('verify.html')
    return render_template('register.html')


#def is_valid_password(password):
    # Define the pattern for strong passwords
   # pattern = r"^(?=.*[a-z])(?=.*\d)(?=.*[@$!%?&])[a-z\d@$!%?&]{8,}$"

    
    # Check if the password matches the pattern
    return bool(re.match(pattern, password))



def emailVerify():
    
    code = random.randint(100000, 999999)
    print(" \n \n \n \n code is : " + str(code) + " \n \n \n \n \n") 
#  Sending Email for verification
    smtp_port = 587
    session['generated_code'] = code

    sender_email = "campusconnect426@gmail.com"
    receiver_email = request.form['email']  # Recipient's email address
    password = "hxlt vkhr ibao fwfy"  #  gamil app-specific password
    receiver_email = receiver_email.lower()
    print ( " \n  \n \n  "+  receiver_email  + " \n \n \n ")

    subject = " Verfy your Account ( Campus Guider  )"
    body = "your verification code is " +  str(code) +" please enter this code to verify your account"
    text = f"Subject: {subject}\n\n{body}"
    server = smtplib.SMTP("smtp.gmail.com", smtp_port)
    server.starttls()
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, text)
    print("Email sent to:", receiver_email)
    server.quit()
    print("Quitiing the SMTP")
    session['email'] = receiver_email
    
    return redirect(url_for('verify' ))



@app.route('/verify' , methods = ['POST'])
def verify():
    
    user_type = session.get('user_type')
    render_template('verify.html')
    sent_code = request.form['code']
    generated_code =session.get('generated_code')

    if sent_code == str(generated_code):
          session.pop('verification_code', None)
          return render_template("verify.html" , message = "Sucessfully validated" , user_type = user_type )

    else:
          return render_template('verify.html' , message = "code did not match" , user_type = user_type  )
    
    


@app.route('/add_info', methods=['GET', 'POST'])
def add_info():
    if request.method == 'POST':
        # Proceed with processing form data
        user = User.query.filter_by(username=session['username']).first()
        
        # Fetch data from the form
        gpa_class_9 = request.form['gpa_9']
        gpa_class_10 = request.form['gpa_10']
        gpa_class_11 = request.form['gpa_11']
        gpa_class_12 = request.form['gpa_12']
        sat_score = request.form['sat_score']
        
        # Update user attributes
        user.gpa_class_9 = gpa_class_9
        user.gpa_class_10 = gpa_class_10
        user.gpa_class_11 = gpa_class_11
        user.gpa_class_12 = gpa_class_12
        user.sat_score = sat_score
        
        # Commit changes to the database
        db.session.commit()
        
        return redirect(url_for('public_feed')) 

    # If GET request, render the form
    return render_template('Add_info.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['username/email']
        password = request.form['password']
        username = None
        
        # Retrieve the user based on the username or email
        user = (User.query.filter_by(username=email).first() or User.query.filter_by(email=email).first())
        
        if user:
            username = user.username  # Only access 'username' if user is not None
            
            if user.check_password(password):
                # Store username, user ID, and friends list in the session
                session['username'] = username
                session['user_id'] = user.id  # Store user ID in the session
                session['friends'] = [friend.username for friend in user.friends]  # Initialize friends list in session

                # Directly access GPA attributes from the user object
                user_gpa_9 = user.gpa_class_9
                user_gpa_10 = user.gpa_class_10
                user_gpa_11 = user.gpa_class_11
                user_gpa_12 = user.gpa_class_12
                user_sat_score = user.sat_score

                # Check if any required fields are missing
                if (
                    user_gpa_9 is None or 
                    user_gpa_10 is None or 
                    user_gpa_11 is None or 
                    user_gpa_12 is None or 
                    user_sat_score is None
                ):
                    return redirect(url_for('add_info'))
                else:
                    return redirect(url_for('public_feed'))  # Redirect to public feed instead of dashboard
            else:
                # If password is incorrect, show an error message
                message = "Oops! Wrong Username or Password."
                return render_template('login.html', message=message, username=username, password=password)
        else:
            # If user is not found, show an error message
            message = "Oops! User not found."
            return render_template('login.html', message=message, username=email, password=password)
    
    # Render the login page for GET requests
    return render_template('login.html')


import random
from flask import session
from itertools import cycle

# Global variables to control chunk rotation and stop condition
chunk_rotation_iterator = None
last_chunk_order = None
rotation_stopped = False  # Flag to indicate whether rotation has stopped

@app.route('/forget_pass' , methods=['POST'])
def forget_pass():
    if request.method == 'POST':
        email = request.form['email']
        session['user_type'] = "existing_user"
        
        user_type = session.get('user_type')  
        session['email'] = email 

        print (email)

        user = User.query.filter_by(email=email).first()
        if user:
            message = "Code sent to your email"
            emailVerify()
            return render_template ( "verify.html" , user_type = user_type)
            

        else :
            message = "Email not found."
            print(message)
            return render_template("forget_pass.html" , messgae = message)

    return render_template("forget_pass.html")

@app.route('/new_password', methods=['POST'])
def new_password():

    password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    # Fetch the email stored in the session
    email = session.get('email')
    
    if not email:
        return render_template("forget_pass.html", message="Session expired. Please try again.")
    
    # Retrieve the user from the database
    user = User.query.filter_by(email=email).first()

    if not user:
        return render_template("forget_pass.html", message="User not found. Please try again.")

    # Get the new password and confirmation from the form

    
    # Clear the session variable for user type
    session.pop('user_type', None)
    
    if password == confirm_password:
        # Hash the password and update the user record
        user.set_password(password)
        db.session.commit()  # Save the updated user to the database
        return  redirect(url_for('login' , message ="Password Changed , Plase Login."))
    else:
        # Passwords don't match
        return render_template("new_password.html", message="Passwords do not match.")



@app.route('/<university_name>')
def university_page(university_name):
    # Check if the user is logged in and retrieve the user object
    user = User.query.filter_by(username=session['username']).first() if 'username' in session else None
    
    # Default profile picture if the user does not have one
    user_profile_pic = user.profile_pic if user and user.profile_pic else 'default.jpg'

    # Asset dictionary to handle university-specific and common images
    assets = {
        "notification": "notification.png",
        "inbox": "chaticon.png",
        "video": "videoicon.png",
        "search": "search.png",
        "friends": "friendsicon.png",
        "group": "servericon.png",
        "courses": "coursesicon.png",
        "notificationbell": "notificationbell.png",
        "webinar": "webinar.png",
        "chat": "inbox.png",
        "reels": "video.png",
        "homeicon": "homeicon.png",
        "profileicon": "profileicon.png",
        "helpersicon": "helpers.png",
        "ai": "ai.png",
        "scholarshipicon": "scholarshipicon.png",
        "photo": "photo.png",
        "livevideo": "live-video.png",
    }



    # Ensure the university name is correctly formatted for template rendering
    if university_name.endswith('.html'):
        university_name = university_name[:-5]  # Strip '.html' extension for safety

    # Get the specific university image or a default one
    university_image = f"{university_name}.jpeg"

    harvarduniversity = "harvarduniversity.jpeg"
    stanforduniversity = "stanforduniversity.jpeg"
    texasstateuniversity = "texastateuniversity.jpeg"

    # Render the template with context
    return render_template(
        f'{university_name}.html',
        user=user,
        user_profile_pic=user_profile_pic,
        university_image=university_image,
        harvarduniversity = harvarduniversity,
        stanforduniversity = stanforduniversity,
        texasstateuniversity = texasstateuniversity,
        **assets  # Unpack assets to be used in the template
    )



@app.route('/')
def index():
    return render_template('index.html')

def is_valid_password(password):
    # Define the pattern for strong passwords
    pattern = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    # Check if the password matches the pattern
    return bool(re.match(pattern, password))




import random
from flask import session
from itertools import cycle

# Global variables to control chunk rotation and stop condition
chunk_rotation_iterator = None
last_chunk_order = None
rotation_stopped = False  # Flag to indicate whether rotation has stopped

# Chat page route
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        content = request.form['content']
        username = session.get('username', 'Guest')  # Default to 'Guest' if no user is logged in
        server_id = request.form['server_id']  # Assume you pass server ID from the frontend

        # Save the message to the database
        new_message = ChatMessage(content=content, username=username, server_id=server_id)
        db.session.add(new_message)
        db.session.commit()

    # Get chat messages for the specific server
    server_id = request.args.get('server_id')  # Assume server ID is passed as query parameter
    messages = ChatMessage.query.filter_by(server_id=server_id).order_by(ChatMessage.timestamp.asc()).all()
    user = User.query.filter_by(username=session['username']).first()

    # Assuming you have a 'Friendship' table or a relationship in the 'User' model
    # Query for the friends of the logged-in user
    friends = user.friends  # Assuming `friends` is a relationship defined in the User model
    

    return render_template('chat.html', messages=messages, server_id=server_id, friends=friends)

@app.route('/essays')
def essays():
    return render_template('essays.html')


@app.route('/challenges')
def challenges():
    return render_template('challenges.html')

@app.route('/scholarshipsearch')
def scholarshipsearch():
    return render_template('scholarshipsearch.html')

@app.route('/upload_essay')
def upload_essay():
        return render_template('upload_essay')










@app.route('/courses')
def courses():
    global chunk_rotation_iterator, last_chunk_order, rotation_stopped

        # Fetch courses from the database, ordered by upload time (most recent first)
    courses = Course.query.order_by(Course.upload_time.desc()).all()

        # Determine chunk size dynamically based on the total number of courses
    total_courses = len(courses)
    chunk_size = max(2, total_courses // 5)  # Minimum chunk size is 2

        # Divide courses into chunks
    chunks = [courses[i:i + chunk_size] for i in range(0, len(courses), chunk_size)]

        # Shuffle courses within each chunk
    for chunk in chunks:
        random.shuffle(chunk)

        if rotation_stopped:
            # If rotation is stopped, maintain the last chunk order
            rotated_chunks = last_chunk_order
        else:
            # Initialize or update the global iterator for rotating chunks
            if not chunk_rotation_iterator:
                chunk_rotation_iterator = cycle(range(len(chunks)))

            # Get the next chunk rotation order
            try:
                rotation_index = next(chunk_rotation_iterator)
            except StopIteration:
                rotation_index = None  # or some other default value


            # Rotate chunks: Bring the selected chunk to the front
            rotated_chunks = chunks[rotation_index:] + chunks[:rotation_index]

            # Check if the current rotated order matches the previous one
            if rotated_chunks == last_chunk_order:
                rotation_stopped = True  # Stop further rotation
            else:
                last_chunk_order = rotated_chunks  # Update the last chunk order

        # Flatten the rotated and shuffled chunks into a single list
        shuffled_courses = [course for chunk in rotated_chunks for course in chunk]

        # Debugging output (optional)
        print(f"Rotated Chunks Order: {rotated_chunks}")
        print(f"Shuffled Courses: {[course.title for course in shuffled_courses]}")

        # Render the courses page
        return render_template('courses.html', courses=shuffled_courses)





@app.route('/get_username_suggestions', methods=['GET'])
def get_username_suggestions():
    query = request.args.get('query', '')
    user_id = session.get('user_id')  # Assume the user is logged in

    if not user_id or not query:
        return jsonify({'suggestions': []})

    # Find friends of the logged-in user whose username matches the query
    friends_list = db.session.query(User.username).join(
        friends, friends.c.friend_id == User.id
    ).filter(
        friends.c.user_id == user_id, 
        User.username.ilike(f'{query}%')
    ).limit(10).all()

    suggestions = [{'username': friend.username} for friend in friends_list]

    return jsonify({'suggestions': suggestions})


def allowed_file(filename):
    # Check if file extension is in allowed extensions
    return '.' in filename and (filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'] or not app.config['ALLOWED_EXTENSIONS'])


@app.route('/handle_helper_request/<int:request_id>', methods=['POST'])
def handle_helper_request(request_id):
    data = request.get_json()
    action = data.get('action')
    request_item = HelperRequest.query.get(request_id)
    
    if request_item and request_item.receiver_id == session['user_id']:
        if action == 'accept':
            request_item.status = 'accepted'
        elif action == 'reject':
            request_item.status = 'rejected'
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'error'}), 400


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        
        if request.method == 'POST':
            user.sat_score = request.form['sat_score']
            user.eca = request.form['eca']
            user.essay = request.form['essay']
            user.major_subject = request.form['major_subject']  # New field for Major
            user.minor_subject = request.form['minor_subject']  # New field for Minor
            
            # Handle profile picture upload
            if 'profile_pic' in request.files:
                profile_pic = request.files['profile_pic']
                if profile_pic:
                    filename = secure_filename(profile_pic.filename)
                    profile_pic.save(os.path.join(app.config['PROFILE_FOLDER'], filename))
                    user.profile_pic = filename
            
            db.session.commit()  # Save all updates to the database
            return redirect(url_for('profile'))
        
        # Assign a default profile picture if the user hasn't uploaded one
        user_profile_pic = user.profile_pic if user.profile_pic else 'default.jpg'
        
        return render_template('profile.html', user=user, user_profile_pic=user_profile_pic)
    
    return redirect(url_for('login'))



#####################################################################                REEELS   START           #####################################################################
#####################################################################                REEELS   START           #####################################################################
#####################################################################                REEELS   START           #####################################################################
#####################################################################                REEELS   START           #####################################################################
#####################################################################                REEELS   START           #####################################################################



def randomize_courses(courses):
    """
    Randomize courses based on upload time and a random factor.
    """
    def calculate_weight(course):
        # Calculate recency in seconds
        recency_seconds = (datetime.utcnow() - course.upload_time).total_seconds()

        # Invert recency to prioritize newer courses
        time_weight = max(1, 1 / recency_seconds) if recency_seconds > 0 else 1

        # Add a random factor
        random_weight = random.uniform(0.8, 1.2)  # Introduces some randomness

        # Final weight combines recency and randomness
        return time_weight * random_weight

    # Assign a weight to each course
    courses_with_weights = [
        {"course": course, "weight": calculate_weight(course)}
        for course in courses
    ]

    # Sort by weight in descending order
    randomized_courses = sorted(courses_with_weights, key=lambda x: x["weight"], reverse=True)

    # Extract and return courses only
    return [item["course"] for item in randomized_courses]

#@app.route('/challenges')
#def challenges():
    user_id = session.get('user_id')

    # Get the search query and section from the request
    section = request.args.get('section', 'available')

    # Initialize empty lists for both sections
    available_courses = []
    user_challenges = []

    if section == 'available':
        # Fetch available courses not yet added to challenges
        available_courses = Course.query.filter(
            ~Course.id.in_(
                db.session.query(UserChallenge.course_id).filter_by(user_id=user_id)
            )
        ).all()
        # Randomize available courses
        randomized_courses = randomize_courses(available_courses)
    else:
        # Fetch user challenges
        user_challenges = db.session.query(UserChallenge).join(Course).filter(
            UserChallenge.user_id == user_id
        ).all()

        # Update statuses for user challenges
        for challenge in user_challenges:
            # Skip updating status if it's already "Time Overdue"
            if challenge.status == "Time Overdue":
                continue

            # Check if the course is already completed
            if challenge.status != "Completed":
                completion_datetime = datetime.combine(challenge.completion_date, challenge.completion_time)
                current_datetime = datetime.now()

                if current_datetime > completion_datetime:
                    challenge.status = "Time Overdue"
                else:
                    challenge.status = "Not Completed"

                db.session.commit()  # Save status changes to the database

    # Render the challenges template with current section and query
    return render_template(
        'challenges.html',
        available_courses=randomized_courses if section == 'available' else [],
        current_section=section
    )



@app.route('/search_courses', methods=['GET'])
def search_courses():
    query = request.args.get('query', '').strip()
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))

    # Perform the search query
    if query:
        # Fetch matching courses
        matching_courses = Course.query.filter(Course.title.ilike(f"%{query}%")).all()

        # Separate into Available and User Challenges


        return render_template(
            'challenges.html'
        )

    return redirect(url_for('challenges'))


@app.route('/like_reel', methods=['POST'])
def like_reel():
    user_id = session.get('user_id')  # Assume user is logged in and their ID is stored in the session
    reel_id = request.json.get('reel_id')
    
    if not user_id or not reel_id:
        return jsonify({'success': False, 'message': 'User ID and Reel ID are required'}), 400

    user = User.query.get(user_id)
    reel = Reel.query.get(reel_id)

    if not user or not reel:
        return jsonify({'success': False, 'message': 'User or Reel not found'}), 404

    if reel in user.liked_reels:
        # If the user has already liked the reel, remove the like
        user.liked_reels.remove(reel)
        reel.likes -= 1
        db.session.commit()
        return jsonify({'success': True, 'liked': False, 'likes': reel.likes})
    else:
        # Otherwise, add the like
        user.liked_reels.append(reel)
        reel.likes += 1
        db.session.commit()
        return jsonify({'success': True, 'liked': True, 'likes': reel.likes})


@app.route('/get_course_videos/<int:course_id>', methods=['GET'])
def get_course_videos(course_id):
    # Retrieve the course videos
    courses_videos = CourseVideo.query.filter_by(course_id=course_id).all()
    
    # Serialize the course videos into a list of dictionaries
    videos_list = [{
        'id': video.id,
        'filename': video.filename,
        'description': video.description
    } for video in courses_videos]

    # Return as JSON
    return jsonify(videos=videos_list)

@app.route('/delete_comment', methods=['POST'])
def delete_comment():
    user_id = session.get('user_id')  # Assuming user is logged in and their ID is stored in the session
    comment_id = request.json.get('comment_id')
    
    if not user_id or not comment_id:
        return jsonify({'success': False, 'message': 'User ID and Comment ID are required'}), 400

    comment = ReelComment.query.get(comment_id)

    if not comment or comment.user_id != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized or comment not found'}), 403

    db.session.delete(comment)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Comment deleted successfully'})

@app.route('/review_contents/<int:course_id>')
def review_contents(course_id):
    # Query the course resources and assignments based on the course_id
    course_resources = CourseResource.query.filter_by(course_id=course_id).all()
    course_assignments = CourseAssignment.query.filter_by(course_id=course_id).all()

    # Pass the resources and assignments to the template
    return render_template('review_contents.html', 
                           course_resources=course_resources, 
                           course_assignments=course_assignments)


@app.route('/comment_reel', methods=['POST'])
def comment_reel():
    user_id = session.get('user_id')  # Assume user is logged in and their ID is stored in the session
    reel_id = request.json.get('reel_id')
    comment_text = request.json.get('comment')

    if not user_id or not reel_id or not comment_text:
        return jsonify({'success': False, 'message': 'Reel ID, User ID, and comment text are required'}), 400

    # Create the comment
    new_comment = ReelComment(content=comment_text, reel_id=reel_id, user_id=user_id)
    db.session.add(new_comment)
    db.session.commit()

    return jsonify({'success': True, 'comment_id': new_comment.id})


@app.route('/share_reel', methods=['POST'])
def share_reel():
    reel_id = request.json.get('reel_id')
    if not reel_id:
        return jsonify({'success': False, 'message': 'Reel ID is required'}), 400

    reel = Reel.query.get(reel_id)
    if not reel:
        return jsonify({'success': False, 'message': 'Reel not found'}), 404

    reel.shares += 1
    db.session.commit()
    return jsonify({'success': True, 'shares': reel.shares})

@app.route('/upload_course_video', methods=['GET', 'POST'])
def upload_course_video():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form.get('category')
        uploader_id = session.get('user_id')
        course_length = request.form.get('course_length')  # New field

        # Handle thumbnail upload
        thumbnail_file = request.files.get('thumbnail')
        thumbnail_filename = None
        if thumbnail_file:
            thumbnail_filename = secure_filename(thumbnail_file.filename)
            thumbnail_path = os.path.join(app.config['COURSE_THUMBNAIL_FOLDER'], thumbnail_filename)
            thumbnail_file.save(thumbnail_path)

        # Save course details
        new_course = Course(
            title=title,
            description=description,
            category=category,
            uploader_id=uploader_id,
            thumbnail=thumbnail_filename,
            course_length=course_length 
           
        )
        db.session.add(new_course)
        db.session.commit()

        # Debugging: Check if resource files are processed
        for resource_file in request.files.getlist('resource_file[]'):
            if resource_file:
                resource_filename = secure_filename(resource_file.filename)
                resource_path = os.path.join(app.config['COURSE_RESOURCE_FOLDER'], resource_filename)
                resource_file.save(resource_path)  # Save file
                print(f"Saved resource file to: {resource_path}")  # Debugging

                new_resource = CourseResource(filename=resource_filename, course_id=new_course.id)
                db.session.add(new_resource)

        # Debugging: Check if assignment files are processed
        for assignment_file in request.files.getlist('assignment_file[]'):
            if assignment_file:
                assignment_filename = secure_filename(assignment_file.filename)
                assignment_path = os.path.join(app.config['COURSE_ASSIGNMENT_FOLDER'], assignment_filename)
                assignment_file.save(assignment_path)  # Save file
                print(f"Saved assignment file to: {assignment_path}")  # Debugging

                new_assignment = CourseAssignment(filename=assignment_filename, course_id=new_course.id)
                db.session.add(new_assignment)

        # Debugging: Check if instructor photos are processed
        instructor_names = request.form.getlist('instructor_name[]')
        profile_links = request.form.getlist('instructor_profile_link[]')
        fb_links = request.form.getlist('instructor_fb_link[]')
        linkedin_links = request.form.getlist('instructor_linkedin_link[]')
        instructor_photos = request.files.getlist('instructor_photo[]')

        for name, profile_link, fb_link, linkedin_link, photo in zip(
            instructor_names, profile_links, fb_links, linkedin_links, instructor_photos
        ):
            if photo:
                photo_filename = secure_filename(photo.filename)
                photo_path = os.path.join(app.config['COURSE_INSTRUCTOR_FOLDER'], photo_filename)
                photo.save(photo_path)  # Save file
                print(f"Saved instructor photo to: {photo_path}")  # Debugging

                instructor = CourseInstructor(
                    name=name,
                    profile_link=profile_link,
                    fb_link=fb_link,
                    linkedin_link=linkedin_link,
                    photo_filename=photo_filename,
                    course_id=new_course.id
                )
                db.session.add(instructor)

                video_titles = request.form.getlist('video_title[]')
                
        video_descriptions = request.form.getlist('video_description[]')
        video_files = request.files.getlist('video_file[]')
        
        for video_title, video_description, video_file in zip(video_titles, video_descriptions, video_files):
            if video_file:
                video_filename = secure_filename(video_file.filename)
                video_path = os.path.join(app.config['COURSE_VIDEO_FOLDER'], video_filename)
                video_file.save(video_path)
                print(f"Video saved to {video_path}")

                course_video = CourseVideo(
                    course_id=new_course.id,
                    title=video_title,
                    filename=video_filename,
                    description=video_description
                )
                db.session.add(course_video)

        db.session.commit()

        return redirect(url_for('courses'))

    return render_template('upload_course.html')


def is_valid_course_length(length):
    pattern = r"^\d{2}:\d{2}:\d{2}$"  # HH:MM:SS format
    return re.match(pattern, length) is not None

#def update_challenge_status():
    # Fetch all challenges with "In Progress" status
    in_progress_challenges = UserChallenge.query.filter_by(status='In Progress').all()
    current_datetime = datetime.now()

    for challenge in in_progress_challenges:
        challenge_datetime = datetime.combine(challenge.completion_date, challenge.completion_time)
        if current_datetime >= challenge_datetime:
            challenge.status = 'Course Completed'
            db.session.commit()

#@app.before_request
#ef before_request():
    update_challenge_status()















@app.route('/search_essays', methods=['GET', 'POST'])
def search_essays():
    essays = []  # Default empty list for essays
    search_query = ''  # Default empty search query

    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()

        if search_query:
            # Query the database for essays matching the topi
            flash('Please enter a topic to search.', 'error')

    return render_template('search_essays.html', essays=essays, search_query=search_query)



















@app.route('/like_video/<int:video_id>', methods=['POST'])
def like_video(video_id):
    if 'username' not in session:
        return 'Unauthorized', 401
    
    user = User.query.filter_by(username=session['username']).first()
    video = Video.query.get_or_404(video_id)

    existing_reaction = Reaction.query.filter_by(video_id=video_id, user_id=user.id, reaction_type='like').first()
    
    if not existing_reaction:
        new_reaction = Reaction(video_id=video_id, user_id=user.id, reaction_type='like')
        db.session.add(new_reaction)
        db.session.commit()
    
    return 'Liked', 200

@app.route('/server/<int:server_id>')
def server(server_id):
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get the current logged-in user
    current_user = User.query.filter_by(username=session['username']).first()

    # Get the server object
    server = Server.query.get_or_404(server_id)

    # Check if the user is a member of the server or the owner
    if current_user not in server.members and current_user != server.owner:
        return "Access Denied: You do not have permission to view this server.", 403

    # Render the server page if the user is a member or the owner
    return render_template('server.html', server=server, members=server.members)


def get_current_user():
    if 'username' in session:
        return User.query.filter_by(username=session['username']).first()
    return None

@app.before_request
def before_request():
    g.current_user = get_current_user()


@app.route('/course/<slug>')
def view_course(slug):
    course = Course.query.filter_by(slug=slug).first_or_404()

    # Fetch all videos associated with the course
    course_videos = CourseVideo.query.filter_by(course_id=course.id).all()

    # Fetch resources and assignments
    course_resources = CourseResource.query.filter_by(course_id=course.id).all()
    course_assignments = CourseAssignment.query.filter_by(course_id=course.id).all()

    # Fetch instructors
    course_instructors = CourseInstructor.query.filter_by(course_id=course.id).all()

    # Serialize course videos
    videos_list = [{
        'id': video.id,
        'title': video.title,
        'filename': video.filename,
        'description': video.description
    } for video in course_videos]

    # Fetch the current user (adjust this based on your session management)
    current_user = get_current_user()  # Ensure this function returns the current user

    # Fetch related courses based on the same category
    related_courses = Course.query.filter(Course.category == course.category).all()

    # Check if the current user has progress saved for this course
    progress = CourseProgress.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    remaining_time = progress.remaining_time if progress else course.course_length

    return render_template(
        'view_course.html',
        course=course,
        videos=videos_list,
        resources=course_resources,
        assignments=course_assignments,
        instructors=course_instructors,
        user=current_user,
        related_courses=related_courses,
        remaining_time=remaining_time,  # Pass remaining time for the timer
        progress=progress  # Pass progress for UI adjustments
    )






@app.route('/servers')
def servers():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()

    # Fetch servers the user owns and is a member of
    owned_servers = Server.query.filter_by(owner=user).all()
    joined_servers = Server.query.filter(Server.members.contains(user)).all()

    return render_template('servers.html', owned_servers=owned_servers, joined_servers=joined_servers)

@app.route('/my_courses')
def my_courses():
    return render_template('mycourses.html')

@app.route('/enrolled_courses')
def enrolled_courses():
    user_id = session.get('user_id')
    user = User.query.get_or_404(user_id)
    enrolled_courses = user.enrolled_courses  # Retrieve the user's enrolled courses
    return render_template('enrolled_courses.html', enrolled_courses=enrolled_courses)

@app.route('/made_courses')
def made_courses():
    user_id = session.get('user_id')
    made_courses = Course.query.filter_by(uploader_id=user_id).all()
    return render_template('made_courses.html', made_courses=made_courses)

@app.route('/enroll_in_course/<int:course_id>', methods=['POST', 'GET'])
def enroll_in_course(course_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    course = Course.query.get(course_id)

    if course not in user.enrolled_courses:
        user.enrolled_courses.append(course)
        db.session.commit()

    return redirect(url_for('enrolled_courses'))




@app.route('/server_feed/<int:server_id>', methods=['GET'])
def server_feed(server_id):
    user = User.query.filter_by(username=session['username']).first()
    server = Server.query.get_or_404(server_id)

    # Ensure user is a member or owner of the server
    if user not in server.members and user != server.owner:
        return "You are not allowed to access this server.", 403

    posts = ServerPost.query.filter_by(server_id=server.id).all()
    return render_template('server_feed.html', server=server, posts=posts)

# Make Post
@app.route('/server_post/<int:server_id>', methods=['GET', 'POST'])
def server_post(server_id):
    user = User.query.filter_by(username=session['username']).first()
    server = Server.query.get_or_404(server_id)

    # Ensure user is a member or owner of the server
    if user not in server.members and user != server.owner:
        return "You are not allowed to make posts in this server.", 403

    if request.method == 'POST':
        content = request.form.get('content')
        media_file = request.files.get('media_file')
        
        # Handle file upload
        if media_file:
            filename = secure_filename(media_file.filename)
            media_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            media_file.save(media_path)
            
            new_post = ServerPost(content=content, media_filename=filename, user_id=user.id, server_id=server.id)
        else:
            new_post = ServerPost(content=content, user_id=user.id, server_id=server.id)
        
        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for('server_feed', server_id=server.id))

    return render_template('server_post.html', server=server)






@app.route('/create_server', methods=['GET', 'POST'])
def create_server():
    if request.method == 'POST':
        server_name = request.form['server_name']
        owner_id = session.get('user_id')

        # Check if the user is logged in
        if not owner_id:
            return redirect(url_for('login'))

        # Create a new server and generate a unique code
        new_server = Server(name=server_name, owner_id=owner_id)
        new_server.generate_unique_code()

        db.session.add(new_server)
        db.session.commit()

        return redirect(url_for('servers'))  # Redirect to servers list

    return render_template('create_server.html')



@app.route('/join_server', methods=['POST'])
def join_server():
    if 'username' not in session:
        return redirect(url_for('login'))

    server_code = request.form['server_code']
    user = User.query.filter_by(username=session['username']).first()

    # Find the server with the entered code
    server = Server.query.filter_by(code=server_code).first()

    if server:
        # Check if the user is already a member of the server
        if user not in server.members:
            server.members.append(user)
            db.session.commit()
            return redirect(url_for('servers'))
        else:
            return 'You are already a member of this server.'
    else:
        return 'Invalid server code.'




@app.route('/server/<int:server_id>', methods=['GET'])
def view_server(server_id):
    server = Server.query.get_or_404(server_id)
    user = User.query.filter_by(username=session['username']).first()
    
    if user not in server.members:
        return redirect(url_for('servers'))  # Prevent non-members from viewing the server

    return render_template('server.html', server=server, user=user)


@app.route('/send_friend_request/<int:receiver_id>', methods=['POST'])
def send_friend_request(receiver_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    sender = User.query.filter_by(username=session['username']).first()
    receiver = User.query.get(receiver_id)

    if receiver and receiver != sender:
        existing_request = FriendRequest.query.filter_by(sender_id=sender.id, receiver_id=receiver.id).first()
        if not existing_request:
            friend_request = FriendRequest(sender_id=sender.id, receiver_id=receiver.id, status='pending')
            db.session.add(friend_request)
            db.session.commit()
            return f'Friend request sent to {receiver.username}!'
        else:
            return 'Friend request already sent.'
    
    return redirect(url_for('view_profile', user_id=receiver_id))

@app.route('/remove_friend/<int:friend_id>', methods=['POST'])
def remove_friend(friend_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    friend = User.query.get(friend_id)

    if not user or not friend:
        return redirect(url_for('friend_list'))

    # Remove the friend relationship
    if friend in user.friends:
        user.friends.remove(friend)
        friend.friends.remove(user)
        db.session.commit()

    return redirect(url_for('friend_list'))




@app.route('/give_star/<int:receiver_id>', methods=['POST'])
def give_star(receiver_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = User.query.filter_by(username=session['username']).first()
    receiver = User.query.get(receiver_id)

    # Check if the current user has already given a star to the receiver
    existing_star = Star.query.filter_by(giver_id=current_user.id, receiver_id=receiver.id).first()
    if existing_star:
        return jsonify({'status': 'already_given'}), 400  # Error: Already gave a star to this user

    # Add a new star
    receiver.stars_received += 1
    new_star = Star(giver_id=current_user.id, receiver_id=receiver.id)
    db.session.add(new_star)
    db.session.commit()

    return jsonify({'status': 'success'}), 200  # Success: Star given


#@app.route('/complete_course', methods=['POST'])
#def complete_course():
    data = request.get_json()
    user_id = data.get('user_id')
    course_id = data.get('course_id')

    # Fetch or create progress entry
    progress = CourseProgress.query.filter_by(user_id=user_id, course_id=course_id).first()
#    user_challenge = UserChallenge.query.filter_by(user_id=user_id, course_id=course_id).first()

    if progress:
        # Skip if challenge status is "Time Overdue"
        if user_challenge and user_challenge.status == "Time Overdue":
            return jsonify({'status': 'error', 'message': 'Challenge is overdue and cannot be completed'}), 403

        progress.remaining_time = "00:00:00"
        progress.is_completed = True  # Mark as completed
        db.session.commit()

        # Update challenge status if it exists and is not "Time Overdue"
        if user_challenge and user_challenge.status != "Time Overdue":
            user_challenge.status = "Completed"
            db.session.commit()

        return jsonify({'status': 'success', 'message': 'Course marked as completed'})
    else:
        return jsonify({'status': 'error', 'message': 'Progress not found'}), 404


@app.route('/create_group', methods=['POST'])
def create_group():
    if 'username' not in session:
        return redirect(url_for('login'))

    group_name = request.form.get('group_name')
    user = User.query.filter_by(username=session['username']).first()

    if group_name and user:
        new_group = Group(name=group_name)
        new_group.members.append(user)  # Add the creator to the group
        db.session.add(new_group)
        db.session.commit()
        return redirect(url_for('chat'))
    else:
        return "Error creating group", 400


@app.route('/remove_member_from_group', methods=['POST'])
def remove_member_from_group():
    data = request.json
    group_id = data.get('group_id')
    user_id = data.get('user_id')
    group = Group.query.get_or_404(group_id)
    user = User.query.get_or_404(user_id)
    if user in group.members:
        group.members.remove(user)
        db.session.commit()
        return '', 200
    return '', 400

# Route to send a request for LOR
@app.route('/request_lor/<int:receiver_id>', methods=['POST'])
def request_lor(receiver_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    sender = User.query.filter_by(username=session['username']).first()
    receiver = User.query.get(receiver_id)

    if not receiver or receiver == sender:
        return redirect(url_for('search'))

    # Check if the LOR request already exists
    existing_request = HelperRequest.query.filter_by(sender_id=sender.id, receiver_id=receiver.id, helper_type='lor').first()
    if not existing_request:
        # Create a new LOR request
        new_request = HelperRequest(sender_id=sender.id, receiver_id=receiver.id, helper_type='lor', status='pending')
        db.session.add(new_request)
        db.session.commit()
        return f'LOR request sent to {receiver.username}!'
    else:
        return 'LOR request already sent.'

# Route to send a request for Counsel
@app.route('/request_counsel/<int:receiver_id>', methods=['POST'])
def request_counsel(receiver_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    sender = User.query.filter_by(username=session['username']).first()
    receiver = User.query.get(receiver_id)

    if not receiver or receiver == sender:
        return redirect(url_for('search'))

    # Check if the Counsel request already exists
    existing_request = HelperRequest.query.filter_by(sender_id=sender.id, receiver_id=receiver.id, helper_type='counsel').first()
    if not existing_request:
        # Create a new Counsel request
        new_request = HelperRequest(sender_id=sender.id, receiver_id=receiver.id, helper_type='counsel', status='pending')
        db.session.add(new_request)
        db.session.commit()
        return f'Counsel request sent to {receiver.username}!'
    else:
        return 'Counsel request already sent.'

@app.route('/ai_search', methods=['GET', 'POST'])
def ai_search():
    return redirect("https://collegerecommender.netlify.app/")

    






























#-----------------------------------------------WEBINAR----------------------------------------------
#-----------------------------------------------WEBINAR----------------------------------------------
#-----------------------------------------------WEBINAR----------------------------------------------
#-----------------------------------------------WEBINAR----------------------------------------------
#-----------------------------------------------WEBINAR----------------------------------------------

@app.route('/get_friends', methods=['GET'])
def get_friends():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    friends = user.friends.all()  # Assuming User has a 'friends' relationship
    return jsonify(friends=[{'username': friend.username} for friend in friends])


@app.route('/send_reel', methods=['POST'])
def send_reel():
    data = request.json
    reel_slug = data['reel_id']
    friends_usernames = data['friends_usernames']  # Receive an array of friend usernames
    
    # Get the reel by its slug
    reel = Reel.query.filter_by(slug=reel_slug).first()
    
    if not reel:
        return jsonify(success=False, message='Reel not found'), 404

    # Send the reel to each friend
    for friend_username in friends_usernames:
        friend = User.query.filter_by(username=friend_username).first()
        if friend:
            send_reel_to_friend(reel.id, friend.id)  # Use the same function to send the reel

    return jsonify(success=True)

def send_reel_to_friend(reel_id, friend_id):
    # Fetch the reel by its ID to get the slug
    reel = Reel.query.get(reel_id)
    
    if reel:
        # Use slug for the URL instead of reel_id
        reel_url = url_for('view_single_reel', slug=reel.slug, _external=True)
        
        # Get the current user (sender)
        sender_id = session.get('user_id')
        
        # Create a message with the reel link
        message_content = f"Check out this reel: {reel_url}"

        # Add the message to the database
        new_message = PrivateMessage(
            sender_id=sender_id,
            receiver_id=friend_id,
            content=message_content
        )
        
        db.session.add(new_message)
        db.session.commit()

        return True
    return False  # Handle the case where the reel wasn't found



@app.route('/reel/<slug>')
def view_single_reel(slug):
    user_id = session.get('user_id')
    reel = Reel.query.filter_by(slug=slug).first_or_404()

    if reel.visibility == 'Private' and reel.user_id != user_id:
        return "This reel is private.", 403

    if reel.visibility == 'Friends' and reel.user_id != user_id:
        user = User.query.get(user_id)
        if user_id not in [friend.id for friend in user.friends]:
            return "This reel is only visible to friends.", 403

    is_liked = False
    if user_id:
        user = User.query.get(user_id)
        is_liked = reel in user.liked_reels

    reel_data = {
        'id': reel.id,
        'title': reel.title,
        'description': reel.description,
        'filename': reel.filename,
        'likes': reel.likes,
        'shares': reel.shares,
        'comments_count': len(reel.comments),
        'is_liked': is_liked,
        'visibility': reel.visibility,
        'uploader_id': reel.user_id,
    }

    return render_template('single_reel.html', reel=reel_data)












# Route to send a request for Mentorship
@app.route('/request_mentorship/<int:receiver_id>', methods=['POST'])
def request_mentorship(receiver_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    sender = User.query.filter_by(username=session['username']).first()
    receiver = User.query.get(receiver_id)

    if not receiver or receiver == sender:
        return redirect(url_for('search'))

    # Check if the Mentorship request already exists
    existing_request = HelperRequest.query.filter_by(sender_id=sender.id, receiver_id=receiver.id, helper_type='mentorship').first()
    if not existing_request:
        # Create a new Mentorship request
        new_request = HelperRequest(sender_id=sender.id, receiver_id=receiver.id, helper_type='mentorship', status='pending')
        db.session.add(new_request)
        db.session.commit()
        return f'Mentorship request sent to {receiver.username}!'
    else:
        return 'Mentorship request already sent.'

@app.route('/mentors')
def mentors():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    # Fetch mentorship requests
    sent_requests = HelperRequest.query.filter_by(sender_id=user.id, helper_type='mentorship').all()
    received_requests = HelperRequest.query.filter_by(receiver_id=user.id, helper_type='mentorship').all()

    # Fetch existing mentorships
    mentorships_as_mentor = Mentorship.query.filter_by(mentor_id=user.id).all()
    mentorships_as_mentee = Mentorship.query.filter_by(mentee_id=user.id).all()

    # Collect user IDs involved in existing mentorships
    mentorship_user_ids = {m.mentee_id for m in mentorships_as_mentor} | {m.mentor_id for m in mentorships_as_mentee}

    return render_template('mentors.html', 
                           sent_requests=sent_requests, 
                           received_requests=received_requests,
                           mentorships_as_mentor=mentorships_as_mentor,
                           mentorships_as_mentee=mentorships_as_mentee,
                           mentorship_user_ids=mentorship_user_ids, now=date.today())


@app.route('/handle_mentorship_request/<int:request_id>', methods=['POST'])
def handle_mentorship_request(request_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    action = request.json.get('action')
    mentorship_request = HelperRequest.query.get(request_id)

    if mentorship_request and mentorship_request.receiver_id == User.query.filter_by(username=session['username']).first().id:
        if action == 'accept':
            mentorship_request.status = 'accepted'
        elif action == 'reject':
            mentorship_request.status = 'rejected'
        db.session.commit()
        return '', 200
    return '', 400



@app.route('/webinar')
def webinar():
    return render_template('webinar.html')

# Example route to handle POST requests for creating a webinar
@app.route('/create_webinar', methods=['GET', 'POST'])
def create_webinar():
    if request.method == 'POST':
        # Handle the form submission and create a new webinar
        current_user = User.query.get(1)  # Replace with session user ID or logged-in user

        if not current_user:
            flash("Please log in to create a webinar.", "danger")
            return redirect(url_for('login'))

        new_webinar = Webinar(
            title=request.form['webinar_name'],
            description=request.form['description'],
            webinar_id=request.form.get('webinar_id'),
            duration=int(request.form['webinar_duration']),
            meeting_type=request.form['meeting_type'],
            date=request.form['date'],
            time=request.form['time'],
            link=request.form['webinar_link'],
            creator=current_user
        )

        try:
            db.session.add(new_webinar)
            db.session.commit()
            flash("Webinar created successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating webinar: {str(e)}", "danger")
        
        return redirect(url_for('join_webinar'))

    # If it's a GET request, render the form
    return render_template('create_webinar.html')

@app.route('/set_mentorship_relation/<int:request_id>', methods=['POST'])
def set_mentorship_relation(request_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    data = request.get_json()
    relation = data.get('relation')  # 'mentor' or 'mentee'

    user = User.query.filter_by(username=session['username']).first()
    mentorship_request = HelperRequest.query.get(request_id)

    if not mentorship_request or mentorship_request.status != 'accepted':
        return 'Invalid request', 400

    if relation not in ['mentor', 'mentee']:
        return 'Invalid relation', 400

    # Determine the other user's ID
    if user.id == mentorship_request.sender_id:
        other_user_id = mentorship_request.receiver_id
    else:
        other_user_id = mentorship_request.sender_id

    # Check if mentorship already exists
    existing_mentorship = Mentorship.query.filter(
        ((Mentorship.mentor_id == user.id) & (Mentorship.mentee_id == other_user_id)) |
        ((Mentorship.mentor_id == other_user_id) & (Mentorship.mentee_id == user.id))
    ).first()

    if existing_mentorship:
        return 'Mentorship already established', 400

    # Establish mentorship based on selected relation
    if relation == 'mentor':
        mentor_id = user.id
        mentee_id = other_user_id
    else:  # 'mentee'
        mentor_id = other_user_id
        mentee_id = user.id

    # Create the mentorship
    new_mentorship = Mentorship(mentor_id=mentor_id, mentee_id=mentee_id)
    db.session.add(new_mentorship)
    db.session.commit()

    return 'Relation set successfully', 200


@app.route('/save_webinar', methods=['POST'])
def save_webinar():
    webinar_name = request.form['webinar_name']
    description = request.form['description']
    webinar_link = request.form['webinar_link']
    date = request.form['date']
    time = request.form['time']
    
    # Logic to save webinar details goes here

    return redirect(url_for('public_feed'))  # Redirect to the public feed after saving


@app.route('/join_webinar')
def join_webinar():
    # Fetch actual webinars from the database
    webinars = Webinar.query.all()
    return render_template('join_webinar.html', webinars=webinars)


@app.route('/about_webinar/<int:webinar_id>')
def about_webinar(webinar_id):
    webinar = Webinar.query.get_or_404(webinar_id)  # Fetch webinar by ID, or show 404 error if not found
    creator_username = webinar.creator.username  # Access the username through the relationship

    return render_template('about_webinar.html', webinar=webinar, creator_username=creator_username)






#-----------------------------------------------WEBINAR----------------------------------------------
#-----------------------------------------------WEBINAR----------------------------------------------
#-----------------------------------------------WEBINAR----------------------------------------------
#-----------------------------------------------WEBINAR----------------------------------------------
#-----------------------------------------------WEBINAR----------------------------------------------









































































@app.route('/helpers_section')
def helpers_section():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Filter only LOR and Counsel requests where the current user is the sender or receiver
    sent_requests = HelperRequest.query.filter_by(sender_id=user_id).filter(HelperRequest.helper_type.in_(['lor', 'counsel'])).all()
    received_requests = HelperRequest.query.filter_by(receiver_id=user_id).filter(HelperRequest.helper_type.in_(['lor', 'counsel'])).all()
    
    return render_template('helpers_section.html', sent_requests=sent_requests, received_requests=received_requests)


# Route to handle response to LOR or Counsel requests
@app.route('/respond_helper_request/<int:request_id>/<response>', methods=['POST'])
def respond_helper_request(request_id, response):
    if 'username' not in session:
        return redirect(url_for('login'))

    helper_request = HelperRequest.query.get_or_404(request_id)
    
    if response == 'accept':
        helper_request.status = 'accepted'
    else:
        helper_request.status = 'declined'

    db.session.commit()
    return redirect(url_for('helpers_section'))




@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        
        if request.method == 'POST':
            # Update user information
            user.sat_score = request.form['sat_score']
            user.eca = request.form['eca']
            user.essay = request.form['essay']
            user.major_subject = request.form['major_subject']  # Major
            user.minor_subject = request.form['minor_subject']  # Minor
            
            # Handle profile picture upload
            if 'profile_pic' in request.files:
                profile_pic = request.files['profile_pic']
                
                if profile_pic and allowed_file(profile_pic.filename):
                    filename = secure_filename(profile_pic.filename)
                    # Save the file in the designated folder
                    profile_pic.save(os.path.join(app.config['PROFILE_FOLDER'], filename))
                    # Update user profile picture
                    user.profile_pic = filename
                else:
                    flash("Invalid file type. Please upload a .png, .jpg, or .jpeg file", "error")
            
            # Commit the changes
            db.session.commit()
            return redirect(url_for('profile'))
        
        return render_template('edit_profile.html', user=user)
    
    return redirect(url_for('login'))



@app.route('/group_members/<int:group_id>', methods=['GET'])
def group_members(group_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    group = Group.query.get_or_404(group_id)
    user = User.query.filter_by(username=session['username']).first()

    if user not in group.members:
        return "You are not a member of this group", 403

    members = group.members  # Fetch the group members
    return render_template('group_members.html', group=group, members=members)


@app.route('/friend_requests', methods=['GET', 'POST'])
def view_friend_requests():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('login'))

    # Fetch all pending friend requests received by the user
    received_requests = FriendRequest.query.filter_by(receiver_id=user.id, status='pending').all()

    # Fetch all friend requests sent by the user
    sent_requests = FriendRequest.query.filter_by(sender_id=user.id, status='pending').all()

    if request.method == 'POST':
        request_id = request.form.get('request_id')
        action = request.form.get('action')

        friend_request = FriendRequest.query.get(request_id)
        if friend_request and friend_request.receiver_id == user.id:
            if action == 'accept':
                friend_request.status = 'accepted'
                # Add both users as friends
                sender = User.query.get(friend_request.sender_id)
                if sender not in user.friends:
                    user.friends.append(sender)
                if user not in sender.friends:
                    sender.friends.append(user)
                db.session.commit()
            elif action == 'decline':
                friend_request.status = 'declined'
                db.session.commit()

        return redirect(url_for('view_friend_requests'))

    return render_template('friend_requests.html', received_requests=received_requests, sent_requests=sent_requests)



@app.route('/view_friends')
def view_friends():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    friends_list = user.friends.all()  # Fetch all friends

    return render_template('friends_list.html', friends=friends_list)



@app.route('/search_user')
def search_user():
    query = request.args.get('query')
    users = User.query.filter(User.username.ilike(f'%{query}%')).all()
    return jsonify({'users': [{'id': user.id, 'username': user.username} for user in users]})

@app.route('/get_user_profile/<int:user_id>')
def get_user_profile(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({'id': user.id, 'username': user.username, 'email': user.email, 'profile_pic': user.profile_pic or 'default.jpg'})



@app.route('/add_member_to_group', methods=['POST'])
def add_member_to_group():
    data = request.json
    group_id = data.get('group_id')
    user_id = data.get('user_id')
    group = Group.query.get_or_404(group_id)
    user = User.query.get_or_404(user_id)
    if user not in group.members:
        group.members.append(user)
        db.session.commit()
        return '', 200
    return '', 400





@app.route('/respond_friend_request/<int:request_id>/<response>', methods=['POST'])
def respond_friend_request(request_id, response):
    if 'username' not in session:
        return redirect(url_for('login'))

    friend_request = FriendRequest.query.get_or_404(request_id)
    if response == 'accept':
        friend_request.status = 'accepted'
        # Add both users as friends
        sender = User.query.get(friend_request.sender_id)
        receiver = User.query.get(friend_request.receiver_id)
        if sender not in receiver.friends:
            receiver.friends.append(sender)
        if receiver not in sender.friends:
            sender.friends.append(receiver)
    else:
        friend_request.status = 'declined'

    db.session.commit()
    return redirect(url_for('view_friend_requests'))




@app.route('/reels', methods=['GET', 'POST'])
def reels():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    reels = Reel.query.order_by(Reel.id.desc()).all()

    return render_template('reels.html', user=user, reels=reels)

from random import choices  # Ensure this import is present


@app.route('/upload_reel', methods=['GET', 'POST'])
def upload_reel():
    if request.method == 'POST':
        # Process the uploaded file and form data
        if 'reel_file' not in request.files:
            return "No file part", 400

        file = request.files['reel_file']
        if file.filename == '':
            return "No selected file", 400

        if file:
            # Securely save the file
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['REEL_FOLDER'], filename))

            # Get form data
            title = request.form.get('title')
            description = request.form.get('description')
            tags = request.form.get('tags')
            visibility = request.form.get('visibility')  # 'Public', 'Friends'
            user_id = session.get('user_id')  # Get the current user's ID

            # Save the reel to the database
            new_reel = Reel(title=title, description=description, filename=filename, tags=tags, visibility=visibility, user_id=user_id)
            new_reel.generate_slug()  # Generate unique slug
            db.session.add(new_reel)
            db.session.commit()

            return "Reel uploaded successfully", 200

    # If GET request, render the upload form
    return render_template('upload_reel.html')



import math
from random import shuffle

@app.route('/public_feed')
def public_feed():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Retrieve the user
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('login'))

    # Retrieve all posts ordered by creation time (newest first)
    posts = Post.query.order_by(Post.timestamp.desc()).all()

    # Retrieve videos and separate them by visibility
    videos = Video.query.order_by(Video.id.desc()).all()  # Order videos by upload time (latest first)
    public_videos = [video for video in videos if video.privacy == 'public']
    friends_videos = [video for video in videos if video.privacy == 'friends' and video.uploader in user.friends]
    user_videos = [video for video in videos if video.uploader_id == user.id]
    visible_videos = list({video.id: video for video in public_videos + friends_videos + user_videos}.values())

    # Determine the number of chunks and shuffle videos
    total_videos = len(visible_videos)
    if total_videos <= 10:
        num_chunks = 5
    elif total_videos <= 100:
        num_chunks = 10
    else:
        num_chunks = 50
    videos_per_chunk = max(1, math.ceil(total_videos / num_chunks))
    chunks = [visible_videos[i:i + videos_per_chunk] for i in range(0, total_videos, videos_per_chunk)]
    for chunk in chunks:
        shuffle(chunk)

    # Retrieve friend requests
    received_requests = FriendRequest.query.filter_by(receiver_id=user.id, status='pending').all()

    # Retrieve courses
    courses = Course.query.order_by(Course.upload_time.desc()).all()

    # Set user's profile picture
    user_profile_pic = user.profile_pic if user.profile_pic else 'default.jpg'
    # Path to the uploads directory
    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'])
    
    # List all image files in the uploads directory
    image_files = []
    if os.path.exists(upload_dir):
        image_files = [
            file for file in os.listdir(upload_dir) 
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))
        ]
    

    

    # Render the feed template
    return render_template(
        'public_feed.html',
        user=user,
        user_profile_pic=user_profile_pic,
        posts=posts,
        visible_videos=chunks,  # Pass shuffled video chunks
        received_requests=received_requests,
        courses=courses,
        manyimages=image_files,
        
    )



@app.route('/get_reaction_users/<int:video_id>/<reaction_type>', methods=['GET'])
def get_reaction_users(video_id, reaction_type):
    reactions = Reaction.query.filter_by(video_id=video_id, reaction_type=reaction_type).all()
    users = [{'username': reaction.user.username} for reaction in reactions]
    return jsonify({'users': users})

@app.route('/post/<unique_id>')
def view_video_by_unique_id(unique_id):
    video = Video.query.filter_by(unique_id=unique_id).first_or_404()
    user_id = session.get('user_id')
    user = User.query.get(user_id)


    return render_template('view_video.html', video=video)


@app.route('/upload_video', methods=['GET', 'POST'])
def upload_video():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        tags = request.form['tags']
        privacy = request.form.get('privacy', 'public')
        video_file = request.files['video_file']

        # Validate form inputs
        if not title or not description or not video_file:
            flash('All fields are required.')
            return redirect(url_for('upload_video'))
        
        if not allowed_file(video_file.filename):
            flash('Invalid file type. Please upload a video file.')
            return redirect(url_for('upload_video'))

        # Ensure the directory for videos exists
        video_dir = app.config['VIDEOS_FOLDER']
        if not os.path.exists(video_dir):
            os.makedirs(video_dir)

        # Save the uploaded video file with a unique filename
        original_filename = secure_filename(video_file.filename)
        unique_filename = f"{uuid4().hex}_{original_filename}"
        video_path = os.path.join(video_dir, unique_filename)
        video_file.save(video_path)

        # Save video details to the database
        uploader = User.query.filter_by(username=session['username']).first()
        new_video = Video(
            title=title,
            description=description,
            filename=unique_filename,
            category=category,
            uploader_id=uploader.id,
            tags=tags,
            privacy=privacy
        )
        try:
            db.session.add(new_video)
            db.session.commit()
            return redirect(url_for('view_video_by_unique_id', unique_id=new_video.unique_id))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while saving the video. Please try again.')
            return redirect(url_for('upload_video'))
    
    return render_template('upload_video.html')



@app.route('/friend_list')
def friend_list():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch the current logged-in user
    user = User.query.filter_by(username=session['username']).first()
    
    if not user:
        return redirect(url_for('login'))

    friends = user.friends.all()  # Fetch all friends of the current user

    # Pass the user object along with the list of friends to the template
    return render_template('friend_list.html', user=user, friends=friends)


@app.route('/upload_photo', methods=['GET', 'POST'])
def upload_photo():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        photo_file = request.files['photo_file']
        if photo_file:
            # Directory to save uploaded photos
            upload_dir = app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            # Save the uploaded file securely
            filename = secure_filename(photo_file.filename)
            photo_path = os.path.join(upload_dir, filename)
            photo_file.save(photo_path)
            
            # Redirect to public_feed after upload
            return redirect(url_for('public_feed'))
    
    return render_template('upload_photo.html')


@app.route('/react_video/<int:video_id>', methods=['POST'])
def react_video(video_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 403

    data = request.get_json()
    reaction_type = data.get('reaction_type')
    if reaction_type not in ['like', 'love', 'haha']:
        return jsonify({'status': 'error', 'message': 'Invalid reaction type'}), 400

    existing_reaction = Reaction.query.filter_by(video_id=video_id, user_id=user_id).first()

    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            db.session.delete(existing_reaction)  # Toggle off
        else:
            existing_reaction.reaction_type = reaction_type  # Change reaction type
            db.session.add(existing_reaction)
    else:
        new_reaction = Reaction(video_id=video_id, user_id=user_id, reaction_type=reaction_type)
        db.session.add(new_reaction)

    db.session.commit()  # Save changes to database

    # Fetch the updated counts directly from the database
    like_count = Reaction.query.filter_by(video_id=video_id, reaction_type='like').count()
    love_count = Reaction.query.filter_by(video_id=video_id, reaction_type='love').count()
    haha_count = Reaction.query.filter_by(video_id=video_id, reaction_type='haha').count()

    return jsonify({
        'status': 'success',
        'reactions': {
            'like': like_count,
            'love': love_count,
            'haha': haha_count
        },
        'user_reaction': reaction_type
    })





@app.route('/share_video/<int:video_id>', methods=['POST'])
def share_video(video_id):
    if 'username' not in session:
        return jsonify({'status': 'unauthorized'}), 401

    user = User.query.filter_by(username=session['username']).first()
    video = Video.query.get(video_id)

    # Create a new video entry as a "shared" post
    shared_video = Video(
        title=f"Shared: {video.title}",
        description=video.description,
        filename=video.filename,  # Use the same video file
        uploader_id=user.id,
        category=video.category,
        tags=video.tags,
        thumbnail=video.thumbnail,
        privacy=video.privacy
    )
    db.session.add(shared_video)
    db.session.commit()

    return jsonify({'status': 'success'}), 200


@app.route('/comment_video/<int:video_id>', methods=['POST'])
def comment_video(video_id):
    if 'username' not in session:
        return 'Unauthorized', 401

    user = User.query.filter_by(username=session['username']).first()
    comment_content = request.json.get('comment')
    new_comment = Comment(video_id=video_id, user_id=user.id, content=comment_content)
    db.session.add(new_comment)
    db.session.commit()

    # Emit the update to all connected clients
    comment_count = Comment.query.filter_by(video_id=video_id).count()
    socketio.emit('update_comments', {'video_id': video_id, 'comment_count': comment_count})

    return jsonify({'status': 'success'}), 200


@app.route('/view_video/<int:video_id>')
def view_video(video_id):
    # Fetch the video details from the database using the video_id
    video = Video.query.get(video_id)
    if not video:
        abort(404)  # Return a 404 error if the video is not found

    # Fetch the uploader (the user who uploaded the video)
    uploader = User.query.get(video.uploader_id)
    if not uploader:
        uploader = None  # Handle case if uploader is not found

    # Optionally, fetch comments associated with the video
    comments = Comment.query.filter_by(video_id=video.id).all()

    # Render the video details, uploader, and comments in the template
    return render_template('view_video.html', video=video, uploader=uploader, comments=comments)


@app.route('/notifications')
def notifications():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    # Fetch notifications for the user
    user_notifications = Notification.query.filter_by(user_id=user.id).all()

    return render_template('notifications.html', notifications=user_notifications)


@app.route('/logout')
def logout():
    # Clear the session to log out the user
    session.clear()
    return redirect(url_for('login'))



@app.route('/search', methods=['POST'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search_query = request.form.get('search_query', '').strip()
    user_id = session['user_id']
    
    # Perform search for users excluding self
    results = User.query.filter(User.username.ilike(f"%{search_query}%")).filter(User.id != user_id).all()

    # Retrieve all helper requests (LOR, Counsel, Mentorship) involving the current user
    helper_requests = HelperRequest.query.filter(
        ((HelperRequest.sender_id == user_id) | (HelperRequest.receiver_id == user_id)) &
        (HelperRequest.helper_type.in_(['lor', 'counsel', 'mentorship']))
    ).all()

    # Organize requests by user and type for easy lookup in the template
    requests_status = {}
    for user_request in helper_requests:  # Renamed `request` to `user_request`
        other_user_id = user_request.receiver_id if user_request.sender_id == user_id else user_request.sender_id
        if other_user_id not in requests_status:
            requests_status[other_user_id] = {}
        requests_status[other_user_id][user_request.helper_type] = {
            'status': user_request.status,
            'is_sender': user_request.sender_id == user_id
        }

    return render_template('search.html', results=results, requests_status=requests_status)



@app.route('/save_mentorship_dates/<int:mentorship_id>', methods=['POST'])
def save_mentorship_dates(mentorship_id):
    data = request.get_json()
    start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
    
    mentorship = Mentorship.query.get(mentorship_id)
    mentorship.start_date = start_date
    mentorship.end_date = end_date
    db.session.commit()
    
    return jsonify({'status': 'success'}), 200


@app.route('/counsel_request/<int:receiver_id>', methods=['POST'])
def counsel_request(receiver_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    sender = User.query.filter_by(username=session['username']).first()
    receiver = User.query.get(receiver_id)

    if receiver and receiver != sender:
        # Logic to handle counsel request
        # You can implement the logic to store the request or notify the user here
        return f'Counsel request sent to {receiver.username}!', 200
    return redirect(url_for('search'))


@app.route('/profile/<int:user_id>', methods=['GET', 'POST'])
def view_profile(user_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    current_user = User.query.filter_by(username=session['username']).first()
    
    # Check if the profile being viewed is the current logged-in user's profile
    is_current_user = (current_user.id == user.id)
    
    # Handle form submission for actions like adding a friend or giving a star
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_friend':
            if user not in current_user.friends:
                current_user.friends.append(user)
                db.session.commit()
                session['friends'] = [friend.username for friend in current_user.friends]
        elif action == 'give_star':
            if current_user not in user.star_givers:
                user.stars_received += 1
                user.star_givers.append(current_user)
                db.session.commit()
            else:
                flash('You have already given a star to this user.', 'error')
    
    # Check if the profile user is a friend of the current user
    is_friend = user in current_user.friends

    # Assign a default profile picture if the user hasn't uploaded one
    user_profile_pic = user.profile_pic if user.profile_pic else 'default.jpg'

    return render_template('profile.html', 
                           user=user, 
                           is_current_user=is_current_user, 
                           is_friend=is_friend, 
                           user_profile_pic=user_profile_pic)



@app.route('/group_chat/<int:group_id>', methods=['GET', 'POST'])
def group_chat(group_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    group = Group.query.get_or_404(group_id)
    user = User.query.filter_by(username=session['username']).first()


    if request.method == 'POST':
        message_content = request.form.get('message')
        if message_content:
            new_message = Message(content=message_content, user_id=user.id, group_id=group.id)
            db.session.add(new_message)
            db.session.commit()

    return render_template('group_chat.html', group=group)



@socketio.on('send_group_message')
def handle_group_message(data):
    group_id = data['group_id']
    message = data['message']
    username = session.get('username')

    # Save message in the database
    group = Group.query.get(group_id)
    if group:
        user = User.query.filter_by(username=username).first()
        new_message = Message(content=message, user_id=user.id, group_id=group_id)
        db.session.add(new_message)
        db.session.commit()

    # Emit the message to all users in the group room
    room = f'group_{group_id}'
    socketio.emit('new_group_message', {
        'username': username,
        'message': message,
        'timestamp': new_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    }, room=room)
# app.py

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    webinars = Webinar.query.filter_by(user_id=user_id).all()  # Fetch webinars hosted by this user
    return render_template('view_profile.html', user=user, webinars=webinars)


@app.route('/delete_video/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    if 'username' not in session:
        return 'Unauthorized', 401
    
    user = User.query.filter_by(username=session['username']).first()
    video = Video.query.get_or_404(video_id)

    if video.uploader_id != user.id:
        return 'Unauthorized to delete this video', 403

    # Delete the video from the database
    db.session.delete(video)
    db.session.commit()

    return 'Video deleted successfully', 200

@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
def private_chat(user_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = User.query.filter_by(username=session['username']).first()
    chat_user = User.query.get_or_404(user_id)

    room = f'private_{min(current_user.id, chat_user.id)}_{max(current_user.id, chat_user.id)}'

    # Check if a message is sent
    if request.method == 'POST':
        message_content = request.form['message']
        print("\n\n\n\n\n\n", message_content , "\n\n\n\n\n\n")
        if message_content:
            # Save the new message to the database
            new_message = Message(
                content=message_content,
                sender_id=current_user.id,
                receiver_id=chat_user.id
            )
            db.session.add(new_message)
            db.session.commit()
            
            print("\n\n\n\n\n" , new_message , "\n\n\n\n\n")    
            # Send the message to the recipient in real-time using SocketIO
            socketio.emit('receive_private_message', {
                'sender': current_user.username,
                'message': message_content,
                'timestamp': new_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'room': room
            }, room=room)

    # Retrieve all private messages between the two users
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == chat_user.id)) |
        ((Message.sender_id == chat_user.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp).all()

    return render_template('private_chat.html', current_user=current_user, chat_user=chat_user, messages=messages, room=room)


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch the latest user data from the database
    user = User.query.filter_by(username=session['username']).first() 

    # Ensure session['friends'] is initialized
    if 'friends' not in session:
        session['friends'] = [friend.username for friend in user.friends]

    # Fetch user's friends
    friends = User.query.filter(User.username.in_(session['friends'])).all()  
    # Fetch all videos for simplicity
    videos = Video.query.order_by(Video.id.desc()).all()  

    # Handle None values to prevent TypeError
    user_profile_pic = user.profile_pic if user.profile_pic else 'default.jpg'
    user_gpa_class_9 = user.gpa_class_9 if user.gpa_class_9 else 'Not provided'
    user_gpa_class_10 = user.gpa_class_10 if user.gpa_class_10 else 'Not provided'
    user_gpa_class_11 = user.gpa_class_11 if user.gpa_class_11 else 'Not provided'
    user_gpa_class_12 = user.gpa_class_12 if user.gpa_class_12 else 'Not provided'
    user_sat_score = user.sat_score if user.sat_score else 'Not provided'
    user_gpa = user.gpa if user.gpa else 'Not provided'
    user_eca = user.eca if user.eca else 'Not provided'
    user_essay = user.essay if user.essay else 'Not provided'
    universities_to_apply = user.universities_to_apply if user.universities_to_apply else 'Not provided'
    universities_applied = user.universities_applied if user.universities_applied else 'Not provided'
    universities_studying = user.universities_studying if user.universities_studying else 'Not provided'

    # Render the dashboard template with all user data
    return render_template('dashboard.html', user=user, friends=friends, videos=videos, 
                           user_profile_pic=user_profile_pic, user_gpa_class_9=user_gpa_class_9,
                           user_gpa_class_10=user_gpa_class_10, user_gpa_class_11=user_gpa_class_11,
                           user_gpa_class_12=user_gpa_class_12, user_sat_score=user_sat_score,
                           user_gpa=user_gpa, user_eca=user_eca, user_essay=user_essay,
                           universities_to_apply=universities_to_apply, universities_applied=universities_applied,
                           universities_studying=universities_studying)


@app.route('/add_friend/<int:friend_id>', methods=['POST'])
def add_friend(friend_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    friend = User.query.get(friend_id)

    if friend and friend not in user.friends:
        user.friends.append(friend)
        db.session.commit()

    return redirect(url_for('view_profile', user_id=friend_id))



@socketio.on('join')
def on_join(room):
    username = session['username']
    join_room(room)
    if room not in users_in_rooms:
        users_in_rooms[room] = []
    users_in_rooms[room].append(username)

    # Remove the send message here to stop broadcasting the system message
    # socketio.emit('newMessage', {'username': 'System', 'text': f'{username} has joined the room.'}, room=room)

    # Emit updated user list without sending a message to the chat
    socketio.emit('updateUsersList', users_in_rooms[room], room=room)


@socketio.on('leave')
def on_leave(room):
    username = session['username']
    leave_room(room)
    users_in_rooms[room].remove(username)

    # Remove the send message here to stop broadcasting the system message
    # socketio.emit('newMessage', {'username': 'System', 'text': f'{username} has left the room.'}, room=room)

    # Emit updated user list without sending a message to the chat
    socketio.emit('updateUsersList', users_in_rooms[room], room=room)

@socketio.on('send_private_message')
def handle_private_message(data):
    room = data['room']
    message_content = data['message']
    sender = session['username']

    # Get the current user (sender)
    current_user = User.query.filter_by(username=sender).first()

    # Find the chat recipient based on the room identifier
    # You can extract recipient_id from the room name or pass it explicitly
    room_users = room.split('_')[1:]  # Get user ids from room name
    recipient_id = room_users[1] if str(current_user.id) == room_users[0] else room_users[0]
    recipient = User.query.get(recipient_id)

    # Save the new message to the database
    new_message = PrivateMessage(
        content=message_content,
        sender_id=current_user.id,
        receiver_id=recipient.id
    )
    db.session.add(new_message)
    db.session.commit()

    # Send the message to both users in real-time
    socketio.emit('receive_private_message', {
        'sender': current_user.username,
        'message': message_content,
        'timestamp': new_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'room': room
    }, room=room)


@app.route('/server/<int:server_id>/chat', methods=['GET'])
def server_chat(server_id):
    server = Server.query.get_or_404(server_id)
    user = User.query.filter_by(username=session['username']).first()

    chat_history = ChatMessage.query.filter_by(server_id=server_id).order_by(ChatMessage.timestamp).all()

    print("\n\n\n" , chat_history , "\n\n\n")

    return render_template('server_chat.html', server=server, user=user, chat_history=chat_history)
    

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    # Get the post content from the form
    content = request.form.get('content')

    if not content:
        flash("Post content cannot be empty.", "error")
        return redirect(url_for('public_feed'))

    # Create a new post and save it to the database
    new_post = Post(content=content, user_id=user.id)
    db.session.add(new_post)
    db.session.commit()

    flash("Your post has been created!", "success")
    return redirect(url_for('public_feed'))



# Handle incoming messages
@socketio.on('send_message')
def handle_message(data):
    server_id = data['server_id']
    message = data['message']
    username = data['username']

    # Broadcast the message to everyone in the room (server)
    emit('receive_message', {
        'message': message,
        'username': username
    }, room=f'server_{server_id}')
  
    chat_history = ChatMessage(
    server_id=server_id,
    content=message,  # Correct field
    username=username
)

    try:
        db.session.add(chat_history)
        db.session.commit()
        
    except Exception as e:
        print(f"Error saving message to the database: {e}")
        db.session.rollback()
        return "Couldn't save the message"

    # Save the message to the database
    
# Join the room for this server
@socketio.on('join')
def on_join(data):
    server_id = data['server_id']
    username = data['username']
    
    join_room(f'server_{server_id}')
    emit('system_message', {'message': f'{username} has joined the chat.'}, room=f'server_{server_id}')


# WebSocket event for leaving a room (server)
@socketio.on('leave')
def handle_leave(data):
    room = data['room']
    leave_room(room)
    send(f"{session['username']} has left the chat", room=room)


@socketio.on('join_private_chat')
def handle_join_private_chat(data):
    room = data.get('room')  # The unique room for this private chat
    join_room(room)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app,  debug= True , host="0.0.0.0" , port= 8080)
