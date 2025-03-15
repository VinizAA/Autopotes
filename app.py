from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response, send_from_directory
import sqlite3, requests, re, smtplib, base64, os, random
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from PIL import Image


app = Flask(__name__)
app.secret_key = "senhasecreta"

def init_db():
    con = sqlite3.connect('clients.db')
    c = con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id_user INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, password TEXT, email TEXT, profile_pic BLOB)")
    c.execute("CREATE TABLE IF NOT EXISTS potes (id_pote INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, especie TEXT, data_criacao DATETIME, agua INTEGER, nutri INTEGER, id_user INTEGER, FOREIGN KEY(id_user) REFERENCES users(id_user) ON DELETE CASCADE)")
    
    con.commit()
    con.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    con = sqlite3.connect('clients.db')
    c = con.cursor()

    error_email, error_password = None, None

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        c.execute("SELECT * FROM users WHERE email=?", (email,))
        find_email = c.fetchone()

        c.execute("SELECT full_name FROM users WHERE email=?", (email,))
        name = c.fetchone()
        name = name[0] if name else "Usuário"

        if find_email: #tem conta
            #verificar se senha é da conta validada
            c.execute("SELECT password FROM users WHERE email=?", (email,))
            password_db = c.fetchone()

            if password == password_db[0]:
                #entra na conta
                c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
                user_info = c.fetchone()

                session['id'] = user_info[0]
                session['name'] = user_info[1]
                session['email'] = user_info[3]
                con.close()
                return redirect(url_for('profile', email=email))
            else:
                error_password = "Senha incorreta!"
        else:
            error_email = "Usuário não cadastrado! Crie sua conta agora."

    con.close()
    return render_template('login.html', error_password=error_password, error_email=error_email)

@app.route('/register', methods=['GET', 'POST'])
def register():
    con = sqlite3.connect('clients.db')
    c = con.cursor()

    error_password = None
    error_user = None 
    success_message = None
    full_name, email = "", ""

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
                    c.execute("INSERT INTO users VALUES (?,?,?,?,?)", (None, full_name, password, email, None))
                    con.commit()
                    success_message = "Cadastro realizado com sucesso!"
                    choose_image_profile(email)
                    return render_template('register.html', success_message=success_message)
            else:
                error_password = "Senhas precisam ser iguais!"
                return render_template('register.html', error_password=error_password)

    con.close()
    return render_template('register.html', error_user=error_user, full_name=full_name, email=email)

@app.route('/profile/<email>')
def profile(email):
    con = sqlite3.connect('clients.db')
    c = con.cursor()

    c.execute("SELECT full_name, profile_pic FROM users WHERE email=?", (email,))
    row = c.fetchone()
    
    if row:
        name, image_blob = row
        image_perfil = base64.b64encode(image_blob).decode('utf-8') if image_blob else None
    else:
        name = "Usuário"
        image_perfil = None

    c.execute("SELECT id_user FROM users WHERE email = ?", (email,))
    id_usuario = c.fetchone()
    id_usuario = id_usuario[0] if id_usuario else None 

    if id_usuario:
        c.execute("SELECT id_pote, nome, especie, data_criacao, agua, nutri FROM potes WHERE id_user = ?", (id_usuario,))
        potes = c.fetchall()
    else:
        potes = []

    potes_list = [{"id_pote": pote[0], "nome": pote[1], "especie": pote[2], "data_criacao": pote[3], "agua": pote[4], "nutri": pote[5]} for pote in potes]

    print(potes_list)

    water_graph = create_graphs(30, "w")
    nutri_graph = create_graphs(70, "n")

    #print(water_graph)
    #print(nutri_graph)
    
    con.close()
    return render_template('profile.html', email=email, name=name, image_base64=image_perfil, potes=potes_list, water_graph=water_graph, nutri_graph=nutri_graph)

@app.route('/new_pote', methods=['GET', 'POST'])
def new_pote():
    con = sqlite3.connect('clients.db')
    c = con.cursor()

    if request.method == 'POST':
        name = request.form.get('name')
        especie = request.form.get('especie')

        email = session['email']

        if not name or not especie:
            return render_template('new_pote.html', error_info="Preencha todos os campos!")

        id_pote = random.randint(10000, 99999)
        data_criacao = datetime.now().strftime("%d/%m/%Y")

        c.execute("SELECT id_user FROM users WHERE email = ?", (email,))
        id_usuario = c.fetchone()

        if id_usuario:
            id_usuario = id_usuario[0]  

            c.execute("INSERT INTO potes (id_pote, nome, especie, data_criacao, id_user) VALUES (?, ?, ?, ?, ?)", (id_pote, name, especie, data_criacao, id_usuario))

            con.commit()
            con.close()

            return redirect(url_for('profile', email=email))
        else:
            con.close()
            return render_template('new_pote.html', email=email, error_info="Erro ao encontrar usuário.")

    return render_template('new_pote.html')

@app.route('/delete_pote/<int:pote_id>', methods=['POST'])
def delete_pote(pote_id):
    con = sqlite3.connect('clients.db')
    c = con.cursor()

    c.execute("DELETE FROM potes WHERE id_pote = ?", (pote_id,))
    con.commit()
    con.close()

    email = session['email']

    return redirect(url_for('profile', email=email))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory('images', filename)

#auxiliar functions
def create_graphs(valor, id):
    if not 0 <= valor <= 100:
        raise ValueError("O valor deve estar entre 0 e 100.")
    
    theta = np.linspace(np.pi, 0, 100)  
    raio_externo = 1
    raio_interno = raio_externo * (1 - 0.3)

    pontos_preenchidos = int(valor * len(theta) / 100)

    theta_preenchido = theta[:pontos_preenchidos]
    theta_restante = theta[pontos_preenchidos:]

    def calcular_coordenadas(raio, theta_valores):
        return raio * np.cos(theta_valores), raio * np.sin(theta_valores)
    
    x_externo_preenchido, y_externo_preenchido = calcular_coordenadas(raio_externo, theta_preenchido)
    x_interno_preenchido, y_interno_preenchido = calcular_coordenadas(raio_interno, theta_preenchido[::-1])
    
    x_externo_restante, y_externo_restante = calcular_coordenadas(raio_externo, theta_restante)
    x_interno_restante, y_interno_restante = calcular_coordenadas(raio_interno, theta_restante[::-1])

    fig, ax = plt.subplots(figsize=(8, 4))

    if id == "w":
        ax.fill(np.concatenate([x_externo_preenchido, x_interno_preenchido]),
                np.concatenate([y_externo_preenchido, y_interno_preenchido]), color='#87CEEB')
    elif id == "n":
        ax.fill(np.concatenate([x_externo_preenchido, x_interno_preenchido]),
                np.concatenate([y_externo_preenchido, y_interno_preenchido]), color='#00FF1E')
        
    ax.fill(np.concatenate([x_externo_restante, x_interno_restante]),
            np.concatenate([y_externo_restante, y_interno_restante]), color='#D3D3D3')

    ax.text(0, 0.2, f"{valor}%", ha='center', va='center', fontsize=55, color='gray', fontweight='bold')

    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_facecolor('#F0F0F0')

    nome_arquivo = f"{id}_{valor}.png"
    caminho_imagem = os.path.join(os.path.dirname(__file__), 'static', 'graphs', nome_arquivo)
    
    os.makedirs(os.path.dirname(caminho_imagem), exist_ok=True)

    plt.savefig(caminho_imagem, bbox_inches='tight', pad_inches=0.5)
    plt.close()

    return f"graphs/{nome_arquivo}"

def choose_image_profile(email):
    pasta = 'images'

    arquivos = os.listdir(pasta)

    imagens = [arquivo for arquivo in arquivos if arquivo.lower().endswith(('.png'))]
    imagem_aleatoria = random.choice(imagens)
    imagem_caminho = os.path.join(pasta, imagem_aleatoria)
    
    con = sqlite3.connect('clients.db')
    c = con.cursor()

    with open(imagem_caminho, 'rb') as file:
        imagem_blob = file.read()

    c.execute("UPDATE users SET profile_pic=? WHERE email=?", (imagem_blob, email,))

    con.commit()
    con.close()

if __name__ == '__main__':
    init_db()   
    app.run(debug=True)

