from flask import Flask, render_template, request, redirect, url_for, session, flash # Removido make_response, send_from_directory se não usados explicitamente
import sqlite3, base64, os, random, io # Removido requests, re, smtplib se não usados explicitamente
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import numpy as np
from datetime import datetime, timedelta
from PIL import Image
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.secret_key = "senhasecreta" # Para produção, use uma chave mais forte e considere variável de ambiente

app.permanent_session_lifetime = timedelta(minutes=30)

# --- Credenciais de Administrador (Defina os valores corretos aqui!) ---
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"
# --- Fim das Credenciais de Administrador ---

# --- Configuração de Caminhos Dinâmicos ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Diretório raiz da aplicação
DB_PATH = os.path.join(BASE_DIR, 'clients.db') # Caminho para o banco de dados
PROFILE_IMAGES_DIR = os.path.join(BASE_DIR, 'images') # Caminho para imagens de perfil (pasta 'images')
# --- Fim da Configuração de Caminhos ---

def init_db():
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id_user INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, password TEXT, email TEXT, profile_pic BLOB)")
    c.execute("CREATE TABLE IF NOT EXISTS potes (id_pote INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, especie TEXT, data_criacao DATETIME, agua INTEGER, nutri INTEGER, w_graph BLOB, n_graph BLOB, id_user INTEGER, FOREIGN KEY(id_user) REFERENCES users(id_user) ON DELETE CASCADE)")
    con.commit()
    con.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_email, error_password = None, None
    form_email = request.form.get('email', '') if request.method == 'POST' else ''

    if request.method == 'POST':
        email_submitted = request.form['email'].strip() # Adicionado .strip()
        password_submitted = request.form['password']

        if email_submitted == ADMIN_USER and password_submitted == ADMIN_PASSWORD:
            session.permanent = True
            session['id'] = 0
            session['name'] = "Administrador"
            session['email'] = ADMIN_USER # Usar a constante
            session['is_admin'] = True
            flash("Login de administrador bem-sucedido!", "success")
            return redirect(url_for('admin_dashboard'))

        con = None
        try:
            con = sqlite3.connect(DB_PATH)
            c = con.cursor()
            c.execute("SELECT id_user, full_name, email, password FROM users WHERE email=?", (email_submitted,))
            user_record = c.fetchone()

            if user_record:
                user_id_db, full_name_db, email_db_from_select, password_db = user_record
                if password_submitted == password_db:
                    session.permanent = True
                    session['id'] = user_id_db
                    session['name'] = full_name_db
                    session['email'] = email_db_from_select
                    session['is_admin'] = False
                    return redirect(url_for('profile', email_param=session['email']))
                else:
                    error_password = "Senha incorreta!"
            else:
                error_email = "Usuário não cadastrado! Crie sua conta agora."
        except sqlite3.Error as e:
            flash("Ocorreu um erro ao tentar fazer login. Por favor, tente novamente.", "danger")
        finally:
            if con:
                con.close()

    return render_template('login.html', error_password=error_password, error_email=error_email, email=form_email)

@app.route('/register', methods=['GET', 'POST'])
def register():
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()
    error_password = None
    error_user = None
    success_message = None
    full_name_form = request.form.get('full_name', '')
    email_form = request.form.get('email', '')

    if request.method == 'POST':
        # full_name_form já pego acima
        password = request.form['password']
        conf_password = request.form['conf_password']
        # email_form já pego acima, mas vamos pegar de novo e com .strip()
        email_form = request.form['email'].strip()

        if password == conf_password:
            valid_password = True
        else:
            valid_password = False
            error_password = "Senhas precisam ser iguais!"

        if full_name_form and password and email_form and valid_password:
            c.execute("SELECT * FROM users WHERE email=? ", (email_form, ))
            if c.fetchone() is not None:
                error_user = "Usuário já existe!"
            else:
                image_blob = choose_image_profile(email_form, return_blob=True)
                c.execute("INSERT INTO users (full_name, password, email, profile_pic) VALUES (?,?,?,?)",
                          (full_name_form, password, email_form, image_blob))
                con.commit()
                success_message = "Cadastro realizado com sucesso!"
        elif not valid_password and not error_password:
             error_password = "Senhas precisam ser iguais!"

    con.close()
    return render_template('register.html', error_user=error_user, error_password=error_password,
                           success_message=success_message, full_name=full_name_form, email=email_form)

@app.route('/profile/<email_param>')
def profile(email_param):
    water_graph, nutri_graph = None, None
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("SELECT full_name, profile_pic FROM users WHERE email=?", (email_param,))
    row = c.fetchone()

    if row:
        name, image_blob = row
        image_perfil = base64.b64encode(image_blob).decode('utf-8') if image_blob else None
    else:
        name = "Usuário não encontrado"
        image_perfil = None
        potes_list = []
        con.close()
        flash("Usuário do perfil não encontrado.", "warning")
        return redirect(url_for('home'))

    c.execute("SELECT id_user FROM users WHERE email = ?", (email_param,))
    id_usuario_data = c.fetchone()
    id_usuario = id_usuario_data[0] if id_usuario_data else None

    if id_usuario:
        c.execute("SELECT id_pote, nome, especie, data_criacao, agua, nutri FROM potes WHERE id_user = ?", (id_usuario,))
        potes_db = c.fetchall()
    else:
        potes_db = []

    if id_usuario:
        for pote_data_tuple in potes_db:
            id_pote_loop, _, _, _, agua_val, nutri_val = pote_data_tuple
            create_graphs(agua_val if agua_val is not None else 0, "w", id_pote_loop, con, c)
            create_graphs(nutri_val if nutri_val is not None else 0, "n", id_pote_loop, con, c)

    potes_list = []
    if id_usuario:
        c.execute("SELECT id_pote, nome, especie, data_criacao, agua, nutri, w_graph, n_graph FROM potes WHERE id_user = ?", (id_usuario,))
        potes_com_graficos = c.fetchall()
        for pote_info in potes_com_graficos:
            id_pote, nome_pote, especie_pote, data_criacao_pote, agua_pote, nutri_pote, w_graph_blob, n_graph_blob = pote_info
            water_graph_b64 = base64.b64encode(w_graph_blob).decode('utf-8') if w_graph_blob else None
            nutri_graph_b64 = base64.b64encode(n_graph_blob).decode('utf-8') if n_graph_blob else None
            potes_list.append({"id_pote": id_pote, "nome": nome_pote, "especie": especie_pote, "data_criacao": data_criacao_pote, "agua": agua_pote, "nutri": nutri_pote, "water_graph": water_graph_b64, "nutri_graph": nutri_graph_b64})

    con.close()
    return render_template('profile.html', email=email_param, name=name, image_base64=image_perfil, potes=potes_list)

@app.route('/new_pote', methods=['GET', 'POST'])
def new_pote():
    if 'email' not in session:
        flash("Você precisa estar logado para adicionar um novo pote.", "warning")
        return redirect(url_for('login'))

    con = sqlite3.connect(DB_PATH)
    c = con.cursor()
    name_val = request.form.get('name', '') if request.method == 'POST' else ''
    especie_val = request.form.get('especie', '') if request.method == 'POST' else ''

    if request.method == 'POST':
        name = request.form.get('name')
        especie = request.form.get('especie')
        current_user_email = session['email']

        if not name or not especie:
            flash("Preencha todos os campos!", "warning")
            return render_template('new_pote.html', name_val=name, especie_val=especie)

        fuso_horario_sp = ZoneInfo("America/Sao_Paulo")
        data = datetime.now(fuso_horario_sp)

        data_criacao = data.strftime("%d/%m/%Y")
        c.execute("SELECT id_user FROM users WHERE email = ?", (current_user_email,))
        id_usuario_data = c.fetchone()

        if id_usuario_data:
            id_usuario = id_usuario_data[0]
            c.execute("INSERT INTO potes (nome, especie, data_criacao, id_user, agua, nutri) VALUES (?, ?, ?, ?, ?, ?)", (name, especie, data_criacao, id_usuario, 0, 0))
            con.commit()
            new_pote_id = c.lastrowid
            if new_pote_id:
                create_graphs(0, "w", new_pote_id, con, c)
                create_graphs(0, "n", new_pote_id, con, c)

            flash("Novo pote adicionado com sucesso!", "success")
            con.close()
            return redirect(url_for('profile', email_param=current_user_email))
        else:
            flash("Erro ao encontrar usuário.", "error")
            con.close()
            return render_template('new_pote.html', error_info="Erro ao encontrar usuário.", name_val=name, especie_val=especie)

    con.close()
    return render_template('new_pote.html')

@app.route('/delete_pote/<int:pote_id>', methods=['POST'])
def delete_pote(pote_id):
    if 'email' not in session:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for('login'))

    con = sqlite3.connect(DB_PATH)
    c = con.cursor()
    c.execute("SELECT potes.id_pote FROM potes JOIN users ON potes.id_user = users.id_user WHERE potes.id_pote = ? AND users.email = ?", (pote_id, session['email']))
    pote_do_usuario = c.fetchone()

    if pote_do_usuario:
        c.execute("DELETE FROM potes WHERE id_pote = ?", (pote_id,))
        con.commit()
        flash("Pote deletado com sucesso!", "success")
    else:
        flash("Não foi possível deletar o pote. Acesso não autorizado ou pote não encontrado.", "error")

    con.close()
    return redirect(url_for('profile', email_param=session['email']))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        flash("Acesso não autorizado. Apenas administradores podem acessar esta página.", "danger")
        return redirect(url_for('login'))

    con = None
    processed_users = []
    processed_potes = []
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        c = con.cursor()

        c.execute("SELECT id_user, full_name, email, profile_pic FROM users ORDER BY id_user")
        users_data = c.fetchall()
        for user_row in users_data:
            user_dict = dict(user_row)
            if user_dict['profile_pic']:
                user_dict['profile_pic_b64'] = base64.b64encode(user_dict['profile_pic']).decode('utf-8')
            else:
                user_dict['profile_pic_b64'] = None
            processed_users.append(user_dict)

        c.execute("SELECT p.id_pote, p.nome AS nome_pote, p.especie, p.data_criacao, p.agua, p.nutri, u.full_name AS nome_usuario, u.email AS email_usuario FROM potes p JOIN users u ON p.id_user = u.id_user ORDER BY p.id_pote")
        potes_data = c.fetchall()
        processed_potes = [dict(pote_row) for pote_row in potes_data]

    except sqlite3.Error as e:
        flash(f"Erro ao acessar o banco de dados no dashboard: {e}", "danger")
    finally:
        if con:
            con.close()

    current_year = datetime.now().year
    return render_template('admin_dashboard.html',
                           users=processed_users,
                           potes=processed_potes,
                           current_year=current_year)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if not session.get('is_admin'):
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    if user_id == session.get('id'):
        flash("Você não pode deletar sua própria conta de administrador.", "warning")
        return redirect(url_for('admin_dashboard'))

    con = None
    try:
        con = sqlite3.connect(DB_PATH)
        c = con.cursor()
        c.execute("SELECT full_name FROM users WHERE id_user = ?", (user_id,))
        user_to_delete = c.fetchone()

        if user_to_delete:
            user_name_to_delete = user_to_delete[0]
            c.execute("DELETE FROM users WHERE id_user = ?", (user_id,))
            con.commit()
            flash(f"Usuário '{user_name_to_delete}' (ID: {user_id}) e todos os seus dados foram deletados com sucesso.", "success")
        else:
            flash(f"Usuário com ID {user_id} não encontrado.", "warning")
    except sqlite3.Error as e:
        flash(f"Erro de banco de dados ao tentar deletar usuário: {e}", "danger")
    except Exception as e_general:
        flash(f"Ocorreu um erro inesperado: {e_general}", "danger")
    finally:
        if con:
            con.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/get_sensor_data', methods=['POST'])
def get_sensor_data():
    if not request.is_json:
        return jsonify({"error": "A requisição deve ser JSON"}), 415
    data = request.get_json()
    items_to_process = []
    if isinstance(data, dict):
        items_to_process = [data]
    elif isinstance(data, list):
        items_to_process = data
    else:
        return jsonify({"error": "Esperado uma lista ou um objeto JSON"}), 400

    con = sqlite3.connect(DB_PATH)
    c = con.cursor()
    success_count = 0
    error_messages = []

    for item in items_to_process:
        pote_id = item.get("id")
        umidade_str = item.get("umidade")
        nutrientes_str = item.get("nutrientes")
        email_sensor = item.get("email")

        if None in (pote_id, umidade_str, nutrientes_str, email_sensor):
            error_messages.append(f"Dados incompletos para um dos itens (ID: {pote_id or 'N/A'})")
            continue

        try:
            umidade = int(umidade_str)
            nutrientes = int(nutrientes_str)
            if not (0 <= umidade <= 100 and 0 <= nutrientes <= 100):
                error_messages.append(f"Valores de umidade/nutrientes fora do intervalo (0-100) para pote_id {pote_id}")
                continue
        except ValueError:
            error_messages.append(f"Valores de umidade/nutrientes inválidos (não numéricos) para pote_id {pote_id}")
            continue

        c.execute("SELECT potes.id_pote FROM potes JOIN users ON potes.id_user = users.id_user WHERE potes.id_pote = ? AND users.email = ?", (pote_id, email_sensor))
        result = c.fetchone()

        if not result:
            error_messages.append(f"Pote {pote_id} não encontrado ou não pertence ao usuário {email_sensor}")
            continue

        c.execute("UPDATE potes SET agua = ?, nutri = ? WHERE id_pote = ?", (umidade, nutrientes, pote_id))
        create_graphs(umidade, "w", pote_id, con, c)
        create_graphs(nutrientes, "n", pote_id, con, c)
        success_count += 1

    con.close()

    if error_messages:
        if success_count > 0:
            return jsonify({"message": f"{success_count} potes atualizados com sucesso, mas ocorreram erros.", "errors": error_messages}), 207
        else:
            return jsonify({"error": "Falha ao processar todos os itens.", "errors": error_messages}), 400

    return jsonify({"message": "Dados recebidos e processados com sucesso!"}), 200

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'id' not in session:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for('login'))

    con = sqlite3.connect(DB_PATH)
    c = con.cursor()
    password_input = request.form.get('password')
    user_id = session['id']
    current_user_email = session['email']

    c.execute("SELECT password, full_name, profile_pic FROM users WHERE id_user = ?", (user_id,))
    user_db_data = c.fetchone()

    if not user_db_data:
        con.close()
        session.clear()
        flash("Usuário não encontrado.", "error")
        return redirect(url_for('login'))

    password_user, name_user, image_blob_user = user_db_data

    if password_input == password_user:
        c.execute("DELETE FROM users WHERE id_user = ?", (user_id,))
        con.commit()
        flash("Conta deletada com sucesso!", "success")
        session.clear()
        con.close()
        return redirect(url_for('home'))
    else:
        image_base64 = base64.b64encode(image_blob_user).decode('utf-8') if image_blob_user else None
        c.execute("SELECT id_pote, nome, especie, data_criacao, w_graph, n_graph, agua, nutri FROM potes WHERE id_user = ?", (user_id,))
        potes_db = c.fetchall()
        potes = []
        for p_data in potes_db:
            potes.append({
                'id_pote': p_data[0], 'nome': p_data[1], 'especie': p_data[2],
                'data_criacao': p_data[3],
                'water_graph': base64.b64encode(p_data[4]).decode('utf-8') if p_data[4] else None,
                'nutri_graph': base64.b64encode(p_data[5]).decode('utf-8') if p_data[5] else None,
                'agua': p_data[6], 'nutri': p_data[7],
            })
        error_message = "Senha incorreta! Tente novamente."
        con.close()
        return render_template(
            'profile.html', error_message=error_message, email=current_user_email,
            name=name_user, image_base64=image_base64, potes=potes
        )

# --- Funções Auxiliares ---
def create_graphs(valor, id_tipo, id_pote, con, c):
    if valor is None:
        valor = 0
    try:
        valor = int(valor)
    except (ValueError, TypeError):
        valor = 0
    if not 0 <= valor <= 100:
        valor = max(0, min(100, valor))

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

    fig, ax = plt.subplots(figsize=(1.2, 0.6))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)


    if id_tipo == "w":
        ax.fill(np.concatenate([x_externo_preenchido, x_interno_preenchido]),
                np.concatenate([y_externo_preenchido, y_interno_preenchido]), color='#87CEEB')
    elif id_tipo == "n":
        ax.fill(np.concatenate([x_externo_preenchido, x_interno_preenchido]),
                np.concatenate([y_externo_preenchido, y_interno_preenchido]), color='#00FF1E')

    ax.fill(np.concatenate([x_externo_restante, x_interno_restante]),
            np.concatenate([y_externo_restante, y_interno_restante]), color='#D3D3D3', alpha=0.5) # Fundo cinza mais transparente

    ax.set_aspect('equal')
    ax.axis('off')

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', transparent=True, bbox_inches='tight', pad_inches=0.05) # pad_inches ajustado
    img_buffer.seek(0)
    img_data = img_buffer.getvalue()
    plt.close(fig)

    coluna = "w_graph" if id_tipo == "w" else "n_graph"
    try:
        c.execute(f"UPDATE potes SET {coluna} = ? WHERE id_pote = ?", (img_data, id_pote))
        con.commit()
    except sqlite3.Error as e:
        print(f"Erro ao atualizar gráfico no BD para pote {id_pote}, coluna {coluna}: {e}")

def choose_image_profile(email_param, return_blob=False):
    if not os.path.exists(PROFILE_IMAGES_DIR):
        print(f"AVISO: Pasta de imagens de perfil não encontrada em {PROFILE_IMAGES_DIR}. Tentando criar.")
        try:
            os.makedirs(PROFILE_IMAGES_DIR)
            print(f"Pasta {PROFILE_IMAGES_DIR} criada. Por favor, adicione 'perfil_nulo.jpg' e outras imagens.")
        except OSError as e:
            print(f"ERRO CRÍTICO: Não foi possível criar a pasta {PROFILE_IMAGES_DIR}: {e}")
            return None # Não pode prosseguir sem a pasta

    # Lista de imagens padrão ou um nome de imagem padrão
    default_image_name = "perfil_nulo.jpg" # Garanta que este arquivo exista na pasta PROFILE_IMAGES_DIR

    arquivos = []
    if os.path.exists(PROFILE_IMAGES_DIR): # Verifica novamente após tentativa de criação
        arquivos = os.listdir(PROFILE_IMAGES_DIR)

    imagens_disponiveis = [arquivo for arquivo in arquivos if arquivo.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if imagens_disponiveis:
        imagem_aleatoria_nome = random.choice(imagens_disponiveis)
    else:
        print(f"Nenhuma imagem encontrada em {PROFILE_IMAGES_DIR}, usando imagem padrão '{default_image_name}'.")
        imagem_aleatoria_nome = default_image_name

    imagem_caminho = os.path.join(PROFILE_IMAGES_DIR, imagem_aleatoria_nome)

    try:
        with open(imagem_caminho, 'rb') as file:
            imagem_blob_data = file.read()
    except FileNotFoundError:
        return None

    if return_blob:
        return imagem_blob_data

    return None

if __name__ == '__main__':
    if not os.path.exists(PROFILE_IMAGES_DIR):
        try:
            os.makedirs(PROFILE_IMAGES_DIR)
        except OSError as e:
            print(f"Não foi possível criar a pasta {PROFILE_IMAGES_DIR}: {e}")

    init_db()
    app.run(host='0.0.0.0', port=2001)

