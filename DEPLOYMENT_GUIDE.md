# 🚀 Deployment Guide për Contabo + cPanel

## 📋 Informacioni i Serverit

- **Server IP:** 195.88.87.62
- **cPanel URL:** https://195.88.87.62:15001/919e11c1
- **Domain:** training.protrade.al
- **Port:** 8501 (Streamlit)

---

## 🔧 Hapat e Deploy-mentit

### Hapi 1: Upload në cPanel

1. **Hyr në cPanel** → File Manager
2. **Shko te:** `/home/username/public_html/` (ose `/public_html/`)
3. **Upload ZIP file:**
   - Kliko "Upload" në cPanel
   - Upload `Analyze-calls.zip`
   - Extract ZIP file (Right-click → Extract)

### Hapi 2: Instalimi i Dependencies

1. **Hyr në Terminal** (cPanel → Terminal):
   ```bash
   cd public_html/Analyze-calls
   
   # Krijo virtual environment
   python3 -m venv venv
   
   # Aktivizo venv
   source venv/bin/activate
   
   # Instalo dependencies
   pip install -r requirements.txt
   ```

### Hapi 3: Konfigurimi i Secrets

1. **Edito `.streamlit/secrets.toml`:**
   ```bash
   nano .streamlit/secrets.toml
   ```

2. **Zëvendëso vlerat:**
   ```toml
   [db]
   host = "65.109.50.236"
   database = "asterisk"
   user = "ShiftAppNew"
   password = "VENDOS_PASSWORD_KETU"
   
   [openai]
   api_key = "VENDOS_OPENAI_KEY_KETU"
   ```

3. **Ruaj file-in** (Ctrl+X, Y, Enter)

### Hapi 4: Testimi i Aplikacionit

1. **Starto aplikacionin:**
   ```bash
   source venv/bin/activate
   streamlit run app.py --server.port 8501 --server.address 0.0.0.0
   ```

2. **Testo në browser:**
   - http://195.88.87.62:8501
   - Ose: http://training.protrade.al:8501

### Hapi 5: Konfigurimi i Domain

1. **Në cPanel → Domains:**
   - Shto domain: `training.protrade.al`
   - Point to: `public_html/Analyze-calls`

2. **Në DNS Settings:**
   - A Record: `training.protrade.al` → `195.88.87.62`

### Hapi 6: SSL/HTTPS (Opsional)

1. **Instalo Let's Encrypt SSL:**
   ```bash
   # Në cPanel → SSL/TLS
   # Kliko "Install SSL Certificate"
   # Zgjidh "Let's Encrypt"
   # Domain: training.protrade.al
   ```

### Hapi 7: Auto-Start me PM2 (Rekomanduar)

1. **Instalo PM2:**
   ```bash
   npm install -g pm2
   ```

2. **Krijo PM2 config:**
   ```bash
   cd public_html/Analyze-calls
   
   # Krijo file: ecosystem.config.js
   nano ecosystem.config.js
   ```

3. **Shto këtë content:**
   ```javascript
   module.exports = {
     apps: [{
       name: 'vicidial-analyzer',
       script: 'venv/bin/streamlit',
       args: 'run app.py --server.port 8501 --server.address 0.0.0.0',
       cwd: '/home/username/public_html/Analyze-calls',
       instances: 1,
       autorestart: true,
       watch: false,
       max_memory_restart: '1G',
       env: {
         NODE_ENV: 'production'
       }
     }]
   }
   ```

4. **Starto me PM2:**
   ```bash
   pm2 start ecosystem.config.js
   pm2 startup
   pm2 save
   ```

### Hapi 8: Firewall Configuration

1. **Hap port 8501:**
   ```bash
   # Në cPanel → Security → Firewall
   # Shto rule: Allow port 8501
   ```

2. **Ose në terminal:**
   ```bash
   ufw allow 8501/tcp
   ufw reload
   ```

---

## 🔒 Siguria

### 1. Secrets Management
- ✅ Mos e ngarko `.streamlit/secrets.toml` në GitHub
- ✅ Përdor environment variables në production
- ✅ Rregullo permissions: `chmod 600 .streamlit/secrets.toml`

### 2. Firewall
```bash
# Lejo vetëm port 8501 dhe 443
ufw allow 8501/tcp
ufw allow 443/tcp
ufw deny 8502/tcp  # Blloko portin e zhvillimit
ufw enable
```

### 3. Rate Limiting
- Konfiguro në cPanel → Security → ModSecurity
- Ose përdor Nginx rate limiting

---

## 📊 Monitoring

### 1. Log Files
```bash
# Streamlit logs
tail -f ~/.pm2/logs/vicidial-analyzer-out.log

# PM2 logs
pm2 logs vicidial-analyzer
```

### 2. Process Status
```bash
pm2 status
pm2 monit
```

### 3. Restart
```bash
pm2 restart vicidial-analyzer
```

---

## 🐛 Troubleshooting

### Problem 1: Port 8501 nuk është i hapur
```bash
# Kontrollo se porti është i hapur
netstat -tulpn | grep 8501

# Nëse jo, hap portin
ufw allow 8501/tcp
```

### Problem 2: Aplikacioni nuk starton
```bash
# Kontrollo logs
pm2 logs vicidial-analyzer --lines 100

# Ose starto manualisht
source venv/bin/activate
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### Problem 3: Database connection failed
```bash
# Testo lidhjen me database
mysql -h 65.109.50.236 -u ShiftAppNew -p asterisk

# Kontrollo credentials në secrets.toml
cat .streamlit/secrets.toml
```

### Problem 4: Domain nuk funksionon
```bash
# Testo DNS
nslookup training.protrade.al

# Kontrollo cPanel DNS settings
# A Record duhet të pointojë tek 195.88.87.62
```

---

## 📞 Support

Nëse ke probleme:
1. Kontrollo logs: `pm2 logs vicidial-analyzer`
2. Verifikimi i ports: `netstat -tulpn | grep 8501`
3. Testo database connection
4. Kontrollo firewall rules

---

## ✅ Checklist për Deploy

- [ ] ZIP file i upload-uar në cPanel
- [ ] ZIP file i extract-uar
- [ ] Virtual environment i krijuar
- [ ] Dependencies të instaluara
- [ ] secrets.toml i konfiguruar
- [ ] Aplikacioni i testuar në port 8501
- [ ] Domain i konfiguruar (training.protrade.al)
- [ ] DNS i konfiguruar
- [ ] SSL i instaluar (opsional)
- [ ] PM2 i konfiguruar për auto-start
- [ ] Firewall i konfiguruar
- [ ] Monitoring i aktivizuar

---

**Data:** 2025-10-19  
**Version:** 1.0  
**Author:** Protrade AI
