#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
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
    query = 'SELECT timestamp, filePath, caption FROM Photo WHERE photoOwner = %s ORDER BY timestamp DESC'
    cursor.execute(query, (user))
    data = cursor.fetchall()
    cursor.close()
    return render_template('home.html', username=user, posts=data)


@app.route('/post', methods=['GET', 'POST'])
def post():
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

    query  = "INSERT INTO `follow`(`followerUsername`, `followeeUsername`, `acceptedfollow`) VALUES (%s,%s,%s)"
    #print(request.form['toFollow'])
    cursor.execute(query, (username, toFollow, False))
    conn.commit()
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
    cursor = conn.cursor();
    query = 'SELECT followerUsername FROM Follow WHERE followeeUsername = %s AND acceptedfollow = 0'
    cursor.execute(query, (user))
    data = cursor.fetchall()
    cursor.close()
    return render_template('follow.html', requests = data)

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
