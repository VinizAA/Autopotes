from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
import sqlite3, requests, re, smtplib

app = Flask(__name__)
app.secret_key = "senhasecreta"

def init_db():
    con = sqlite3.connect('clients.db')
    c = con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, password TEXT, email TEXT)")

    con.commit()
    con.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    con = sqlite3.connect('users.db')
    c = con.cursor()

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']



        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    con = sqlite3.connect('clients.db')
    c = con.cursor()

    error_password = None
    error_user = None 
    success_message = None
    full_name, email, dob = "", "", ""

    if request.method == 'POST':
        full_name = request.form['full_name']
        password = request.form['password']
        conf_password = request.form['conf_password']
        email = request.form['email']

        if password == conf_password:
            valid_password = True
        else:
            valid_password = False

        if full_name and password and email:
            if valid_password == True:
                c.execute("SELECT * FROM users WHERE email=? ", (email, ))
                if c.fetchone() is not None:
                    error_user = "Usuário já existe!"
                    return render_template('register.html', error_user=error_user)
                else:
                    c.execute("INSERT INTO users VALUES (?,?,?,?)", (None, full_name, password, email))
                    con.commit()
                    success_message = "Cadastro realizado com sucesso!"
                    return render_template('register.html', success_message=success_message)
            else:
                error_password = "Senhas precisam ser iguais!"
                return render_template('register.html', error_password=error_password)

    con.close()
    return render_template('register.html', error_user=error_user, full_name=full_name, email=email)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

