######################################
# Photo Sharing Website -Joseph Kwan
# Part of Boston University CS460
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################


import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask_login

#for image uploading
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '5555'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)


#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out')

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', suppress='True')

@app.route("/register", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
		password=request.form.get('password')
		first_name=request.form.get('first_name')
		last_name=request.form.get('last_name')
		birth_date=request.form.get('birth_date')
		hometown=request.form.get('hometown')
		gender=request.form.get('gender')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return render_template('register.html', message='All fields are required')
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (email, password, first_name, last_name, birth_date, hometown, gender)"
            "VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(email, password, first_name, last_name, birth_date, hometown, gender)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))


@app.route("/friends", methods=['GET'])
def friend():
	email = flask_login.current_user.id
	uid = getUserIdFromEmail(email)

	cursor = conn.cursor()
	cursor.execute("SELECT u.* FROM Users u "
				   "INNER JOIN Friends f1 ON u.user_id = f1.user_id2 "
				   "INNER JOIN Friends f2 ON f1.user_id1 = f2.user_id2 "
				   "WHERE f2.user_id1 = '{0}' AND f1.user_id2 "
				   "NOT IN (SELECT user_id2 FROM Friends WHERE user_id1 = '{0}')".format(uid))
	fet = cursor.fetchall()

	return render_template('friends.html', friends= getFriendsList(uid), recommended=fet)

@app.route("/friends", methods=['POST'])
@flask_login.login_required
def add_friends():
	email = flask_login.current_user.id
	uid = getUserIdFromEmail(email)
	try:
		user1 = getUserIdFromEmail(flask_login.current_user.id)
		print('clear1')
		user2 = getUserIdFromEmail(request.form.get('friend_email'))
		print('clear2')
	except:
		print("couldn't find all tokens")
		return render_template('friends.html', message='Email empty or not found', friends= getFriendsList(uid))
	conn.cursor()
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	if user2 == user_id:
		return render_template('friends.html', message= 'You cannot friend yourself', friends= getFriendsList(uid))
	else:
		try:
			conn.cursor()
			print('entry')
			print(cursor.execute("INSERT INTO Friends (user_id1, user_id2)" "VALUES ('{0}', '{1}')".format(user1, user2)))
			print('inserted friend')
			conn.commit()
			return render_template('friends.html', message="Friend Added", friends= getFriendsList(uid))
		except:
			return render_template('friends.html', message="Already Friends", friends= getFriendsList(uid))



def getFriendsList(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id2  FROM Friends WHERE user_id1 = '{0}'".format(uid))
	fet = cursor.fetchall()
	friendIDs = [friends[0] for friends in fet]
	friendemails = []
	for i in friendIDs:
		cursor.execute("SELECT email FROM Users WHERE user_id = '{0}'".format(i))
		friendemails.append(cursor.fetchone()[0])
	print(friendemails)
	return friendemails

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, photo_id, caption  FROM Photos WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getTaggedPhotos(tid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, photo_id, caption FROM Photos NATURAL JOIN Tags NATURAL JOIN Tagged WHERE tag_id = '{0}'".format(tid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getSearchedPhotos(pname):
	return 0

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True


def getUsersAlbums(user_id):
	cursor = conn.cursor()
	cursor.execute("SELECT name FROM Albums WHERE user_id = '{0}'".format(user_id))
	fet = cursor.fetchall()
	album_id = [alb[0] for alb in fet]
	return album_id

def getAlbumIdFromName(album_name, user_id):
	cursor = conn.cursor()
	cursor.execute("SELECT A.albums_id FROM Albums A WHERE (A.name = '{0}' AND A.user_id = '{1}')".format(album_name, user_id))
	return cursor.fetchone()[0]

def getAlbumPhotos(aid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, photo_id, caption FROM Photos WHERE albums_id = '{0}'".format(aid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getTagIdFromName(tag_name):
	cursor = conn.cursor()
	cursor.execute("SELECT tag_id FROM Tags WHERE name = '{0}'".format(tag_name))
	return cursor.fetchone()[0]

def getLikesFromPhoto(photo_id):#gets the number of likes from a single photo via id
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Likes WHERE photo_id = '{0}'".format(photo_id))
	return len(cursor.fetchall())

def getLikedBy(photo_id):#gets the number of likes from a single photo via id
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Likes WHERE photo_id = '{0}'".format(photo_id))
	list = cursor.fetchall()
	names = [0 for j in range(len(list))]
	for i in range(len(list)):
		uid = list[i][0]
		cursor = conn.cursor()
		cursor.execute("SELECT email from Users WHERE user_id = '{0}'".format(uid))
		to_add = cursor.fetchone()[0]
		names[i] = to_add
	return names

def isPhotoLiked(photo_id, user_id):
	#use this to check if someone already liked a photo already
	cursor = conn.cursor()
	if cursor.execute("SELECT photo_id  FROM Likes WHERE photo_id = '{0}' AND user_id = '{1}'".format(photo_id, user_id)):
		#this means there are greater than zero entries with that like
		return True
	else:
		return False

#end login code


@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		album = getAlbumIdFromName(request.form.get('album'), uid)
		photo_data = base64.b64encode(imgfile.read()).decode("ascii")
		cursor = conn.cursor()
		cursor.execute('''INSERT INTO Photos (imgdata, user_id, caption, albums_id) VALUES ('{0}', '{1}', '{2}', '{3}' )'''.format(photo_data,uid, caption, album))
		conn.commit()
		return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid),base64=base64)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html')
#end photo uploading code

@app.route("/album", methods=['GET'])
@flask_login.login_required##?
def album():
	return render_template('album.html', album = getUsersAlbums(getUserIdFromEmail(flask_login.current_user.id)))

@app.route('/album', methods=['POST'])
@flask_login.login_required
def create_album():
	try:
		user_id = getUserIdFromEmail(flask_login.current_user.id)
		album_name = request.form.get('album')
		cursor = conn.cursor()
		if album_name not in getUsersAlbums(getUserIdFromEmail(flask_login.current_user.id)):
			cursor.execute("INSERT INTO Albums (name, user_id) VALUES ('{0}', '{1}')".format(album_name, user_id))
			conn.commit()
			return render_template('album.html', message = 'Album added to collection',
								   album = getUsersAlbums(getUserIdFromEmail(flask_login.current_user.id)))
		else:
			return render_template('album.html', message = 'Error: Duplicate Album',
								   album = getUsersAlbums(getUserIdFromEmail(flask_login.current_user.id)))

	except:
		return flask.redirect(flask.url_for('album'))

@app.route("/gallery", methods=['GET'])
@flask_login.login_required
def gallery():
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id, name FROM Albums WHERE user_id = '{0}'".format(user_id))
	fet2 = cursor.fetchall()
	return render_template('gallery.html',
						   user_albums = getUsersAlbums(getUserIdFromEmail(flask_login.current_user.id)), opened='False', a_tuple =fet2)


@app.route("/gallery", methods=['POST'])
@flask_login.login_required
def show_photos():

	user_id = getUserIdFromEmail(flask_login.current_user.id)
	album_name = request.form.get('album')
	album_id = getAlbumIdFromName(album_name, user_id)
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, caption FROM Photos WHERE( user_id = '{0}' AND albums_id = '{1}')".format(user_id, album_id))
	fet = cursor.fetchall()#YES
	ids = getAlbumPhotos(album_id)
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id, name FROM Albums WHERE user_id = '{0}'".format(user_id))
	fet2 = cursor.fetchall()
	return render_template('gallery.html', user_albums = getUsersAlbums(getUserIdFromEmail(flask_login.current_user.id)),
						   opened='True', current = album_name, contents = fet, tuple = ids, a_tuple =fet2 )

@app.route("/gallery/del", methods=['POST'])
@flask_login.login_required
def del_photos():
	del1 = request.form.get('del')
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Photos WHERE(photo_id ="+del1+" )")
	return render_template('gallery.html', user_albums=getUsersAlbums(getUserIdFromEmail(flask_login.current_user.id)),
						   opened='False')

@app.route("/gallery/del_album", methods=['POST'])
@flask_login.login_required
def del_album():
	del2 = request.form.get('del_album')
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Albums WHERE(albums_id ="+del2+")")
	return render_template('gallery.html', user_albums=getUsersAlbums(getUserIdFromEmail(flask_login.current_user.id)),
						   opened='False')

@app.route("/gallery/add_tag", methods=['POST'])
@flask_login.login_required
def assign_tags():
	tag = request.form.get('tag')
	p_select = request.form.get('p_select')
	if tagExists(tag) == False:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Tags (name, quantity) VALUES ('{0}', '{1}')".format(tag, 0))
		conn.commit()
	tag_id = getTagIdFromName(tag)
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Tagged (photo_id, tag_id) VALUES ('{0}', '{1}')".format(p_select, tag_id))
	conn.commit()
	tagCounter(tag_id)
	return render_template('gallery.html', user_albums=getUsersAlbums(getUserIdFromEmail(flask_login.current_user.id)),
						   opened='False')
def tagExists(tag):
	#use this to check if a tag exists
	cursor = conn.cursor()
	if cursor.execute("SELECT name  FROM Tags WHERE name = '{0}'".format(tag)):
		return True
	else:
		return False

@app.route("/gallery/tags", methods=['POST'])
@flask_login.login_required
def tagSearch():
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	tag_name = request.form.get('tag_search')
	tag_id = getTagIdFromName(tag_name)
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, caption FROM Photos NATURAL JOIN Tagged "
				   "WHERE( tag_id ='{0}' AND user_id = '{1}')".format(tag_id, user_id))
	fet = cursor.fetchall()
	return render_template('gallery.html', user_albums=getUsersAlbums(getUserIdFromEmail(flask_login.current_user.id)),
						   opened='False', tag_search ='True', current=tag_name, contents=fet)

@app.route('/browse', methods=['GET'])
def browse():
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT name FROM Tags LIMIT 5")
	fet = cursor.fetchall()
	cursor = conn.cursor()
	cursor.execute("SELECT tag_id FROM Tags LIMIT 5")
	list = cursor.fetchall()
	cursor = conn.cursor()
	tag_list = []
	for i in list:
		tag_list += [i[0]]

	cursor.execute("SELECT DISTINCT imgdata, photo_id, caption from Photos NATURAL JOIN TAGGED "
					   "WHERE tag_id IN {0}".format(tuple(tag_list)))
	img_data = cursor.fetchall()


	return render_template('browse.html', popular=fet, contents = img_data)



@app.route("/browse_tags", methods=['POST'])
def globalTagSearch():
	#try statement
	try:
		tag_name = request.form.get('tag_search')
		tag_id = getTagIdFromName(tag_name)
		cursor = conn.cursor()
		cursor.execute("SELECT imgdata, caption, photo_id FROM Photos NATURAL JOIN Tagged "
					   "WHERE tag_id ='{0}'".format(tag_id))
	except:
		print("Not within search")
		return render_template('browse.html', message='Tag does not exist!')

	fet = cursor.fetchall()
	img_data = [ [0 for x in range(len(fet[0])+2)] for y in range(len(fet))]
	for f in range(len(img_data)):
		for g in range(len(img_data[0])):
			if g == (len(img_data[0])-2):
				img_data[f][g] = getLikesFromPhoto(fet[f][2])
			elif g == (len(img_data[0])-1):
				img_data[f][g] = getLikedBy(fet[f][2])
			else:
				img_data[f][g] = fet[f][g]

	return render_template('browse.html', t_search='True', current=tag_name, contents=img_data, p_list=getTaggedPhotos(tag_id))

@app.route("/browse_photos", methods=['POST'])
def globalPhotoSearch():
	try:
		photo_caption = request.form.get('photo_search')
		print(photo_caption)
		cursor = conn.cursor()
		cursor.execute("SELECT imgdata, caption, photo_id FROM Photos WHERE caption = '{0}'".format(photo_caption))
		fet = cursor.fetchall()
	except:
		print("Not within search")
		return render_template('browse.html', message='No result')

	img_data = [[0 for x in range(len(fet[0]) + 2)] for y in range(len(fet))]
	for f in range(len(img_data)):
		for g in range(len(img_data[0])):
			if g == (len(img_data[0]) - 2):
				img_data[f][g] = getLikesFromPhoto(fet[f][2])
			elif g == (len(img_data[0]) - 1):
				img_data[f][g] = getLikedBy(fet[f][2])
			else:
				img_data[f][g] = fet[f][g]

	return render_template('browse.html', p_search='True', current=photo_caption, contents=img_data)

@app.route("/browse_comments", methods=['POST'])
def globalCommentSearch():
	try:
		comment = request.form.get('comment_search')
		cursor = conn.cursor()
		cursor.execute("SELECT imgdata, caption, photo_id FROM Photos WHERE photo_id = ( SELECT (photo_id) FROM Comments WHERE text = '{0}')".format(comment))
	except:
		print("Not within search")
		return render_template('browse.html', message='No result')

	fet = cursor.fetchall()
	print(fet)
	img_data = [[0 for x in range(len(fet[0]) + 2)] for y in range(len(fet))]
	for f in range(len(img_data)):
		for g in range(len(img_data[0])):
			if g == (len(img_data[0]) - 2):
				img_data[f][g] = getLikesFromPhoto(fet[f][2])
			elif g == (len(img_data[0]) - 1):
				img_data[f][g] = getLikedBy(fet[f][2])
			else:
				img_data[f][g] = fet[f][g]


	return render_template('browse.html', p_search='True', current=comment, contents=img_data)



def tagCounter(t_id):
	cursor = conn.cursor()
	cursor.execute("UPDATE Tags SET quantity = quantity + 1 WHERE tag_id = '{0}'".format(t_id))
	conn.commit()
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Tags ORDER BY quantity DESC")
	return True



@app.route("/browse/comment", methods=['POST'])
def comm_photos():
	com1 = request.form.get('comment')
	pid = request.form.get('photo_id')
	try:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Comments (photo_id, text, user_id) VALUES ('{0}', '{1}', '{2}')".format(pid, com1, uid))
		conn.commit()

	except:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Comments (photo_id, text) VALUES ('{0}', '{1}')".format(pid, com1))
		conn.commit()
		return render_template('browse.html', t_search='False', message='Comment added anonymously')
	return render_template('browse.html',t_search='False', message = 'Comment added')

@app.route("/browse/like", methods=['POST'])#CONTINUE
def like_photos():
	photo_id = request.form.get('photo_id2')
	user_id = getUserIdFromEmail(flask_login.current_user.id)

	if(isPhotoLiked(photo_id,user_id)):
		return render_template('browse.html', t_search='False', message='You cannot re-like the same photo!')#message = 'you cannot relike the same photo!'


	else:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Likes (photo_id, user_id) VALUES ('{0}', '{1}')".format(photo_id, user_id))
		conn.commit()
		return render_template('browse.html', t_search='False', message='Liked Photo!')



def giveUserScore(user_id):
	p_total = len(getUsersPhotos(user_id))
	cursor = conn.cursor()
	cursor.execute("SELECT photo_id FROM Comments Where user_id = '{0}'".format(user_id))
	c_total = len(cursor.fetchall())
	u_total = p_total + c_total
	print(u_total)
	cursor = conn.cursor()
	cursor.execute("UPDATE Users SET score ='{0}' WHERE user_id = '{1}'".format(u_total,user_id))
	conn.commit()
	return

@app.route("/friends", methods=['GET'])
def user_ranking():
	cursor = conn.cursor()
	cursor.execute("SELECT user_id, email FROM Users")
	all_users = cursor.fetchall()
	for u in all_users:
		giveUserScore(u[0])
	cursor.execute("SELECT * FROM Users ORDER BY score DESC")
	conn.commit()
	cursor.execute("SELECT email FROM Users LIMIT 10")
	top_ten = cursor.fetchall()
	return render_template('hello.html', leaderboard = top_ten)


#default page

@app.route("/", methods=['GET'])
def hello():
	cursor = conn.cursor()
	cursor.execute("SELECT user_id, email FROM Users")
	all_users = cursor.fetchall()
	for u in all_users:
		giveUserScore(u[0])
	cursor.execute("SELECT * FROM Users ORDER BY score DESC")
	conn.commit()
	if len(all_users) < 10:
		cursor.execute("SELECT email FROM Users ")
		top_ten = cursor.fetchall()
	else:
		cursor.execute("SELECT email FROM Users LIMIT 10")
		top_ten = cursor.fetchall()
	return render_template('hello.html', message='Welecome to Photoshare', leaderboard = top_ten)


if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)
