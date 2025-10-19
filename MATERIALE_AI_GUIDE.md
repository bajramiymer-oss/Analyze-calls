# 🤖 Udhëzues për Materiale AI

## Përmbledhje

Moduli **Materiale AI** është një veçori e re e shtuar në **Tools** që përdor inteligjencën artificiale për të gjeneruar materiale trajnimi dhe shitjeje bazuar në analiz reale të telefonatave.

## Veçoritë Kryesore

### 1️⃣ Lloje Materialesh

#### 🎯 Objeksione & Përgjigje Konsultative
- Ekstrakton **minimum 10 objeksione** unike nga telefonatat
- Kategorizon objeksionet: Çmim, Kohë, Konkurrencë, Dyshim, Nevoja, Teknike
- Për çdo objeksion jep:
  - **Prevention**: Si ta parandalosh që objeksioni të lindet
  - **Value Building**: Si të ndërtosh vlerë përpara se të flasësh për zgjidhje
  - **Response Framework**: Struktura e përgjigjes (jo vetëm teksti)
  - **Example Dialogue**: Shembull konkret dialogu (3-5 shkëmbime)
- Jep strategji të përgjithshme dhe rekomandime për flow

#### 📝 Skript Shitjeje
Gjeneron skript të plotë me:
- **Opening** - Hapje me impact + variacionet + tips
- **Discovery** - Pyetje kyçe, pikë dëgjimi, sinjale paralajmëruese
- **Presentation** - Value proposition, përfitime, prova, storytelling
- **Objection Handling** - Framework dhe shembuj
- **Closing** - Mbyllje kryesore + alternative + next steps
- **Key Phrases** - Fraza që funksionojnë mirë
- **Tone Guidelines** - Si duhet të jetë toni
- **Do/Don't** - Çfarë të bësh/mos bësh

#### ❓ FAQ (Pyetje të Shpeshta)
- Ekstrakton pyetjet më të shpeshta nga klientët
- Kategorizon pyetjet
- Jep përgjigje të shkurtra dhe të detajuara
- Tregon frekuencën e çdo pyetjeje

#### ⭐ Best Practices
- Ekstrakton praktikat më të mira nga telefonatat e suksesshme
- Kategorizon: Hapje, Zbulim, Prezantim, Mbyllje, Ton
- Shpjegon pse funksionon çdo praktikë
- Jep shembuj konkretë
- Tregon vështirësinë e implementimit
- Jep pattern-e të top performers
- Lista e gabimeve që duhen shmangur
- Rekomandime për trajnim

---

## Si të Përdoresh

### Hapi 1: Zgjedh Llojin e Materialit

Hap faqen **Tools** → Tab **🤖 Materiale AI**

Zgjedh njërin nga:
- 🎯 Objeksione & Përgjigje Konsultative
- 📝 Skript Shitjeje
- ❓ FAQ (Pyetje të Shpeshta)
- ⭐ Best Practices

---

### Hapi 2: Zgjedh Projektin/Fushatën (Opsional)

Nëse ke krijuar **Kampanja/Projekte** në Settings, mund t'i përzgjedhësh për të marrë kontekstin dhe dokumentet e projektit.

**Përfitimet:**
- AI-ja përdor kontekstin e biznesit për materiale më të përshtatur
- Dokumentet e ngarkuara (PDF/DOCX) përdoren si referencë
- Output-i është më i personalizuar për projektin specifik

**Opsioni:**
- "Asnjë (pa kontekst specifik)" - nëse nuk ke projekt ose nuk dëshiron kontekst

---

### Hapi 3: Zgjedh Burimin e të Dhënave

Ke 2 opsione:

#### A) 📁 Transkripte ekzistuese (folder lokal)
Nëse ke tashmë transkripte të ruajtura:

1. Vendos path-in e folderit (default: `out_analysis`)
2. Zgjedh nëse dëshiron të kërkosh edhe në nënfolderat
3. Kliko **"🔍 Gjej transkriptet"**
4. Kontrollo listën e transkripteve të gjetura

**Kujdes:** Analizohen **TË GJITHA** transkriptet e gjetura (jo limit).

#### B) 🎙️ Regjistrime nga DB (download + transkriptim automatik)
Nëse dëshiron të shkarkosh direkt nga Vicidial:

1. Zgjedh databazën (DB1 ose DB2)
2. Vendos filtrat:
   - Data fillimit/mbarimit + ora
   - Fushata Vicidial (opsional)
   - Kohëzgjatja min/max (sekonda)
   - Maksimumi i regjistrimeve
3. Vendos kredencialet Basic Auth (nëse duhen)
4. Kliko **"⬇️ Shkarko & Transkripto"**

**Procesi:**
1. Shkarkimi i regjistrimeve nga DB
2. Transkriptimi automatik me OpenAI Whisper/GPT-4o
3. Ruajtja në session përkohësor

---

### Hapi 4: Instruksione Shtesë (Opsionale)

Në këtë fushë mund të japësh udhëzime specifike për AI-në:

**Shembuj:**
- "Fokuso tek objeksionet teknike"
- "Përfshi shembuj konkretë me numra"
- "Ton profesional por miqësor"
- "Jep më shumë rëndësi mbylljes"
- "Adapto për klientë B2B në vend të B2C"

**Zgjedh gjuhën:**
- 🇦🇱 Shqip
- 🇮🇹 Italisht
- 🇬🇧 Anglisht

---

### Hapi 5: Gjenero Materialin

Kliko **"🚀 Gjenero Materialin"**

AI-ja do të:
1. Lexojë të gjitha transkriptet
2. Kombinojë kontekstin e projektit + dokumentet
3. Aplikojë instruksionet shtesë
4. Gjenerojë materialin në gjuhën e zgjedhur

**Koha e procesimit:**
- 10-50 transkripte: ~30-60 sekonda
- 50-200 transkripte: ~1-3 minuta
- 200+ transkripte: ~3-5 minuta

---

### Hapi 6: Shiko Rezultatin

Rezultati shfaqet në format të strukturuar në UI:

#### Për Objeksione:
- Lista e objeksioneve me expansion panels
- Detaje për çdo objeksion (category, frequency, context)
- Qasja konsultative (prevention, value building, response, dialogue)
- Strategji e përgjithshme
- Rekomandime për call flow

#### Për Skript:
- Seksionet e skriptit (Opening, Discovery, Presentation, etc.)
- Sub-seksione me detaje
- Key phrases dhe tone guidelines
- Do/Don't list

#### Për FAQ:
- Lista e pyetjeve me përgjigje
- Kategorizim
- Frekuencë

#### Për Best Practices:
- Lista e praktikave
- Shpjegime dhe shembuj
- Pattern-e të top performers
- Gabime që duhen shmangur

---

### Hapi 7: Eksporto Materialin

Tre formate eksportimi:

#### 📄 DOCX (Word Document)
- Format profesional me headers dhe structure
- I lehtë për edit dhe print
- Ideal për dokumente zyrtare trajnimi

#### 📋 JSON
- Format i strukturuar për integrimi me sisteme të tjera
- Ideal për procesim automatik
- Ruhen të gjitha metadata

#### 📝 TXT
- Format i thjeshtë teksti
- I lehtë për share via email
- Kompatibël me çdo platformë

**Download Button:** Pas eksportimit, shfaqet buton për të shkarkuar file-in direkt.

---

## Best Practices për Përdorim

### 1. Përzgjedh transkripte cilësore
- **Minimum 20-30 transkripte** për rezultate të mira
- **50-100+ transkripte** për rezultate optimale
- Përfshi transkripte nga agentë të ndryshëm (të mirë dhe të dobët)
- Sigurohu që transkriptet janë të plota (jo fragmente)

### 2. Përdor kontekst projekti
- Krijo kampanjë në Settings dhe ngarko dokumente
- Dokumentet mund të jenë: script ekzistues, objection handling, product info
- Sa më shumë kontekst, aq më të personalizuara materialet

### 3. Jep instruksione specifike
- Mos u kufizohu në instruksione gjenerike
- Specifikoja tonat, audiencën, objektivat
- Përshkruaj sfidën kryesore që po përballon

### 4. Kontrollo dhe adapto rezultatin
- AI-ja jep rekomandime të mira, por jo perfekte
- Review-o rezultatin me ekspertë të shitjeve
- Adapto për kulturën dhe stilin e kompanisë

### 5. Përdite periodikisht
- Gjenero materiale çdo muaj ose çdo tremujor
- Shiko evolucionin e objeksioneve dhe praktikave
- Adapto trajnimet bazuar në rezultate të reja

---

## Shembuj Përdorimi

### Rast 1: Trajnim për Agentë të Rinj

**Qëllimi:** Krijo materiale trajnimi për onboarding.

**Hapat:**
1. Zgjedh **"📝 Skript Shitjeje"**
2. Zgjedh projektin e kampanjës
3. Ngarko transkripte nga top performers (50+)
4. Instruksione shtesë: "Skript i thjeshtë dhe i qartë për agentë të rinj, me fokus tek opening dhe discovery"
5. Gjuha: Shqip
6. Gjenero → Eksporto si DOCX

**Rezultat:** Skript i strukturuar që përdoret në trajnime.

---

### Rast 2: Përmirësim Objection Handling

**Qëllimi:** Identifiko objeksionet kryesore dhe trajno ekipin.

**Hapat:**
1. Zgjedh **"🎯 Objeksione & Përgjigje"**
2. Zgjedh projektin
3. Shkarko regjistrime nga 2 javët e fundit (200+ calls)
4. Instruksione: "Fokuso tek objeksionet e çmimit dhe konkurrencës"
5. Gjenero → Shiko rezultatin
6. Eksporto si DOCX dhe distribuoj te team

**Rezultat:** Dokument me 10+ objeksione dhe qasje konsultative për çdo objeksion.

---

### Rast 3: FAQ për Website/Support

**Qëllimi:** Krijo FAQ për website bazuar në pyetjet reale të klientëve.

**Hapat:**
1. Zgjedh **"❓ FAQ"**
2. Zgjedh projektin
3. Ngarko transkripte nga 1 muaji (100+)
4. Instruksione: "Përfshi vetëm pyetjet më të shpeshta, përgjigje të shkurtra dhe profesionale"
5. Gjuha: Anglisht (nëse website është në anglisht)
6. Gjenero → Eksporto si JSON për integrimin në website

---

### Rast 4: Quality Monitoring

**Qëllimi:** Identifiko praktikat e mira dhe ato që duhen përmirësuar.

**Hapat:**
1. Zgjedh **"⭐ Best Practices"**
2. Zgjedh projektin
3. Ngarko transkripte nga top 20% e agjentëve (50+)
4. Instruksione: "Fokuso tek toni, empatia dhe mbyllja"
5. Gjenero
6. Krahazo me praktikat aktuale

**Rezultat:** Lista e praktikave që duhen promovuar + gabime që duhen shmangur.

---

## Limitime dhe Konsiderata

### Kostot API
- Çdo gjenerim përdor OpenAI API (GPT-4o)
- Sa më shumë transkripte, aq më i lartë kostoja
- **Rekomandim:** Përdor 50-200 transkripte për balancë cost/quality

### Cilësia e Input
- Transkriptet e dobëta → rezultate të dobëta
- Sigurohu që transkriptet janë të lexueshme
- Shmang transkripte me shumë noise ose gabime

### Gjuha
- AI-ja funksionon më mirë në anglisht
- Shqip dhe italisht funksionojnë mirë por mund të kenë nuanca
- Kontrollo rezultatin për consistency

### Personalizimi
- Rezultati është starting point, jo final product
- Review-o dhe adapto për nevojat specifike
- Kombinim i AI suggestions me expertise njerëzore

---

## Troubleshooting

### Problem: "Nuk u gjend asnjë transkript"
**Zgjidhje:**
- Kontrollo path-in e folderit
- Sigurohu që ka file .txt në folder
- Aktivizo "Përfshi nënfolderat"

### Problem: "Gabim gjatë gjenerimit"
**Zgjidhje:**
- Kontrollo OPENAI_API_KEY në secrets
- Sigurohu që ke balance në API account
- Redukto numrin e transkripteve nëse janë shumë të gjata

### Problem: Rezultati nuk është në gjuhën e zgjedhur
**Zgjidhje:**
- Re-gjenero materialin
- Shto në instruksione: "DUHET të jetë 100% në [gjuha]"

### Problem: Objeksionet janë më pak se 10
**Zgjidhje:**
- Shto më shumë transkripte për analiz
- Sigurohu që transkriptet përmbajnë objeksione reale
- Modifiko instruksionet: "Gjej minimum 15 objeksione unike"

---

## Integrimi me Pipeline

Materiale AI është një modul standalone, por integrohet mirë me:

1. **Pipeline Komplet** - Përdor transkriptet e gjeneruara automatikisht
2. **Settings → Campaigns** - Përdor kontekstin dhe dokumentet e kampanjave
3. **Raporte** - Eksporto materialet dhe bashkangjitji me raporte cilësie

---

## Zhvillime të Ardhshme

- [ ] Training Scenarios Generator
- [ ] Competitive Analysis (krahasim me konkurrencë)
- [ ] Personalized Coaching Plans (për çdo agjent)
- [ ] A/B Testing Scripts (gjenero variante skriptesh)
- [ ] Voice Tone Analysis Integration

---

## Support

Për probleme ose pyetje:
1. Kontrollo këtë dokumentacion
2. Shiko logs në Streamlit console
3. Kontakto Protrade AI Support

---

**Version:** 1.0
**Last Updated:** 2025-10-15
**Author:** Protrade AI








