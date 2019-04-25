#Import Flask Library
from flask import Flask, flash, render_template, request, session, url_for, redirect
import pymysql.cursors
import os

import hashlib

salt = b"dankmemes"

def sha1Pass(password):
    m = hashlib.sha1()
    m.update(password)
    return m.hexdigest()

#Initialize the app from Flask
app = Flask(__name__)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 3306,
                       user='root',
                       #password='root',
                       db='finstagram',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

#Define a route to hello function
@app.route('/')
def hello():
    return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    return render_template('register.html')

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    #grabs information from the forms
    username = request.form['username']
    password = sha1Pass((request.form['password']).encode('utf-8') + salt)

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM Person WHERE username = %s and password = %s'
    cursor.execute(query, (username, password))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if(data):
        #creates a session for the the user
        #session is a built in
        session['username'] = username
        return redirect(url_for('home'))
    else:
        #returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    username = request.form['username']
    password = sha1Pass((request.form['password']).encode('utf-8') + salt)
    fname = request.form['fname']
    lname = request.form['lname']

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(query, (username))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO Person VALUES(%s, %s, %s, %s, %s, %s, %s)'
        cursor.execute(ins, (username, password, fname, lname, None, None, True))
        conn.commit()
        cursor.close()
        return render_template('index.html')


@app.route('/home')
def home():
    user = session['username']
    cursor = conn.cursor();
    query = 'SELECT photoID, photoOwner, timestamp, filePath, caption FROM Photo WHERE photoOwner = %s ORDER BY timestamp DESC'
    cursor.execute(query, (user))
    data = cursor.fetchall()
    query = 'SELECT * FROM Belong WHERE username = %s'
    cursor.execute(query, (user))
    groups = cursor.fetchall()
    length = [ i for i in range(len(groups)) ]
    cursor.close()
    return render_template('home.html', username=user, posts=data, group = groups, length = length)


@app.route('/post', methods=['GET', 'POST'])
def post():
    print("test")
    username = session['username']
    cursor = conn.cursor();
    pic = request.files['pic']
    extension = os.path.splitext(pic.filename)[1]
    caption = None if len(request.form['caption']) == 0 else request.form['caption']
    allFollowers = True if request.form['allFollowers'] == "true" else False

    target = os.path.join(APP_ROOT, 'uploads/')

    query = 'INSERT INTO Photo (photoOwner, timestamp, caption, allFollowers) VALUES(%s, NOW(), %s, %s)'
    cursor.execute(query, (username, caption, allFollowers))
    conn.commit()

    query = 'SELECT photoID FROM Photo WHERE photoOwner = %s ORDER BY timestamp DESC'
    cursor.execute(query, (username))
    data = cursor.fetchone()
    # print(data)
    # print(extension)

    file_name = str(data['photoID']) + extension
    pic.save("/".join([APP_ROOT, "static/uploads", file_name]))

    query = 'UPDATE Photo SET filePath = %s WHERE photoID = %s'
    cursor.execute(query, (file_name, data['photoID']))
    conn.commit()

    if not allFollowers:
        groupName = dict()
        groupOwner = dict()
        for key in request.form:
            split = key.split(",")
            if "groupName" == split[0]:
                groupName[int(split[1])] = request.form[key]
            elif "groupOwner" == split[0]:
                groupOwner[int(split[1])] = request.form[key]

        for key in groupName:
            query = "INSERT INTO Share VALUES(%s, %s, %s)"
            cursor.execute(query, (groupName[key], groupOwner[key], data['photoID']))
            conn.commit()

    cursor.close()
    return redirect(url_for('home'))

@app.route('/select_blogger')
def select_blogger():
    #check that user is logged in
    #username = session['username']
    #should throw exception if username not found

    cursor = conn.cursor();
    # query = 'SELECT DISTINCT username FROM blog'
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return render_template('select_blogger.html', user_list=data)

@app.route('/show_posts', methods=["GET", "POST"])
def show_posts():
    poster = request.args['poster']
    cursor = conn.cursor();
    # query = 'SELECT ts, blog_post FROM blog WHERE username = %s ORDER BY ts DESC'
    cursor.execute(query, poster)
    data = cursor.fetchall()
    cursor.close()
    return render_template('show_posts.html', poster_name=poster, posts=data)

@app.route('/send_follow', methods = ["GET", "POST"])
def send_follow():
    #reloads page but sends follow to user specified
    username = session['username']
    toFollow = request.form['toFollow']
    cursor = conn.cursor()
    #prior to following, followee msut exist - will need to check
    query = 'SELECT Count(*) as count FROM Person WHERE username = %s;'
    cursor.execute(query, (toFollow))
    data = cursor.fetchall()
    if data[0]['count'] == 1:
        query = 'SELECT Count(*) as count FROM Follow WHERE followerUsername = %s AND followeeUsername = %s;'
        cursor.execute(query, (username, toFollow))
        data = cursor.fetchall()
        if data[0]['count'] == 1:
            flash("You're already following " + toFollow)
        else:
            query  = "INSERT INTO `follow`(`followerUsername`, `followeeUsername`, `acceptedfollow`) VALUES (%s,%s,%s)"
            #print(request.form['toFollow'])
            cursor.execute(query, (username, toFollow, False))
            conn.commit()
    else:
        flash(toFollow + " does not exist!")
    return redirect(url_for('follow'))

@app.route('/accept_follow/<follower>')
def accept_follow(follower):
    cursor = conn.cursor()
    query = 'UPDATE Follow SET acceptedfollow = 1 WHERE followerUsername = %s AND followeeUsername = %s'
    cursor.execute(query, (follower, session['username']))
    conn.commit()
    cursor.close()
    return redirect(url_for('follow'))

@app.route('/reject_follow/<follower>')
def reject_follow(follower):
    cursor = conn.cursor()
    query = 'DELETE FROM Follow WHERE followerUsername = %s AND followeeUsername = %s'
    cursor.execute(query, (follower, session['username']))
    conn.commit()
    cursor.close()
    return redirect(url_for('follow'))

@app.route('/follow')
def follow():
    user = session['username']
    data = []
    cursor = conn.cursor();
    #get users who are still pending
    query = 'SELECT followerUsername FROM Follow WHERE followeeUsername = %s AND acceptedfollow = 0'
    cursor.execute(query, (user))
    data.append(cursor.fetchall())
    #get users who were accepted
    query = 'SELECT followerUsername FROM Follow WHERE followeeUsername = %s AND acceptedfollow = 1'
    cursor.execute(query, (user))
    data.append(cursor.fetchall())
    cursor.close()
    return render_template('follow.html', requests = data)

@app.route('/group')
def group():
    user = session['username']
    cursor = conn.cursor()
    query = 'SELECT groupName, groupOwner FROM Belong WHERE username = %s'
    cursor.execute(query, (user))
    data = cursor.fetchall()
    cursor.close()
    return render_template('group.html', request = data)

@app.route('/create_group',  methods = ["GET", "POST"])
def create_group():
    user = session['username']
    group_name = request.form["createGroup"]
    cursor = conn.cursor();
    #check if user already owns a
    query = 'SELECT Count(*) as count FROM closefriendgroup WHERE groupName = %s AND groupOwner = %s;'
    cursor.execute(query,(group_name, user))
    data = cursor.fetchall()
    print(data[0]['count'])
    if data[0]['count'] == 1:
        #print("I already own a group with this name")
        flash('You already own a group with name:' + group_name)
    else:
        #create a group if user does not currently own a group
        query = 'INSERT INTO closefriendgroup (groupName, groupOwner) VALUES (%s,%s);'
        cursor.execute(query, (group_name, user))
        query = 'INSERT INTO belong (groupName, groupOwner, username) VALUES (%s,%s,%s);'
        cursor.execute(query, (group_name, user, user))
        conn.commit()
        cursor.close()

    return redirect(url_for('group'))

@app.route('/add_friend', methods = ["GET", "POST"])
def add_friend():
    user = session['username']
    group_name = request.form["group_name"]
    to_add = request.form["toAdd"]
    cursor = conn.cursor();

    #find if group exists and you are the owner
    query = 'SELECT Count(*) as count FROM closefriendgroup WHERE groupName = %s AND groupOwner = %s;'
    cursor.execute(query,(group_name, user))
    data = cursor.fetchall()
    if data[0]['count'] == 1:
        #check if user you are adding is already in the group
        query = 'SELECT Count(*) as count FROM belong WHERE groupName = %s AND groupOwner = %s AND username = %s;'
        cursor.execute(query, (group_name, user, to_add))
        data = cursor.fetchall()
        if data[0]['count'] > 0:
            #to_add already in group
            flash(to_add + " is already in " + group_name)
        else:
            query = 'SELECT Count(*) as count FROM Person WHERE username = %s;'
            cursor.execute(query,(to_add))
            data = cursor.fetchall()
            if data[0]['count'] == 1:
                query = 'INSERT INTO belong (groupName, groupOwner, username) VALUES (%s,%s,%s);'
                cursor.execute(query, (group_name, user, to_add))
                conn.commit()
            else:
                flash(to_add + " does not exist!")
    else:
        #to_add already in group
        flash("You need to be the owner of " + group_name)

    return redirect(url_for('group'))

@app.route("/tag/<photoID>")
def tag(photoID):
    cursor = conn.cursor();
    query = 'SELECT filePath FROM Photo WHERE photoID = %s;'
    cursor.execute(query, (photoID))
    filePath = cursor.fetchall()[0]["filePath"]
    query = 'SELECT * FROM Tag WHERE username = %s AND acceptedTag <> 1;'
    cursor.execute(query, (session["username"]))
    data = cursor.fetchall()
    return render_template("add_tag.html", photoID = photoID, filePath = filePath, requests = data)


@app.route("/add_tag", methods = ["GET", "POST"])
def add_tag():
    username = session["username"]
    tagee = request.form["toTag"]
    photoID = request.form["photoID"]
    cursor = conn.cursor();

    #check if user you are adding is already being tagged
    query = 'SELECT Count(*) as count FROM Tag WHERE username = %s AND photoID = %s;'
    cursor.execute(query, (tagee, photoID))
    data = cursor.fetchall()
    print(data)
    if data[0]['count'] == 0:
        added = True if username == tagee else False
        query = 'INSERT INTO Tag(username, photoID, acceptedTag) VALUES (%s, %s, %s);'
        cursor.execute(query, (tagee, photoID, added))
        conn.commit()
    else:
        #to_add already in group
        flash(tagee + " is already being tagged")

    return redirect(url_for('tag', photoID = photoID))

@app.route('/accept_tag/<tagee>/<photoID>')
def accept_tag(tagee, photoID):
    cursor = conn.cursor()
    query = 'UPDATE Tag SET acceptedTag = 1 WHERE username = %s AND photoID = %s;'
    cursor.execute(query, (tagee, photoID))
    conn.commit()
    cursor.close()
    return redirect(url_for('tag', photoID = photoID))

@app.route('/reject_tag/<tagee>/<photoID>')
def reject_tag(tagee, photoID):
    cursor = conn.cursor()
    query = 'DELETE FROM Tag WHERE username = %s AND photoID = %s;'
    cursor.execute(query, (tagee, photoID))
    conn.commit()
    cursor.close()
    return redirect(url_for('tag', photoID = photoID))


@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')

app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
