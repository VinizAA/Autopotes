from flask import Flask, request, jsonify, render_template, Response
import json
from datetime import datetime
from queue import Queue
import threading
import time

app = Flask(__name__)
data_queue = Queue()
clients = []
latest_data = {"temp": 0, "hum": 0, "timestamp": ""}

# Função para enviar dados para todos os clientes conectados
def send_to_clients(data):
    for client in list(clients):
        try:
            client.put(data)
        except:
            clients.remove(client)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['POST'])
def receive_data():
    global latest_data
    if request.method == 'POST':
        data = request.json
        
        # Adicionar timestamp
        data["timestamp"] = datetime.now().strftime("%H:%M:%S")
        latest_data = data
        
        # Notificar todos os clientes
        send_to_clients(data)
        
        print(f"Dados recebidos: {data}")
        return jsonify({"status": "sucesso", "mensagem": "Dados recebidos"}), 200

@app.route('/stream')
def stream():
    def generate():
        # Criar uma fila para este cliente
        client_queue = Queue()
        clients.append(client_queue)
        
        # Enviar dados iniciais se disponíveis
        if latest_data["timestamp"]:
            yield f"data: {json.dumps(latest_data)}\n\n"
        
        try:
            while True:
                # Obter novos dados da fila do cliente
                data = client_queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        except GeneratorExit:
            # Remover cliente quando a conexão for fechada
            if client_queue in clients:
                clients.remove(client_queue)
    
    return Response(generate(), content_type='text/event-stream')

if __name__ == '__main__':
    # Criar a pasta templates se não existir
    import os
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Criar o arquivo HTML
    with open('templates/index.html', 'w') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Monitor de Dados do ESP32</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            background-color: white;
        }
        .card h2 {
            margin-top: 0;
            color: #333;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        .data-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            font-size: 18px;
            padding: 10px;
            border-radius: 4px;
            background-color: #f9f9f9;
        }
        .value {
            font-weight: bold;
            color: #007bff;
        }
        .timestamp {
            text-align: right;
            font-size: 14px;
            color: #666;
            margin-top: 15px;
        }
        .update-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #ccc;
            margin-left: 10px;
        }
        .update-indicator.active {
            background-color: #4CAF50;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .connection-status {
            text-align: center;
            padding: 5px;
            margin-bottom: 15px;
            border-radius: 4px;
            font-size: 14px;
        }
        .connected {
            background-color: #dff0d8;
            color: #3c763d;
        }
        .disconnected {
            background-color: #f2dede;
            color: #a94442;
        }
    </style>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const statusElement = document.getElementById('connection-status');
            const indicatorElement = document.getElementById('update-indicator');
            let eventSource;
            
            function connectEventSource() {
                // Fechar conexão existente se houver
                if (eventSource) {
                    eventSource.close();
                }
                
                // Conectar ao evento SSE do servidor
                eventSource = new EventSource('/stream');
                
                eventSource.onopen = function() {
                    statusElement.textContent = "Conectado ao servidor";
                    statusElement.className = "connection-status connected";
                };
                
                eventSource.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        
                        // Atualizar os valores na página
                        document.getElementById('temperatura').textContent = data.temp.toFixed(1);
                        document.getElementById('umidade').textContent = data.hum.toFixed(1);
                        document.getElementById('timestamp').textContent = data.timestamp;
                        
                        // Mostrar indicador de atualização
                        indicatorElement.classList.add('active');
                        setTimeout(() => {
                            indicatorElement.classList.remove('active');
                        }, 1000);
                        
                        // Mostrar animação de atualização
                        const card = document.querySelector('.card');
                        card.style.transition = 'background-color 0.3s';
                        card.style.backgroundColor = '#f0f8ff';
                        setTimeout(() => {
                            card.style.backgroundColor = 'white';
                        }, 300);
                    } catch (e) {
                        console.error("Erro ao processar dados:", e);
                    }
                };
                
                eventSource.onerror = function() {
                    statusElement.textContent = "Desconectado - Tentando reconectar...";
                    statusElement.className = "connection-status disconnected";
                    
                    // Tentar reconectar após alguns segundos
                    setTimeout(connectEventSource, 5000);
                };
            }
            
            // Iniciar conexão
            connectEventSource();
            
            // Verificar conexão a cada 30 segundos
            setInterval(function() {
                if (eventSource.readyState === EventSource.CLOSED) {
                    statusElement.textContent = "Conexão perdida - Reconectando...";
                    statusElement.className = "connection-status disconnected";
                    connectEventSource();
                }
            }, 30000);
        });
    </script>
</head>
<body>
    <h1>Monitor de Dados do ESP32</h1>
    
    <div id="connection-status" class="connection-status">Conectando ao servidor...</div>
    
    <div class="card">
        <h2>Leituras do Sensor</h2>
        <div class="data-row">
            <span>Temperatura:</span>
            <span class="value"><span id="temperatura">--</span>°C</span>
        </div>
        <div class="data-row">
            <span>Umidade:</span>
            <span class="value"><span id="umidade">--</span>%</span>
        </div>
        <div class="timestamp">
            Última atualização: <span id="timestamp">--</span>
            <div id="update-indicator" class="update-indicator"></div>
        </div>
    </div>
</body>
</html>""")
    
    # Iniciar o servidor
    print("Servidor iniciado em http://0.0.0.0:5000")
    print("Para ver o endereço IP do servidor, verifique o resultado de 'ipconfig' (Windows) ou 'ifconfig' (Linux/Mac)")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)