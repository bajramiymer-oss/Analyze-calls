# 🚀 Quick Start Guide për ChatGPT Agent

## 📋 Informacioni i Serverit

- **Server IP:** 195.88.87.62
- **cPanel URL:** https://195.88.87.62:15001/919e11c1
- **Domain:** training.protrade.al
- **Port:** 8501

---

## 🎯 Hapat e Deploy-mentit (Për Agent)

### 1️⃣ Upload në cPanel

```
1. Hyr në cPanel: https://195.88.87.62:15001/919e11c1
2. Shko te File Manager
3. Navigo te: /home/username/public_html/
4. Upload: Analyze-calls.zip
5. Right-click → Extract
```

### 2️⃣ Instalimi (Terminal në cPanel)

```bash
cd public_html/Analyze-calls

# Krijo virtual environment
python3 -m venv venv

# Aktivizo venv
source venv/bin/activate

# Instalo dependencies
pip install -r requirements.txt
```

### 3️⃣ Konfigurimi

```bash
# Edito secrets.toml
nano .streamlit/secrets.toml

# Zëvendëso këto vlera:
[db]
host = "65.109.50.236"
database = "asterisk"
user = "ShiftAppNew"
password = "VENDOS_PASSWORD_KETU"

[openai]
api_key = "VENDOS_OPENAI_KEY_KETU"

# Ruaj: Ctrl+X, Y, Enter
```

### 4️⃣ Starto Aplikacionin

```bash
# Opsioni 1: Manual
source venv/bin/activate
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# Opsioni 2: Me PM2 (Rekomanduar)
npm install -g pm2
pm2 start 'source venv/bin/activate && streamlit run app.py --server.port 8501 --server.address 0.0.0.0' --name vicidial-analyzer
pm2 startup
pm2 save
```

### 5️⃣ Testo

```
Open browser:
http://195.88.87.62:8501
http://training.protrade.al:8501
```

---

## 🔧 Konfigurimi i Domain

### Në cPanel:

1. **Domains** → **Add Domain**
2. Domain: `training.protrade.al`
3. Document Root: `/home/username/public_html/Analyze-calls`

### DNS Settings:

```
A Record: training.protrade.al → 195.88.87.62
```

---

## 🔒 SSL (Opsional)

```bash
# Në cPanel → SSL/TLS
1. Kliko "Install SSL Certificate"
2. Zgjidh "Let's Encrypt"
3. Domain: training.protrade.al
4. Install
```

---

## 📊 Monitoring

```bash
# PM2 Status
pm2 status

# Logs
pm2 logs vicidial-analyzer

# Restart
pm2 restart vicidial-analyzer
```

---

## ⚠️ Troubleshooting

### Port nuk është i hapur:
```bash
ufw allow 8501/tcp
```

### Aplikacioni nuk starton:
```bash
pm2 logs vicidial-analyzer --lines 100
```

### Database connection failed:
```bash
# Testo lidhjen
mysql -h 65.109.50.236 -u ShiftAppNew -p asterisk
```

---

## ✅ Checklist

- [ ] ZIP uploaded në cPanel
- [ ] ZIP extracted
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] secrets.toml configured
- [ ] Application started
- [ ] Domain configured
- [ ] DNS configured
- [ ] SSL installed (opsional)
- [ ] PM2 configured

---

**Koha e vlerësuar:** 15-20 minuta  
**Vështirësia:** Mesatare  
**Kërkesat:** SSH access, Python 3.9+, MySQL client
