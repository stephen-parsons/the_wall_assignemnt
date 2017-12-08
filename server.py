# Stephen Parsons
# Assignment Login and Registration
# 12/6/17

from flask import Flask, render_template, request, redirect, flash, session
from mysqlconnection import MySQLConnector
import re
import datetime
import md5
import os, binascii # include this at the top of your file
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'mp4'])

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
app.secret_key = "myKey"
mysql = MySQLConnector(app, 'wall_assignment')

def allowed_file(filename):
    return '.' in filename and \
    	filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
	session['user_id'] = ""
	session['user_name'] = ""
	return render_template('index.html')
#	
@app.route('/process', methods=["POST"])
def get_info():
	for error in request.form:
		if error == "first_name" or error == "last_name":
			for char in request.form[error]:
				if str(char).isdigit():
				 	flash("No numbers in the name fields!")
					return redirect('/') 
		if error == "password":
			if len(request.form[error]) < 8:
				flash("Password must be at least 8 characters long!")
				return redirect('/')		
		if error == "email":
			if not EMAIL_REGEX.match(request.form['email']):
				flash("Please enter a valid email address!")
				return redirect('/')
			query = "SELECT email FROM users"
			emails = mysql.query_db(query)
			for row in emails:
				if request.form['email'] == row['email']:
					flash("Email already registered!")	
					return redirect('/')	
		if error == "password":
			if request.form[error] != request.form["confirm"]:
				flash("Passwords must match!")
				return redirect('/')
		if len(request.form[error]) < 1:
			flash("Please fill out ALL fields!") # just pass a string to the flash function
			return redirect('/')
	# flash("Success!")	
	first_name = request.form['first_name']
	last_name = request.form['last_name']
	email = request.form['email']
	password = request.form['password']
	salt = binascii.b2a_hex(os.urandom(15))
	hashed_pw = md5.new(password + salt).hexdigest()
	query = "INSERT INTO users (created_at, updated_at, first_name, last_name, email, password, salt) VALUES(NOW(), NOW(), :first_name, :last_name, :email, :hashed_password, :salt)"
	data = {
    	'first_name' : request.form['first_name'],
		'last_name' : request.form['last_name'],
		'email' : request.form['email'],
		'hashed_password' : hashed_pw,
		'salt' : salt
		}
	mysql.query_db(query, data)
	query = "SELECT users.id from users WHERE users.email = :email"
	datae = {
		'email' : email
	}
	userid = mysql.query_db(query, data)
	session['user_id'] = userid[0]['id']
	print userid
	session['user_name'] = request.form['first_name']
   	# return render_template('process.html', first_name=first_name, last_name=last_name, email=email)	
   	#redirect to Wall automatically
   	return redirect('/wall')
#   	
@app.route('/wall')
def wall():
	if session['user_id'] == "":
		flash("Please login or register!")
		return redirect('/')
	# query that gets data of all messages from db
	query = "SELECT CONCAT_WS(' ', users.first_name, users.last_name) as name, CONCAT(DATE_FORMAT(messages.created_at, '%M %D %Y'),' at ', TIME_FORMAT(messages.created_at, '%r')) as timestamp, messages.id as message_id, messages.message as message, messages.user_id as user_id, messages.filename as filename FROM messages JOIN users on users.id = messages.user_id"
	messages = mysql.query_db(query)
	query = "SELECT CONCAT_WS(' ', users.first_name, users.last_name) as name, CONCAT(DATE_FORMAT(comments.created_at, '%M %D %Y'),' at ', TIME_FORMAT(comments.created_at, '%r')) as timestamp, comments.id as comment_id, comments.comment as comment, comments.message_id as message_id FROM comments JOIN users on users.id = comments.user_id"
	comments = mysql.query_db(query)
	length = len(messages) - 1
	return render_template('/wall.html', messages=messages, comments=comments, length=length)
#
@app.route('/submit_message', methods=["POST"])
def submit_message():
	#check file input
	file = request.files['file']
	# print file
	# print allowed_file(file.filename)	
	if file and allowed_file(file.filename):
		filename = secure_filename(file.filename)
		file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
	elif allowed_file(file.filename) == False:
		flash("Choose a valid file type!")
		return redirect('/wall')
	elif file.filename == '':
		filename = None		
	# query that inserts message data to db
	query = "INSERT INTO messages (message, created_at, updated_at, user_id, filename) VALUES (:message, NOW(), NOW(), :user_id, :filename)"
	data = {
    	'message' : request.form['message'],
    	'user_id' : session['user_id'],
    	'filename' : filename
		}
	mysql.query_db(query, data)
	#return to wall
	return redirect('/wall')
#
@app.route('/submit_comment/<message_id>', methods=["POST"])
def submit_comment(message_id):
# query that inserts message data to db
	query = "INSERT INTO comments (comment, created_at, updated_at, user_id, message_id) VALUES (:comment, NOW(), NOW(), :user_id, :message_id)"
	data = {
    	'comment' : request.form['comment'],
    	'user_id' : session['user_id'],
    	'message_id' : message_id
		}
	mysql.query_db(query, data)
	#return to wall
	return redirect('/wall')
#	
@app.route('/login', methods=["POST"])
def login():
	email = request.form['email']
	password = request.form['password']
	query = "SELECT * FROM users"
	data = mysql.query_db(query)
	for row in data:
		encrypted_password = md5.new(password + row['salt']).hexdigest()
		if request.form['email'] == row['email'] and encrypted_password == row['password']:
			# flash("Login Success!")
			session['user_id'] = row['id']
			session['user_name'] = row['first_name']
			print session['user_id']
			# return render_template('login.html', email=email)
			return redirect('/wall')
	else:
		flash("Login info not found!")
		return redirect('/')
#
@app.route('/delete_msg/<message_id>', methods=['POST'])
def delete_message(message_id):
	data = {
	'message_id' : message_id
	}
	query = "SELECT messages.filename FROM messages WHERE id = :message_id"
	filenames = mysql.query_db(query, data)
	for file in filenames:
		if file['filename'] != None:
			os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file['filename']))
	query = "DELETE FROM comments WHERE message_id = :message_id"
	mysql.query_db(query, data)
	query = "DELETE FROM comments WHERE message_id = :message_id"
	mysql.query_db(query, data)
	query = "DELETE FROM messages WHERE id = :message_id"
	mysql.query_db(query, data)
	return redirect('/wall')
@app.route('/logout')
def logout():
	flash("Succesfully logged out!")
	return redirect('/')
app.run(debug=True, host="0.0.0.0")		