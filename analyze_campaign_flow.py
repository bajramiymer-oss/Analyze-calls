"""
Analizë e Flow-it të Telefonatës në Vicidial
Analizon fushatën "1234" dhe shpjegon si kalon telefonata deri tek operatori
"""

import pymysql
from typing import Dict, Any, Optional

# Konfigurimi i database
DB_CONFIG = {
    "host": "95.217.87.125",  # Ose 65.109.50.236
    "user": "crmuser",  # Ose ShiftAppNew
    "password": "N3w_CRM@2024!",  # Ose gshkjdhdbkjTRST26564#$%@$DCYJ
    "database": "asterisk",
    "charset": "utf8mb4"
}

def get_connection():
    """Krijon lidhjen me database"""
    return pymysql.connect(**DB_CONFIG)

def get_campaign_info(campaign_id: str) -> Optional[Dict[str, Any]]:
    """Merr informacionin e fushatës"""
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Merr fushatën
        cur.execute("""
            SELECT * FROM vicidial_campaigns
            WHERE campaign_id = %s
        """, (campaign_id,))
        campaign = cur.fetchone()

        if not campaign:
            print(f"❌ Fushatë '{campaign_id}' nuk u gjet!")
            return None

        print(f"✅ Fushatë e gjetur: {campaign_id}")
        print(f"   Emri: {campaign.get('campaign_name', 'N/A')}")
        print(f"   Përshkrimi: {campaign.get('campaign_description', 'N/A')}")
        print(f"   Dial Method: {campaign.get('dial_method', 'N/A')}")
        print(f"   Active: {campaign.get('active', 'N/A')}")
        print(f"   Campaign CID: {campaign.get('campaign_cid', 'N/A')}")

        return campaign
    except Exception as e:
        print(f"❌ Gabim në lidhje me database: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_campaign_settings(campaign_id: str):
    """Merr konfigurimet e fushatës"""
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Merr konfigurimet
        cur.execute("""
            SELECT * FROM vicidial_campaigns
            WHERE campaign_id = %s
        """, (campaign_id,))
        settings = cur.fetchone()

        if not settings:
            return None

        print("\n" + "="*60)
        print("📋 KONFIGURIMET E FUSHATËS")
        print("="*60)

        # Dial Method (Metoda e Thirrjes)
        dial_method = settings.get('dial_method', 'MANUAL')
        print(f"\n📞 Dial Method: {dial_method}")
        print(f"   - MANUAL: Operatori e bën vetë thirrjen")
        print(f"   - RATIO: Ration dialing (thirrje automatik në raport)")
        print(f"   - ADAPT: Adaptive dialing (adaptiv)")
        print(f"   - ADAPT_HARD_LIMIT: Adaptive me limit të fortë")
        print(f"   - ADAPT_TAPERED: Adaptive i ngushtuar")

        # Campaign Status
        print(f"\n📊 Campaign Status: {settings.get('campaign_status', 'N/A')}")

        # Auto Dial Level
        auto_dial_level = settings.get('auto_dial_level', 'N/A')
        print(f"\n🎚️ Auto Dial Level: {auto_dial_level}")
        print(f"   - 0.0 - 1.0: Raporti i agjentëve të lirë vs. lead-eve")
        print(f"   - Më i lartë = më shumë thirrje automatik")

        # Drop Call Seconds
        drop_call_seconds = settings.get('drop_call_seconds', 'N/A')
        print(f"\n⏱️ Drop Call Seconds: {drop_call_seconds}")
        print(f"   - Kohëzgjatja minimale për të konsideruar thirrje të vlefshme")

        # Local Call Time
        local_call_time = settings.get('local_call_time', 'N/A')
        print(f"\n🕐 Local Call Time: {local_call_time}")
        print(f"   - Kohëzgjatja e thirrjes lokale (sekonda)")

        # Dial Timeout
        dial_timeout = settings.get('dial_timeout', 'N/A')
        print(f"\n⏰ Dial Timeout: {dial_timeout}")
        print(f"   - Koha e pritjes për përgjigje (sekonda)")

        # In-Group
        in_group = settings.get('in_group', 'N/A')
        print(f"\n👥 In-Group: {in_group}")
        print(f"   - Grupi i agjentëve për këtë fushatë")

        # Queue Priority
        queue_priority = settings.get('queue_priority', 'N/A')
        print(f"\n🎯 Queue Priority: {queue_priority}")
        print(f"   - Prioriteti në radhë (më i lartë = më i prioritetizuar)")

        return settings
    except Exception as e:
        print(f"❌ Gabim: {e}")
        return None
    finally:
        if conn:
            conn.close()

def explain_call_flow(campaign_settings: Dict[str, Any]):
    """Shpjegon flow-in e telefonatës"""
    print("\n" + "="*60)
    print("🔄 FLOW-I I TELEFONATËS NË VICIDIAL")
    print("="*60)

    dial_method = campaign_settings.get('dial_method', 'MANUAL')
    auto_dial_level = campaign_settings.get('auto_dial_level', '1.0')
    drop_call_seconds = campaign_settings.get('drop_call_seconds', '0')

    print("\n📱 HAPET E THIRRJES:")
    print("-" * 60)

    if dial_method == 'MANUAL':
        print("""
1️⃣  AGJENTI E BËN THIRRJEN MANUALE
    ├─ Agjenti zgjedh një lead nga lista
    ├─ Shtyp butonin "Call" ose "Dial"
    ├─ Sistemi bën thirrjen në numrin e lead-it
    │
2️⃣  SISTEMI E LIDH THIRRJEN
    ├─ Vicidial bën thirrjen përmes Asterisk
    ├─ Nëse përgjigjet klienti:
    │   ├─ Thirrja kalon tek agjenti
    │   └─ Agjenti fillon bisedën
    ├─ Nëse nuk përgjigjet:
    │   ├─ Sistemi regjistron statusin (NOANSWER, BUSY, etc.)
    │   └─ Agjenti mund të provojë përsëri
    │
3️⃣  GJATË BISEDËS
    ├─ Agjenti mund të ndryshojë statusin e lead-it
    ├─ Sistemi regjistron kohëzgjatjen e bisedës
    ├─ Nëse biseda > drop_call_seconds: Thirrje e vlefshme
    │
4️⃣  PAS BISEDËS
    ├─ Agjenti shënon rezultatin (SALE, CALLBK, etc.)
    ├─ Lead-i merr statusin e ri
    └─ Agjenti është gati për thirrjen tjetër
        """)

    elif dial_method in ['RATIO', 'ADAPT', 'ADAPT_HARD_LIMIT', 'ADAPT_TAPERED']:
        print(f"""
1️⃣  SISTEMI E BËN THIRRJEN AUTOMATIK
    ├─ Dial Method: {dial_method}
    ├─ Auto Dial Level: {auto_dial_level}
    │   └─ Raporti i agjentëve të lirë vs. lead-eve
    ├─ Sistemi zgjedh automatikisht një lead
    │
2️⃣  SISTEMI E LIDH THIRRJEN
    ├─ Vicidial bën thirrjen përmes Asterisk
    ├─ Nëse përgjigjet klienti:
    │   ├─ Sistemi kërkon një agjent të lirë
    │   ├─ Nëse ka agjent të lirë:
    │   │   ├─ Thirrja kalon tek agjenti
    │   │   └─ Agjenti fillon bisedën
    │   └─ Nëse NUK ka agjent të lirë:
    │       ├─ Klienti dëgjon muzikë (queue)
    │       ├─ Sistemi pret për agjent të lirë
    │       └─ Kur agjenti bëhet i lirë → thirrja kalon tek ai
    ├─ Nëse nuk përgjigjet:
    │   ├─ Sistemi regjistron statusin (NOANSWER, BUSY, etc.)
    │   └─ Agjenti nuk merr këtë thirrje
    │
3️⃣  GJATË BISEDËS
    ├─ Agjenti mund të ndryshojë statusin e lead-it
    ├─ Sistemi regjistron kohëzgjatjen e bisedës
    ├─ Nëse biseda > {drop_call_seconds} sekonda: Thirrje e vlefshme
    │
4️⃣  PAS BISEDËS
    ├─ Agjenti shënon rezultatin (SALE, CALLBK, etc.)
    ├─ Lead-i merr statusin e ri
    ├─ Agjenti bëhet i lirë përsëri
    └─ Sistemi fillon thirrjen tjetër automatikisht
        """)

    print("\n" + "="*60)
    print("🔑 KONCEPTET KYÇE:")
    print("="*60)
    print("""
• Dial Method: Metoda e thirrjes (manual ose automatik)
• Auto Dial Level: Raporti i agjentëve vs. lead-eve
• Drop Call Seconds: Kohëzgjatja minimale për thirrje të vlefshme
• Queue: Radha e klientëve që presin për agjent
• Lead: Një kontakt/njeri që duhet të thirret
• Status: Gjendja e lead-it (SALE, CALLBK, NOANSWER, etc.)
• In-Group: Grupi i agjentëve që punojnë në këtë fushatë
    """)

def main():
    """Funksioni kryesor"""
    print("="*60)
    print("🔍 ANALIZË E FUSHATËS '1234' NË VICIDIAL")
    print("="*60)

    campaign_id = "1234"

    # Merr informacionin e fushatës
    campaign = get_campaign_info(campaign_id)

    if not campaign:
        print("\n⚠️ Nuk mund të lidhem me database-në.")
        print("   Kjo mund të jetë për shkak të:")
        print("   - Firewall që bllokon IP-në tuaj")
        print("   - Kredencialet e gabuara")
        print("   - Database e jashtme që nuk është e arritshme")
        print("\n💡 Sugjerim: Përdorni këtë skript direkt në serverin ku është Vicidial")
        return

    # Merr konfigurimet
    settings = get_campaign_settings(campaign_id)

    if settings:
        # Shpjegon flow-in
        explain_call_flow(settings)

    print("\n" + "="*60)
    print("✅ Analiza e përfunduar!")
    print("="*60)

if __name__ == "__main__":
    main()







