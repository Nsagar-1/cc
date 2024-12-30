
from flask import request , redirect , url_for ,  render_template , session
from db import db , app 
from classes  import friends
import classes
from sqlalchemy.exc import IntegrityError
import  random  , re  , smtplib
from werkzeug.utils import secure_filename
from flask import Blueprint


gateway = Blueprint('gateway', __name__)
