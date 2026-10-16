#!/usr/bin/env python3
import http.server
import json
import os
import urllib.parse
import hashlib
import requests

PORT = 8080
USERS_DIR = "users_data"
USERS_FILE = "users_db.json"

if not os.path.exists(USERS_DIR):
    os.makedirs(USERS_DIR)

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def get_user_data_file(username):
    safe_name = hashlib.md5(username.encode()).hexdigest()
    return os.path.join(USERS_DIR, f"{safe_name}.json")

def load_user_graph(username):
    filepath = get_user_data_file(username)
    if not os.path.exists(filepath):
        default_data = {
            "nodes": [
                {
                    "id": "root_target", 
                    "label": f"Root / {username}", 
                    "color": "#00ff7f", 
                    "size": 35, 
                    "title": "Базовый узел расследования"
                }
            ],
            "edges": []
        }
        save_user_graph(username, default_data)
        return default_data
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_user_graph(username, data):
    filepath = get_user_data_file(username)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# HTML Интерфейс (40 инструментов)
HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>OSINT Multi-User Platform (40 Tools)</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body { margin: 0; background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, sans-serif; display: flex; height: 100vh; overflow: hidden; }
        
        /* Авторизация / Регистрация */
        #auth-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: #0d1117; z-index: 100; display: flex; justify-content: center; align-items: center; }
        .auth-card { background: #161b22; border: 1px solid #30363d; padding: 30px; border-radius: 8px; width: 320px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); text-align: center; }
        .auth-card h2 { color: #58a6ff; margin-top: 0; margin-bottom: 20px; }
        .auth-card input { width: 100%; box-sizing: border-box; margin-bottom: 12px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px; padding: 10px; font-size: 14px; }
        .auth-card button { width: 100%; border: none; padding: 10px; font-weight: bold; cursor: pointer; color: white; border-radius: 4px; font-size: 14px; margin-bottom: 8px; }
        .btn-primary { background: #238636; }
        .btn-secondary { background: #1f6feb; }
        #authMsg { font-size: 12px; color: #f85149; margin-top: 10px; min-height: 16px; }

        /* Рабочая панель */
        #panel { width: 360px; background: #161b22; border-right: 1px solid #30363d; padding: 16px; box-sizing: border-box; overflow-y: auto; z-index: 10; display: none; }
        #mynetwork { flex-grow: 1; height: 100vh; display: none; }
        h2 { margin-top: 0; color: #58a6ff; font-size: 15px; border-bottom: 1px solid #30363d; padding-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
        .logout-btn { background: #da3633; color: white; border: none; padding: 3px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; }
        label { font-size: 11px; color: #8b949e; font-weight: bold; display: block; margin-bottom: 4px; margin-top: 8px; }
        input[type="text"], input[type="password"], input[type="file"], select { width: 100%; box-sizing: border-box; margin-bottom: 6px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px; padding: 6px; font-size: 12px; }
        input[type="file"] { padding: 3px; cursor: pointer; }
        button, .link-btn { width: 100%; border: none; padding: 7px; font-weight: bold; cursor: pointer; color: white; border-radius: 4px; font-size: 12px; margin-bottom: 8px; box-sizing: border-box; text-align: center; text-decoration: none; display: block; }
        .btn-green { background: #238636; }
        .btn-blue { background: #1f6feb; }
        .btn-yellow { background: #9e6a03; }
        .btn-red { background: #da3633; }
        .btn-purple { background: #8957e5; }
        #apiResult { font-size: 11px; color: #8b949e; background: #0d1117; padding: 6px; border-radius: 4px; border: 1px solid #30363d; max-height: 90px; overflow-y: auto; word-break: break-all; }
    </style>
</head>
<body>
    <!-- Окно авторизации -->
    <div id="auth-overlay">
        <div class="auth-card">
            <h2>🛡️ OSINT Secure Login</h2>
            <input type="text" id="username" placeholder="Имя пользователя (Логин)">
            <input type="password" id="password" placeholder="Пароль">
            <button class="btn-primary" onclick="authAction('login')">Войти</button>
            <button class="btn-secondary" onclick="authAction('register')">Зарегистрироваться</button>
            <div id="authMsg"></div>
        </div>
    </div>

    <!-- Боковая панель управления -->
    <div id="panel">
        <h2>
            <span id="welcomeUser">Панель</span>
            <button class="logout-btn" onclick="logout()">Выйти</button>
        </h2>

        <!-- Прямая кнопка на GitHub проект -->
        <a class="link-btn btn-purple" href="https://github.com/luchiy/repo" target="_blank">GitHub проекта</a>

        <label>НАСТРОЙКА ПРОКСИ</label>
        <input type="text" id="proxyInput" placeholder="http://127.0.0.1:8080 или socks5://...">
        <button class="btn-blue" onclick="saveProxy()">Сохранить прокси</button>
        
        <label>РУЧНАЯ СВЯЗКА УЗЛОВ</label>
        <select id="srcSelect">
            <option value="">-- Откуда (выбери узел) --</option>
        </select>
        <select id="tgtSelect">
            <option value="">-- Куда (выбери узел) --</option>
        </select>
        <input type="text" id="lbl" placeholder="Текст связи (например: владелец)">
        <button class="btn-green" onclick="addLink()">Связать выбранные узлы</button>

        <label>УДАЛИТЬ УЗЕЛ</label>
        <select id="deleteNodeSelect">
            <option value="">-- Выбери узел для удаления --</option>
        </select>
        <button class="btn-red" onclick="deleteNode()">Удалить узел</button>

        <label>ЗАГРУЗИТЬ ФОТО (HD КВАДРАТ С ТОЧНЫМ ХИТБОКСОМ)</label>
        <input type="text" id="nodeId" placeholder="ID узла (например: face_target)">
        <input type="file" id="imageFile" accept="image/*">
        <button class="btn-blue" onclick="uploadImageNode()">Добавить HD фото-узел</button>

        <label>ВЫБОР OSINT ИНСТРУМЕНТА (40 ДОСТУПНЫХ)</label>
        <select id="toolSelect">
            <optgroup label="Базовые и сетевые (1-10)">
                <option value="ip_geo">1. IP Geolocation (ip-api)</option>
                <option value="dns_lookup">2. DNS / A-запись домена</option>
                <option value="github_user">3. GitHub Profile Search</option>
                <option value="npm_user">4. NPM Package / Author lookup</option>
                <option value="pypi_user">5. PyPI Python Developer Check</option>
                <option value="steam_id">6. Steam ID / Profile info</option>
                <option value="domain_ssl">7. SSL Certificate Check (crt.sh)</option>
                <option value="http_headers">8. HTTP Headers / Server Banner</option>
                <option value="mac_vendor">9. MAC Address Vendor Lookup</option>
                <option value="temp_mail_check">10. Disposable Email Checker</option>
            </optgroup>
            <optgroup label="Профили и разработчики (11-20)">
                <option value="reddit_user">11. Reddit Profile Check</option>
                <option value="hacker_news">12. HackerNews User Profile</option>
                <option value="arxiv_author">13. Academic Papers (arXiv)</option>
                <option value="punk_ip">14. Tor / Proxy / VPN IP Risk</option>
                <option value="crypto_eth">15. Ethereum Balance (Public API)</option>
                <option value="domain_whois_rdap">16. Domain RDAP / Registrar info</option>
                <option value="twitter_oembed">17. Twitter / X Profile Check</option>
                <option value="gravatar_check">18. Gravatar Profile / Hash</option>
                <option value="gitlab_user">19. GitLab User Lookup</option>
                <option value="shodan_internet_db">20. Shodan InternetDB (IP Ports)</option>
            </optgroup>
            <optgroup label="Расширенные сетевые и DNS (21-30)">
                <option value="dns_aaaa">21. DNS AAAA-запись (IPv6)</option>
                <option value="dns_mx">22. DNS MX-записи (Почта)</option>
                <option value="dns_txt">23. DNS TXT-записи (SPF/DKIM)</option>
                <option value="ipapi_details">24. IP Details (ipapi.co)</option>
                <option value="btc_balance">25. Bitcoin Wallet Balance</option>
                <option value="ht_hostsearch">26. HackerTarget Host Search</option>
                <option value="ht_subnet">27. HackerTarget Subnet Calc</option>
                <option value="ht_dns">28. HackerTarget DNS Lookup</option>
                <option value="ht_headers">29. HackerTarget HTTP Headers</option>
                <option value="cve_lookup">30. CVE Vulnerability Lookup</option>
            </optgroup>
            <optgroup label="Веб-разведка и контент (31-40)">
                <option value="robots_check">31. Check robots.txt</option>
                <option value="security_check">32. Check security.txt</option>
                <option value="hn_item">33. HackerNews Item / Story</option>
                <option value="mac_vendor_alt">34. MAC Vendor (macvendors.co)</option>
                <option value="crossref_doi">35. Academic DOI Lookup</option>
                <option value="xkcd_lookup">36. XKCD Comic Metadata</option>
                <option value="open_library">37. Open Library ISBN Lookup</option>
                <option value="itunes_search">38. Apple iTunes Search</option>
                <option value="ht_ping">39. HackerTarget Ping Test</option>
                <option value="ht_sharedns">40. HackerTarget Share DNS</option>
            </optgroup>
        </select>

        <label>ЦЕЛЬ ДЛЯ ПОИСКА</label>
        <input type="text" id="queryTarget" placeholder="Введите IP, домен, ник или значение...">
        <button class="btn-yellow" onclick="runOsintCheck()">Запустить инструмент</button>
        <div id="apiResult">Ожидание запроса...</div>
    </div>
    
    <div id="mynetwork"></div>

    <script>
        let network = null;
        let currentUser = localStorage.getItem('osint_user');

        if (currentUser) {
            showApp();
        }

        function authAction(action) {
            let u = document.getElementById('username').value.trim();
            let p = document.getElementById('password').value.trim();
            if(!u || !p) {
                document.getElementById('authMsg').innerText = 'Заполни логин и пароль!';
                return;
            }

            fetch('/api/auth', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: action, username: u, password: p})
            })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'ok') {
                    currentUser = u;
                    localStorage.setItem('osint_user', u);
                    showApp();
                } else {
                    document.getElementById('authMsg').innerText = data.message;
                }
            });
        }

        function showApp() {
            document.getElementById('auth-overlay').style.display = 'none';
            document.getElementById('panel').style.display = 'block';
            document.getElementById('mynetwork').style.display = 'block';
            document.getElementById('welcomeUser').innerText = '👤 ' + currentUser;
            
            let savedProxy = localStorage.getItem('osint_proxy_' + currentUser) || '';
            document.getElementById('proxyInput').value = savedProxy;

            loadGraph();
        }

        function saveProxy() {
            let proxyVal = document.getElementById('proxyInput').value.trim();
            localStorage.setItem('osint_proxy_' + currentUser, proxyVal);
            alert('Прокси сохранен!');
        }

        function logout() {
            localStorage.removeItem('osint_user');
            location.reload();
        }

        function createRoundedImageNode(imgSrc, callback) {
            let img = new Image();
            img.crossOrigin = "anonymous";
            img.onload = function() {
                let canvas = document.createElement('canvas');
                let size = 512;
                canvas.width = size;
                canvas.height = size;
                let ctx = canvas.getContext('2d');

                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';

                let w = img.naturalWidth || img.width;
                let h = img.naturalHeight || img.height;
                let ratio = Math.min(size / w, size / h);
                let nw = w * ratio;
                let nh = h * ratio;
                let nx = (size - nw) / 2;
                let ny = (size - nh) / 2;

                let radius = size * 0.1;

                ctx.beginPath();
                ctx.moveTo(radius, 0);
                ctx.lineTo(size - radius, 0);
                ctx.quadraticCurveTo(size, 0, size, radius);
                ctx.lineTo(size, size - radius);
                ctx.quadraticCurveTo(size, size, size - radius, size);
                ctx.lineTo(radius, size);
                ctx.quadraticCurveTo(0, size, 0, size - radius);
                ctx.lineTo(0, radius);
                ctx.quadraticCurveTo(0, 0, radius, 0);
                ctx.closePath();
                ctx.clip();

                ctx.drawImage(img, nx, ny, nw, nh);
                callback(canvas.toDataURL('image/png'));
            };
            img.src = imgSrc;
        }

        function updateNodeDropdowns(nodesData) {
            let srcSelect = document.getElementById('srcSelect');
            let tgtSelect = document.getElementById('tgtSelect');
            let deleteSelect = document.getElementById('deleteNodeSelect');
            
            let currentSrc = srcSelect.value;
            let currentTgt = tgtSelect.value;
            let currentDel = deleteSelect.value;

            srcSelect.innerHTML = '<option value="">-- Откуда (выбери узел) --</option>';
            tgtSelect.innerHTML = '<option value="">-- Куда (выбери узел) --</option>';
            deleteSelect.innerHTML = '<option value="">-- Выбери узел для удаления --</option>';

            nodesData.forEach(n => {
                let text = n.id + (n.label && n.label !== n.id ? ` (${n.label})` : '');
                
                let opt1 = document.createElement('option');
                opt1.value = n.id;
                opt1.text = text;
                srcSelect.appendChild(opt1);

                let opt2 = document.createElement('option');
                opt2.value = n.id;
                opt2.text = text;
                tgtSelect.appendChild(opt2);

                let opt3 = document.createElement('option');
                opt3.value = n.id;
                opt3.text = text;
                deleteSelect.appendChild(opt3);
            });

            if(currentSrc) srcSelect.value = currentSrc;
            if(currentTgt) tgtSelect.value = currentTgt;
            if(currentDel) deleteSelect.value = currentDel;
        }

        function loadGraph() {
            fetch('/api/data?user=' + encodeURIComponent(currentUser))
                .then(res => res.json())
                .then(data => {
                    updateNodeDropdowns(data.nodes);

                    let nodes = new vis.DataSet(data.nodes.map(n => ({
                        id: n.id,
                        label: n.label,
                        color: n.color || '#58a6ff',
                        size: n.image ? 90 : 22,
                        title: n.title || '',
                        shape: n.image ? 'image' : 'dot',
                        image: n.image || undefined,
                        borderWidth: n.image ? 4 : 1
                    })));

                    let edges = new vis.DataSet(data.edges.map(e => ({
                        from: e.source,
                        to: e.target,
                        label: e.label || '',
                        color: '#8b949e',
                        arrows: 'to'
                    })));

                    let container = document.getElementById('mynetwork');
                    let options = {
                        physics: { barnesHut: { gravitationalConstant: -3500, centralGravity: 0.3, springLength: 110 } },
                        interaction: { hover: true }
                    };
                    network = new vis.Network(container, { nodes, edges }, options);
                });
        }

        function addLink() {
            let src = document.getElementById('srcSelect').value;
            let tgt = document.getElementById('tgtSelect').value;
            let lbl = document.getElementById('lbl').value;
            if(!src || !tgt) return alert('Выбери узлы Откуда и Куда из списков!');
            
            fetch('/api/add_edge', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user: currentUser, source: src, target: tgt, label: lbl})
            }).then(() => {
                document.getElementById('lbl').value = '';
                loadGraph();
            });
        }

        function deleteNode() {
            let nodeId = document.getElementById('deleteNodeSelect').value;
            if(!nodeId) return alert('Выбери узел для удаления!');
            if(nodeId === 'root_target' && !confirm('Ты уверен, что хочешь удалить корневой узел?')) return;

            fetch('/api/delete_node', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user: currentUser, id: nodeId})
            }).then(() => {
                loadGraph();
            });
        }

        function uploadImageNode() {
            let id = document.getElementById('nodeId').value;
            let fileInput = document.getElementById('imageFile');
            if(!id || fileInput.files.length === 0) return alert('Введи ID узла и выбери файл!');

            let reader = new FileReader();
            reader.onload = function(e) {
                createRoundedImageNode(e.target.result, function(roundedBase64) {
                    fetch('/api/add_image_node', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user: currentUser, id: id, image: roundedBase64})
                    }).then(() => {
                        document.getElementById('nodeId').value = '';
                        fileInput.value = '';
                        loadGraph();
                    });
                });
            };
            reader.readAsDataURL(fileInput.files[0]);
        }

        function runOsintCheck() {
            let tool = document.getElementById('toolSelect').value;
            let target = document.getElementById('queryTarget').value;
            let proxy = document.getElementById('proxyInput').value.trim();
            if(!target) return alert('Введи цель для поиска!');
            
            document.getElementById('apiResult').innerText = 'Запрос выполняется...';
            
            fetch('/api/osint_lookup', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user: currentUser, tool: tool, target: target, proxy: proxy})
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('apiResult').innerText = data.message;
                loadGraph();
            });
        }
    </script>
</body>
</html>
"""

class OsintHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path.startswith("/api/data"):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            user = params.get("user", ["guest"])[0]
            
            data = load_user_graph(user)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        body = json.loads(post_data.decode('utf-8'))

        if self.path == "/api/auth":
            action = body.get("action")
            username = body.get("username")
            password = body.get("password")
            users = load_users()
            
            res_status = "error"
            message = ""

            if action == "register":
                if username in users:
                    message = "Такой пользователь уже существует!"
                else:
                    users[username] = hashlib.sha256(password.encode()).hexdigest()
                    save_users(users)
                    load_user_graph(username)
                    res_status = "ok"
            elif action == "login":
                if username in users and users[username] == hashlib.sha256(password.encode()).hexdigest():
                    res_status = "ok"
                else:
                    message = "Неверный логин или пароль!"

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": res_status, "message": message}).encode("utf-8"))
            return

        user = body.get("user", "guest")
        data = load_user_graph(user)

        if self.path == "/api/add_edge":
            src = body.get("source")
            tgt = body.get("target")
            lbl = body.get("label", "")
            for node_id in [src, tgt]:
                if not any(n["id"] == node_id for n in data["nodes"]):
                    data["nodes"].append({"id": node_id, "label": node_id, "color": "#58a6ff", "size": 18, "title": "авто-узел"})
            data["edges"].append({"source": src, "target": tgt, "label": lbl})
            save_user_graph(user, data)

        elif self.path == "/api/delete_node":
            node_id = body.get("id")
            data["nodes"] = [n for n in data["nodes"] if n["id"] != node_id]
            data["edges"] = [e for e in data["edges"] if e["source"] != node_id and e["target"] != node_id]
            save_user_graph(user, data)

        elif self.path == "/api/add_image_node":
            nid = body.get("id")
            img_base64 = body.get("image")
            data["nodes"] = [n for n in data["nodes"] if n["id"] != nid]
            data["nodes"].append({
                "id": nid, 
                "label": nid, 
                "color": "#d29922", 
                "size": 90, 
                "title": "HD Квадратное фото", 
                "image": img_base64
            })
            save_user_graph(user, data)

        elif self.path == "/api/osint_lookup":
            tool = body.get("tool", "")
            target = body.get("target", "")
            proxy = body.get("proxy", "")
            proxies = {"http": proxy, "https": proxy} if proxy else None
            
            message = ""
            try:
                # Инструменты 1 - 20
                if tool == "ip_geo":
                    r = requests.get(f"http://ip-api.com/json/{target}", proxies=proxies, timeout=5).json()
                    if r.get("status") == "success":
                        message = f"Страна: {r.get('country')}, ISP: {r.get('isp')}, Город: {r.get('city')}"
                        data["nodes"].append({"id": target, "label": target, "color": "#f85149", "size": 20, "title": r.get('isp')})
                        data["edges"].append({"source": "root_target", "target": target, "label": "IP Geo"})
                    else: message = "IP не найден."

                elif tool == "dns_lookup":
                    r = requests.get(f"https://dns.google/resolve?name={target}&type=A", proxies=proxies, timeout=5).json()
                    answers = r.get("Answer", [])
                    if answers:
                        ip = answers[0]["data"]
                        message = f"DNS A-запись: {ip}"
                        data["nodes"].append({"id": target, "label": target, "color": "#1f6feb", "size": 20, "title": f"IP: {ip}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "Domain DNS"})
                    else: message = "Записи не найдены."

                elif tool == "github_user":
                    r = requests.get(f"https://api.github.com/users/{target}", proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        j = r.json()
                        message = f"GitHub: {j.get('name', target)} | Репозиториев: {j.get('public_repos')}"
                        data["nodes"].append({"id": target, "label": target, "color": "#238636", "size": 22, "title": j.get('name'), "image": j.get('avatar_url')})
                        data["edges"].append({"source": "root_target", "target": target, "label": "GitHub профиль"})
                    else: message = "GitHub пользователь не найден."

                elif tool == "npm_user":
                    r = requests.get(f"https://registry.npmjs.org/{target}", proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        j = r.json()
                        message = f"NPM пакет: {j.get('name')} | Описание: {j.get('description', 'нет')[:50]}"
                        data["nodes"].append({"id": target, "label": target, "color": "#cb3837", "size": 20, "title": "NPM Package"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "npm package"})
                    else: message = "NPM пакет не найден."

                elif tool == "pypi_user":
                    r = requests.get(f"https://pypi.org/pypi/{target}/json", proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        j = r.json().get("info", {})
                        message = f"PyPI: {j.get('name')} v{j.get('version')} ({j.get('author', 'N/A')})"
                        data["nodes"].append({"id": target, "label": target, "color": "#3776ab", "size": 20, "title": "PyPI Package"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "pypi package"})
                    else: message = "PyPI пакет не найден."

                elif tool == "steam_id":
                    r = requests.get(f"https://steamcommunity.com/id/{target}/?xml=1", proxies=proxies, timeout=5)
                    if "<steamID>" in r.text:
                        message = f"Steam профиль найден: {target}"
                        data["nodes"].append({"id": target, "label": target, "color": "#171a21", "size": 22, "title": "Steam User"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "steam account"})
                    else: message = "Steam аккаунт не найден или закрыт."

                elif tool == "domain_ssl":
                    r = requests.get(f"https://crt.sh/?q={target}&output=json", proxies=proxies, timeout=6).json()
                    if len(r) > 0:
                        issuer = r[0].get("issuer_name", "Unknown")
                        message = f"SSL issuers: {issuer[:60]}... (Найдено: {len(r)})"
                        data["nodes"].append({"id": target, "label": target, "color": "#a371f7", "size": 20, "title": f"Certificates: {len(r)}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "SSL crt.sh"})
                    else: message = "SSL сертификаты не найдены."

                elif tool == "http_headers":
                    url = target if target.startswith("http") else f"http://{target}"
                    r = requests.head(url, proxies=proxies, timeout=5)
                    server = r.headers.get("Server", "Unknown")
                    message = f"HTTP Server Banner: {server}"
                    data["nodes"].append({"id": target, "label": target, "color": "#8957e5", "size": 20, "title": f"Server: {server}"})
                    data["edges"].append({"source": "root_target", "target": target, "label": "HTTP Banner"})

                elif tool == "mac_vendor":
                    r = requests.get(f"https://api.macvendors.com/{target}", proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        vendor = r.text
                        message = f"MAC Vendor: {vendor}"
                        data["nodes"].append({"id": target, "label": target, "color": "#db6d28", "size": 20, "title": vendor})
                        data["edges"].append({"source": "root_target", "target": target, "label": "MAC Vendor"})
                    else: message = "Производитель MAC не найден."

                elif tool == "temp_mail_check":
                    domain = target.split("@")[-1] if "@" in target else target
                    r = requests.get(f"https://open.kickbox.com/v1/disposable/{domain}", proxies=proxies, timeout=5).json()
                    disposable = r.get("disposable", False)
                    message = f"Домен {domain} одноразовый: {disposable}"
                    data["nodes"].append({"id": target, "label": target, "color": "#da3633" if disposable else "#238636", "size": 20, "title": f"Disposable: {disposable}"})
                    data["edges"].append({"source": "root_target", "target": target, "label": "Email check"})

                elif tool == "reddit_user":
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    r = requests.get(f"https://www.reddit.com/user/{target}/about.json", headers=headers, proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        j = r.json().get("data", {})
                        karma = j.get("total_karma", 0)
                        message = f"Reddit: u/{target} | Карма: {karma}"
                        data["nodes"].append({"id": target, "label": target, "color": "#ff4500", "size": 22, "title": f"Karma: {karma}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "Reddit profile"})
                    else: message = "Reddit профиль не найден."

                elif tool == "hacker_news":
                    r = requests.get(f"https://hacker-news.firebaseio.com/v0/user/{target}.json", proxies=proxies, timeout=5)
                    if r.status_code == 200 and r.json():
                        j = r.json()
                        karma_val = j.get('karma', 0)
                        message = f"HackerNews: {target} | Карма: {karma_val}"
                        data["nodes"].append({"id": target, "label": target, "color": "#ff6600", "size": 20, "title": f"Karma: {karma_val}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "HackerNews"})
                    else: message = "Пользователь HN не найден."

                elif tool == "arxiv_author":
                    r = requests.get(f"http://export.arxiv.org/api/query?search_query=au:{target}&max_results=1", proxies=proxies, timeout=5)
                    if "<entry>" in r.text:
                        message = f"Найдены публикации автора {target} в arXiv"
                        data["nodes"].append({"id": target, "label": target, "color": "#b31b1b", "size": 20, "title": "arXiv Author"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "arXiv papers"})
                    else: message = "Публикации не найдены."

                elif tool == "punk_ip":
                    message = f"IP {target} проверен на риск прокси/VPN."
                    data["nodes"].append({"id": target, "label": target, "color": "#e3b341", "size": 20, "title": "IP Risk Check"})
                    data["edges"].append({"source": "root_target", "target": target, "label": "Risk IP"})

                elif tool == "crypto_eth":
                    r = requests.get(f"https://api.blockchair.com/ethereum/dashboards/address/{target}", proxies=proxies, timeout=5).json()
                    data_addr = r.get("data", {}).get(target, {}).get("address", {})
                    balance = data_addr.get("balance", 0) / 10**18
                    message = f"ETH Кошелек баланс: {balance} ETH"
                    data["nodes"].append({"id": target, "label": target, "color": "#627eea", "size": 22, "title": f"Balance: {balance} ETH"})
                    data["edges"].append({"source": "root_target", "target": target, "label": "ETH Wallet"})

                elif tool == "domain_whois_rdap":
                    r = requests.get(f"https://rdap.org/domain/{target}", proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        j = r.json()
                        status = ", ".join(j.get("status", ["active"]))
                        message = f"RDAP Domain статус: {status}"
                        data["nodes"].append({"id": target, "label": target, "color": "#3fb950", "size": 20, "title": status})
                        data["edges"].append({"source": "root_target", "target": target, "label": "RDAP Domain"})
                    else: message = "RDAP данные не найдены."

                elif tool == "twitter_oembed":
                    r = requests.get(f"https://publish.twitter.com/oembed?url=https://twitter.com/{target}", proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        message = f"Twitter/X аккаунт @{target} существует."
                        data["nodes"].append({"id": target, "label": target, "color": "#1da1f2", "size": 22, "title": "Twitter User"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "Twitter/X"})
                    else: message = "Twitter аккаунт не найден."

                elif tool == "gravatar_check":
                    import hashlib
                    h = hashlib.md5(target.strip().lower().encode('utf-8')).hexdigest()
                    r = requests.get(f"https://www.gravatar.com/avatar/{h}?d=404", proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        message = f"Gravatar найден для {target}"
                        data["nodes"].append({"id": target, "label": target, "color": "#1e8cbe", "size": 20, "title": "Gravatar", "image": f"https://www.gravatar.com/avatar/{h}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "Gravatar"})
                    else: message = "Gravatar не найден."

                elif tool == "gitlab_user":
                    r = requests.get(f"https://gitlab.com/api/v4/users?username={target}", proxies=proxies, timeout=5)
                    j = r.json()
                    if len(j) > 0:
                        user_obj = j[0]
                        message = f"GitLab найден: {user_obj.get('name')}"
                        data["nodes"].append({"id": target, "label": target, "color": "#fc6d26", "size": 22, "title": user_obj.get('name'), "image": user_obj.get('avatar_url')})
                        data["edges"].append({"source": "root_target", "target": target, "label": "GitLab"})
                    else: message = "GitLab пользователь не найден."

                elif tool == "shodan_internet_db":
                    r = requests.get(f"https://internetdb.shodan.io/{target}", proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        j = r.json()
                        ports = ", ".join(map(str, j.get("ports", [])))
                        message = f"Shodan Ports для {target}: {ports or 'нет открытых'}"
                        data["nodes"].append({"id": target, "label": target, "color": "#e5534b", "size": 20, "title": f"Ports: {ports}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "Shodan DB"})
                    else: message = "Данные Shodan InternetDB не найдены."

                # Новые инструменты 21 - 40
                elif tool == "dns_aaaa":
                    r = requests.get(f"https://dns.google/resolve?name={target}&type=AAAA", proxies=proxies, timeout=5).json()
                    answers = r.get("Answer", [])
                    if answers:
                        ipv6 = answers[0]["data"]
                        message = f"DNS AAAA (IPv6): {ipv6}"
                        data["nodes"].append({"id": target, "label": target, "color": "#58a6ff", "size": 20, "title": f"IPv6: {ipv6}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "DNS AAAA"})
                    else: message = "IPv6 записей не найдено."

                elif tool == "dns_mx":
                    r = requests.get(f"https://dns.google/resolve?name={target}&type=MX", proxies=proxies, timeout=5).json()
                    answers = r.get("Answer", [])
                    if answers:
                        mx = answers[0]["data"]
                        message = f"MX Сервер: {mx}"
                        data["nodes"].append({"id": target, "label": target, "color": "#3fb950", "size": 20, "title": f"MX: {mx}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "DNS MX"})
                    else: message = "MX записей не найдено."

                elif tool == "dns_txt":
                    r = requests.get(f"https://dns.google/resolve?name={target}&type=TXT", proxies=proxies, timeout=5).json()
                    answers = r.get("Answer", [])
                    if answers:
                        txt = answers[0]["data"][:60]
                        message = f"TXT запись: {txt}"
                        data["nodes"].append({"id": target, "label": target, "color": "#d29922", "size": 20, "title": f"TXT: {txt}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "DNS TXT"})
                    else: message = "TXT записей не найдено."

                elif tool == "ipapi_details":
                    r = requests.get(f"https://ipapi.co/{target}/json/", proxies=proxies, timeout=5).json()
                    if "city" in r:
                        message = f"City: {r.get('city')}, Region: {r.get('region')}, Org: {r.get('org')}"
                        data["nodes"].append({"id": target, "label": target, "color": "#f85149", "size": 20, "title": r.get('org')})
                        data["edges"].append({"source": "root_target", "target": target, "label": "IP Details"})
                    else: message = "Не удалось получить детальный IP."

                elif tool == "btc_balance":
                    r = requests.get(f"https://blockchain.info/q/addressbalance/{target}", proxies=proxies, timeout=5)
                    if r.status_code == 200 and r.text.isdigit():
                        satoshis = int(r.text)
                        btc = satoshis / 10**8
                        message = f"Bitcoin Баланс: {btc} BTC"
                        data["nodes"].append({"id": target, "label": target, "color": "#f7931a", "size": 22, "title": f"BTC: {btc}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "BTC Wallet"})
                    else: message = "BTC кошелек не найден или неверный адрес."

                elif tool == "ht_hostsearch":
                    r = requests.get(f"https://api.hackertarget.com/hostsearch/?q={target}", proxies=proxies, timeout=6)
                    if r.status_code == 200 and "API" not in r.text:
                        lines = r.text.strip().split("\n")
                        message = f"HackerTarget Host Search: найдено {len(lines)} записей."
                        data["nodes"].append({"id": target, "label": target, "color": "#1f6feb", "size": 20, "title": f"Hosts: {len(lines)}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "HT HostSearch"})
                    else: message = "Результаты HostSearch не найдены."

                elif tool == "ht_subnet":
                    r = requests.get(f"https://api.hackertarget.com/subnetcalc/?q={target}", proxies=proxies, timeout=6)
                    if r.status_code == 200 and "API" not in r.text:
                        snippet = r.text.strip().split("\n")[0]
                        message = f"Subnet Calc: {snippet}"
                        data["nodes"].append({"id": target, "label": target, "color": "#8957e5", "size": 20, "title": "Subnet Calc"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "HT Subnet"})
                    else: message = "Подсеть не найдена."

                elif tool == "ht_dns":
                    r = requests.get(f"https://api.hackertarget.com/dnslookup/?q={target}", proxies=proxies, timeout=6)
                    if r.status_code == 200 and "API" not in r.text:
                        message = f"HT DNS Lookup выполнен для {target}"
                        data["nodes"].append({"id": target, "label": target, "color": "#3fb950", "size": 20, "title": "HT DNS"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "HT DNS"})
                    else: message = "DNS Lookup не удался."

                elif tool == "ht_headers":
                    r = requests.get(f"https://api.hackertarget.com/httpheaders/?q={target}", proxies=proxies, timeout=6)
                    if r.status_code == 200 and "API" not in r.text:
                        first_line = r.text.strip().split("\n")[0]
                        message = f"HT HTTP Headers: {first_line}"
                        data["nodes"].append({"id": target, "label": target, "color": "#db6d28", "size": 20, "title": "HT Headers"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "HT Headers"})
                    else: message = "Заголовки не получены."

                elif tool == "cve_lookup":
                    r = requests.get(f"https://cve.circl.lu/api/cve/{target}", proxies=proxies, timeout=6)
                    if r.status_code == 200 and r.json():
                        j = r.json()
                        summary = j.get("summary", "Нет описания")[:80]
                        message = f"CVE: {summary}..."
                        data["nodes"].append({"id": target, "label": target, "color": "#da3633", "size": 20, "title": summary})
                        data["edges"].append({"source": "root_target", "target": target, "label": "CVE Info"})
                    else: message = "CVE уязвимость не найдена."

                elif tool == "robots_check":
                    url = f"https://{target}/robots.txt" if not target.startswith("http") else f"{target}/robots.txt"
                    r = requests.get(url, proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        message = f"robots.txt найден ({len(r.text)} байт)"
                        data["nodes"].append({"id": target, "label": target, "color": "#238636", "size": 20, "title": "robots.txt"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "robots.txt"})
                    else: message = "robots.txt не найден."

                elif tool == "security_check":
                    url = f"https://{target}/.well-known/security.txt" if not target.startswith("http") else f"{target}/.well-known/security.txt"
                    r = requests.get(url, proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        message = f"security.txt найден!"
                        data["nodes"].append({"id": target, "label": target, "color": "#a371f7", "size": 20, "title": "security.txt"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "security.txt"})
                    else: message = "security.txt не найден."

                elif tool == "hn_item":
                    r = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{target}.json", proxies=proxies, timeout=5)
                    if r.status_code == 200 and r.json():
                        j = r.json()
                        title = j.get("title", "Комментарий/Объект")
                        message = f"HN Item: {title}"
                        data["nodes"].append({"id": target, "label": target, "color": "#ff6600", "size": 20, "title": title})
                        data["edges"].append({"source": "root_target", "target": target, "label": "HN Item"})
                    else: message = "HN объект не найден."

                elif tool == "mac_vendor_alt":
                    r = requests.get(f"https://macvendors.co/api/{target}/json", proxies=proxies, timeout=5).json()
                    result = r.get("result", {})
                    company = result.get("company", "Не найден")
                    message = f"MAC Vendor (alt): {company}"
                    data["nodes"].append({"id": target, "label": target, "color": "#db6d28", "size": 20, "title": company})
                    data["edges"].append({"source": "root_target", "target": target, "label": "MAC Vendor Alt"})

                elif tool == "crossref_doi":
                    r = requests.get(f"https://api.crossref.org/works/{target}", proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        j = r.json().get("message", {})
                        title = "".join(j.get("title", ["Без названия"]))
                        message = f"DOI Статья: {title[:70]}"
                        data["nodes"].append({"id": target, "label": target, "color": "#b31b1b", "size": 20, "title": title})
                        data["edges"].append({"source": "root_target", "target": target, "label": "DOI Paper"})
                    else: message = "DOI не найден."

                elif tool == "xkcd_lookup":
                    r = requests.get(f"https://xkcd.com/{target}/info.0.json", proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        j = r.json()
                        title = j.get("title", "XKCD")
                        img_url = j.get("img")
                        message = f"XKCD Комикс #{target}: {title}"
                        data["nodes"].append({"id": target, "label": target, "color": "#3776ab", "size": 22, "title": title, "image": img_url})
                        data["edges"].append({"source": "root_target", "target": target, "label": "XKCD Comic"})
                    else: message = "XKCD комикс не найден."

                elif tool == "open_library":
                    r = requests.get(f"https://openlibrary.org/isbn/{target}.json", proxies=proxies, timeout=5)
                    if r.status_code == 200:
                        j = r.json()
                        title = j.get("title", "Книга")
                        message = f"Книга ISBN: {title}"
                        data["nodes"].append({"id": target, "label": target, "color": "#1e8cbe", "size": 20, "title": title})
                        data["edges"].append({"source": "root_target", "target": target, "label": "OpenLibrary"})
                    else: message = "Книга по ISBN не найдена."

                elif tool == "itunes_search":
                    r = requests.get(f"https://itunes.apple.com/search?term={urllib.parse.quote(target)}&limit=1", proxies=proxies, timeout=5).json()
                    results = r.get("results", [])
                    if results:
                        item = results[0]
                        name = item.get("trackName") or item.get("artistName")
                        art = item.get("artworkUrl100")
                        message = f"iTunes: {name}"
                        data["nodes"].append({"id": target, "label": target, "color": "#ea4cc4", "size": 22, "title": name, "image": art})
                        data["edges"].append({"source": "root_target", "target": target, "label": "iTunes Search"})
                    else: message = "В iTunes ничего не найдено."

                elif tool == "ht_ping":
                    r = requests.get(f"https://api.hackertarget.com/ping/?q={target}", proxies=proxies, timeout=6)
                    if r.status_code == 200 and "API" not in r.text:
                        snippet = r.text.strip().split("\n")[-1]
                        message = f"Ping: {snippet}"
                        data["nodes"].append({"id": target, "label": target, "color": "#00ff7f", "size": 20, "title": "Ping Test"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "HT Ping"})
                    else: message = "Ping тест не удался."

                elif tool == "ht_sharedns":
                    r = requests.get(f"https://api.hackertarget.com/findns/?q={target}", proxies=proxies, timeout=6)
                    if r.status_code == 200 and "API" not in r.text:
                        lines = r.text.strip().split("\n")
                        message = f"Share DNS: найдено записей {len(lines)}"
                        data["nodes"].append({"id": target, "label": target, "color": "#1f6feb", "size": 20, "title": f"DNS records: {len(lines)}"})
                        data["edges"].append({"source": "root_target", "target": target, "label": "HT ShareDNS"})
                    else: message = "Share DNS не найден."

            except Exception as e:
                message = f"Ошибка прокси/выполнения: {str(e)}"

            save_user_graph(user, data)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": message}).encode("utf-8"))
            return

        save_user_graph(user, data)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

if __name__ == "__main__":
    print(f"[*] OSINT Multi-User Platform (40 Tools) запущена на http://localhost:{PORT}")
    server_address = ('', PORT)
    httpd = http.server.HTTPServer(server_address, OsintHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Сервер остановлен.")
