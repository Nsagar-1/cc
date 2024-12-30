from db import db , app
import classes
from flask import request, jsonify , redirect , session , url_for , render_template , flash 
from datetime import date 


@app.route('/get_friends', methods=['GET'])
def get_friends():
    user_id = session.get('user_id')
    user = classes.User().query.get(user_id)
    friends = user.friends.all()  # Assuming classes.User() has a 'friends' relationship
    return jsonify(friends=[{'username': friend.username} for friend in friends])


@app.route('/send_reel', methods=['POST'])
def send_reel():
    data = request.json
    reel_slug = data['reel_id']
    friends_usernames = data['friends_usernames']  # Receive an array of friend usernames
    
    # Get the reel by its slug
    reel = classes.Reel().query.filter_by(slug=reel_slug).first()
    
    if not reel:
        return jsonify(success=False, message='classes.Reel() not found'), 404

    # Send the reel to each friend
    for friend_username in friends_usernames:
        friend = classes.User().query.filter_by(username=friend_username).first()
        if friend:
            send_reel_to_friend(reel.id, friend.id)  # Use the same function to send the reel

    return jsonify(success=True)

def send_reel_to_friend(reel_id, friend_id):
    # Fetch the reel by its ID to get the slug
    reel = classes.Reel().query.get(reel_id)
    
    if reel:
        # Use slug for the URL instead of reel_id
        reel_url = url_for('view_single_reel', slug=reel.slug, _external=True)
        
        # Get the current user (sender)
        sender_id = session.get('user_id')
        
        # Create a message with the reel link
        message_content = f"Check out this reel: {reel_url}"

        # Add the message to the database
        new_message = classes.PrivateMessage(
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
    reel = classes.Reel().query.filter_by(slug=slug).first_or_404()

    if reel.visibility == 'Private' and reel.user_id != user_id:
        return "This reel is private.", 403

    if reel.visibility == 'Friends' and reel.user_id != user_id:
        user = classes.User().query.get(user_id)
        if user_id not in [friend.id for friend in user.friends]:
            return "This reel is only visible to friends.", 403

    is_liked = False
    if user_id:
        user = classes.User().query.get(user_id)
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












# Route to send a request for classes.Mentorship()
@app.route('/request_mentorship/<int:receiver_id>', methods=['POST'])
def request_mentorship(receiver_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    sender = classes.User().query.filter_by(username=session['username']).first()
    receiver = classes.User().query.get(receiver_id)

    if not receiver or receiver == sender:
        return redirect(url_for('search'))

    # Check if the classes.Mentorship() request already exists
    existing_request = classes.HelperRequest().query.filter_by(sender_id=sender.id, receiver_id=receiver.id, helper_type='mentorship').first()
    if not existing_request:
        # Create a new classes.Mentorship() request
        new_request = classes.HelperRequest()(sender_id=sender.id, receiver_id=receiver.id, helper_type='mentorship', status='pending')
        db.session.add(new_request)
        db.session.commit()
        return f'classes.Mentorship() request sent to {receiver.username}!'
    else:
        return 'classes.Mentorship() request already sent.'

@app.route('/mentors')
def mentors():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = classes.User().query.filter_by(username=session['username']).first()

    # Fetch mentorship requests
    sent_requests = classes.HelperRequest().query.filter_by(sender_id=user.id, helper_type='mentorship').all()
    received_requests = classes.HelperRequest().query.filter_by(receiver_id=user.id, helper_type='mentorship').all()

    # Fetch existing mentorships
    mentorships_as_mentor = classes.Mentorship().query.filter_by(mentor_id=user.id).all()
    mentorships_as_mentee = classes.Mentorship().query.filter_by(mentee_id=user.id).all()

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
    mentorship_request = classes.HelperRequest().query.get(request_id)

    if mentorship_request and mentorship_request.receiver_id == classes.User().query.filter_by(username=session['username']).first().id:
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
        current_user = classes.User().query.get(1)  # Replace with session user ID or logged-in user

        if not current_user:
            flash("Please log in to create a webinar.", "danger")
            return redirect(url_for('login'))

        new_webinar = classes.Webinar()(
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
            flash("classes.Webinar() created successfully!", "success")
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

    user = classes.User().query.filter_by(username=session['username']).first()
    mentorship_request = classes.HelperRequest().query.get(request_id)

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
    existing_mentorship = classes.Mentorship().query.filter(
        ((classes.Mentorship().mentor_id == user.id) & (classes.Mentorship().mentee_id == other_user_id)) |
        ((classes.Mentorship().mentor_id == other_user_id) & (classes.Mentorship().mentee_id == user.id))
    ).first()

    if existing_mentorship:
        return 'classes.Mentorship() already established', 400

    # Establish mentorship based on selected relation
    if relation == 'mentor':
        mentor_id = user.id
        mentee_id = other_user_id
    else:  # 'mentee'
        mentor_id = other_user_id
        mentee_id = user.id

    # Create the mentorship
    new_mentorship = classes.Mentorship()(mentor_id=mentor_id, mentee_id=mentee_id)
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
    webinars = classes.Webinar().query.all()
    return render_template('join_webinar.html', webinars=webinars)


@app.route('/about_webinar/<int:webinar_id>')
def about_webinar(webinar_id):
    webinar = classes.Webinar().query.get_or_404(webinar_id)  # Fetch webinar by ID, or show 404 error if not found
    creator_username = webinar.creator.username  # Access the username through the relationship

    return render_template('about_webinar.html', webinar=webinar, creator_username=creator_username)





