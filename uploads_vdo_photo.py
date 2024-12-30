from flask import app  , session , request , redirect , url_for , render_template , jsonify , abort
from db import db 
import classes , os  , socketio  
from werkzeug.utils import secure_filename







##*********************************** Videos ***********************************##
##*********************************** Videos ***********************************##
@app.route('/upload_video', methods=['GET', 'POST'])
def upload_video():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        tags = request.form['tags']
        privacy = request.form['privacy']
        video_file = request.files['video_file']

        # Ensure the directory for videos exists
        video_dir = app.config['VIDEOS_FOLDER']
        if not os.path.exists(video_dir):
            os.makedirs(video_dir)

        # Save the uploaded video file
        if video_file:
            filename = secure_filename(video_file.filename)
            video_path = os.path.join(video_dir, filename)
            video_file.save(video_path)

            # Get the uploader and save video details in the database
            uploader = classes.User().query.filter_by(username=session['username']).first()
            new_video = classes.Video()(
                title=title, 
                description=description, 
                filename=filename, 
                category=category, 
                uploader_id=uploader.id,
                tags=tags,
                privacy=privacy
            )
            db.session.add(new_video)
            db.session.commit()

            return redirect(url_for('view_video_by_unique_id', unique_id=new_video.unique_id))
    
    return render_template('upload_video.html')



@app.route('/upload_photo', methods=['GET', 'POST'])
def upload_photo():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        photo_file = request.files['photo_file']
        if photo_file:
            photo_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'photos')
            if not os.path.exists(photo_dir):
                os.makedirs(photo_dir)
            
            filename = secure_filename(photo_file.filename)
            photo_path = os.path.join(photo_dir, filename)
            photo_file.save(photo_path)
            # Logic to save photo details to the database
            return redirect(url_for('dashboard'))
    
    return render_template('upload_photo.html')



@app.route('/react_video/<int:video_id>', methods=['POST'])
def react_video(video_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'classes.User() not logged in'}), 403

    data = request.get_json()
    reaction_type = data.get('reaction_type')
    if reaction_type not in ['like', 'love', 'haha']:
        return jsonify({'status': 'error', 'message': 'Invalid reaction type'}), 400

    existing_reaction = classes.Reaction().query.filter_by(video_id=video_id, user_id=user_id).first()

    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            db.session.delete(existing_reaction)  # Toggle off
        else:
            existing_reaction.reaction_type = reaction_type  # Change reaction type
            db.session.add(existing_reaction)
    else:
        new_reaction = classes.Reaction()(video_id=video_id, user_id=user_id, reaction_type=reaction_type)
        db.session.add(new_reaction)

    db.session.commit()  # Save changes to database

    # Fetch the updated counts directly from the database
    like_count = classes.Reaction().query.filter_by(video_id=video_id, reaction_type='like').count()
    love_count = classes.Reaction().query.filter_by(video_id=video_id, reaction_type='love').count()
    haha_count = classes.Reaction().query.filter_by(video_id=video_id, reaction_type='haha').count()

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

    user = classes.User().query.filter_by(username=session['username']).first()
    video = classes.Video().query.get(video_id)

    # Create a new video entry as a "shared" post
    shared_video = classes.Video()(
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

    user = classes.User().query.filter_by(username=session['username']).first()
    comment_content = request.json.get('comment')
    new_comment = classes.Comment(video_id=video_id, user_id=user.id, content=comment_content)
    db.session.add(new_comment)
    db.session.commit()

    # Emit the update to all connected clients
    comment_count = classes.Comment.query.filter_by(video_id=video_id).count()
    socketio.emit('update_comments', {'video_id': video_id, 'comment_count': comment_count})

    return jsonify({'status': 'success'}), 200


@app.route('/view_video/<int:video_id>')
def view_video(video_id):
    # Fetch the video details from the database using the video_id
    video = classes.Video().query.get(video_id)
    if not video:
        abort(404)  # Return a 404 error if the video is not found

    # Render the video details in the view_video.html template
    return render_template('view_video.html', video=video)





## *************************** REELS ********************************************************* ##
## *************************** REELS ********************************************************* ##

@app.route('/reels', methods=['GET', 'POST'])
def reels():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = classes.User().query.filter_by(username=session['username']).first()
    reels = classes.Reel().query.order_by(classes.Reel().id.desc()).all()

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
            new_reel = classes.Reel()(title=title, description=description, filename=filename, tags=tags, visibility=visibility, user_id=user_id)
            new_reel.generate_slug()  # Generate unique slug
            db.session.add(new_reel)
            db.session.commit()

            return "classes.Reel() uploaded successfully", 200

    # If GET request, render the upload form
    return render_template('upload_reel.html')






@app.route('/delete_video/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    if 'username' not in session:
        return 'Unauthorized', 401
    
    user = classes.User().query.filter_by(username=session['username']).first()
    video = classes.Video().query.get_or_404(video_id)

    if video.uploader_id != user.id:
        return 'Unauthorized to delete this video', 403

    # Delete the video from the database
    db.session.delete(video)
    db.session.commit()

    return 'classes.Video() deleted successfully', 200