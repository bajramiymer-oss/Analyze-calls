import streamlit as st
import pathlib
from core.voip_rates import get_voip_rates, update_voip_rates
from core.status_settings import (
    get_status_cost_map,
    update_status_cost_map,
    get_resa_threshold_percent,
    update_resa_threshold_percent,
    get_dial_statuses_for_dials,
    update_dial_statuses_for_dials,
    get_allow_all_statuses,
    update_allow_all_statuses,
    get_network_limits,
    update_network_limits,
)
from core.campaign_manager import (
    get_all_campaigns,
    create_campaign,
    update_campaign,
    delete_campaign,
    add_document_to_campaign,
    remove_document_from_campaign,
    get_campaign_by_id,
)

st.title("⚙️ Settings — Konfigurime")

st.markdown("""
Këtu mund të konfigurosh të gjitha parametrat që përdoren në raportet e Smart Reports.
Këto vlera ruhen automatikisht dhe aplikohen në të gjitha raportet.
""")

# ================== VoIP Rates ==================
st.markdown("---")
st.markdown("## 📞 VoIP Rates (€/min)")
st.caption("Tarifat e kostos së thirrjeve për mobile dhe fix. Përdoren për të llogaritur koston totale VoIP.")

rates = get_voip_rates()
col1, col2, col3 = st.columns([1,1,1])
with col1:
    m_val = st.number_input(
        "Mobile rate (€/min)",
        min_value=0.000001,
        max_value=2.0,
        value=float(rates.mobile_eur_per_min),
        step=0.001,
        format="%.6f",
        help="Kosto për minutë për thirrje mobile"
    )
with col2:
    f_val = st.number_input(
        "Fix rate (€/min)",
        min_value=0.000001,
        max_value=2.0,
        value=float(rates.fix_eur_per_min),
        step=0.001,
        format="%.6f",
        help="Kosto për minutë për thirrje fix"
    )
with col3:
    st.caption(f"**Azhornuar:** {rates.updated_at}")
    st.caption(f"Mobile: €{rates.mobile_eur_per_min:.6f}")
    st.caption(f"Fix: €{rates.fix_eur_per_min:.6f}")

if st.button("💾 Ruaj VoIP Rates", type="primary", use_container_width=True):
    try:
        saved = update_voip_rates({
            "mobile_eur_per_min": m_val,
            "fix_eur_per_min": f_val,
        })
        st.success(f"✅ U ruajtën tarifat: Mobile = €{saved.mobile_eur_per_min:.6f}/min, Fix = €{saved.fix_eur_per_min:.6f}/min")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Nuk u ruajtën tarifat: {e}")

# ================== Status Costs ==================
st.markdown("---")
st.markdown("## 💰 Status Costs (€/call)")
st.caption("Kosto mesatare për thirrje sipas statusit. Përdoren për të llogaritur koston totale sipas statusit në raportin '02_Status_Mix_Cost'.")

status_map = get_status_cost_map()

# Let user edit rows dynamically
edited_values = {}
cols = st.columns(4)
keys = sorted(status_map.keys())
for idx, k in enumerate(keys):
    with cols[idx % 4]:
        edited_values[k] = st.number_input(
            f"{k}",
            min_value=0.0,
            max_value=1.0,
            value=float(status_map[k]),
            step=0.001,
            format="%.6f",
            help=f"Kosto për thirrje me status {k}"
        )

if st.button("💾 Ruaj Status Costs", use_container_width=True):
    try:
        saved_map = update_status_cost_map(edited_values)
        st.success("✅ U ruajtën kostot sipas statusit.")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Nuk u ruajtën status costs: {e}")

# ================== Resa Threshold ==================
st.markdown("---")
st.markdown("## 📊 Resa Threshold (%)")
st.caption("Pragu minimal i Resa-s për të konsideruar një listë si 'e mirë' në smart_pick. Përdoret në raportin '01_List_Cost'.")

current_thresh = get_resa_threshold_percent()
col_thresh1, col_thresh2 = st.columns([2,1])
with col_thresh1:
    new_thresh = st.number_input(
        "Resa threshold (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(current_thresh),
        step=0.1,
        help="Listat me Resa ≥ kësaj vlere konsiderohen për 'smart pick'"
    )
with col_thresh2:
    st.caption(f"**Aktuale:** {current_thresh:.2f}%")

if st.button("💾 Ruaj Resa Threshold", use_container_width=True):
    try:
        v = update_resa_threshold_percent(new_thresh)
        st.success(f"✅ U ruajt pragu: {v:.2f}%")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Nuk u ruajt pragu: {e}")

# ================== Dial Statuses ==================
st.markdown("---")
st.markdown("## 📋 Dial Statuses for 01_List_Cost")
st.caption("Statuset që llogariten si 'dials' në raportin '01_List_Cost'. Nëse aktivizohet 'Allow ALL', të gjitha statuset përfshihen.")

current_statuses = get_dial_statuses_for_dials()
# Lista e plotë e statuseve të mundshme në Vicidial
all_possible_statuses = [
    "AA", "AB", "ADC", "AFAX", "AL", "AM", "A",
    "B", "BUSY",
    "CALLBK", "CBHOLD", "CPTERR",
    "DC", "DEC", "DISCONN", "DNC", "DROP", "DROPHG",
    "ERI", "ERRVM",
    "IVRXFR",
    "LAGGED", "LB", "LRERR",
    "MAXCALL", "MLINAT", "MLIVEO", "MLVMCT", "MLVMEO",
    "NA", "NANQUE", "NCALL", "NOINT", "N",
    "PAMD", "PDROP", "PM", "PU",
    "QVMAIL",
    "RQXFER",
    "SALE", "SVYCLM",
    "TIMEOT", "XDROP", "XFER"
]
all_suggestions = sorted(set(list(status_map.keys()) + current_statuses + all_possible_statuses))
allow_all = get_allow_all_statuses()

col_allow1, col_allow2 = st.columns([1,3])
with col_allow1:
    allow_all_new = st.checkbox(
        "Allow ALL statuses",
        value=allow_all,
        help="Kur aktivizohet, të gjitha statuset përdoren (nuk aplikohet filtër)"
    )
with col_allow2:
    selected = st.multiselect(
        "Dial statuses (kur ALL është OFF)",
        options=all_suggestions,
        default=current_statuses,
        help="Këto statuse përdoren vetëm për llogaritjen e total_dials dhe total_sec në 01_List_Cost.",
        disabled=allow_all_new
    )

if st.button("💾 Ruaj Dial Statuses", use_container_width=True):
    try:
        saved = update_dial_statuses_for_dials(selected)
        update_allow_all_statuses(allow_all_new)
        mode = "ALL" if allow_all_new else "FILTERED"
        st.success(f"✅ Mode={mode}. U ruajtën: {', '.join(saved) if saved else 'ALL'}")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Nuk u ruajtën dial statuses: {e}")

# ================== Campaign Contexts ==================
st.markdown("---")
st.markdown("## 🎯 Menaxhimi i Fushatave/Konteksteve")
st.caption("Krijo dhe menaxho kontekste specifike për fushata të ndryshme (Google Reserve, Tim Business, etj.). Çdo fushatë mund të ketë kontekst dhe dokumente të dedikuara.")

# Tabat për menaxhim
tab1, tab2 = st.tabs(["📋 Lista e Fushatave", "➕ Shto/Ndrysho Fushatë"])

with tab1:
    st.markdown("### Lista e fushatave ekzistuese")

    campaigns = get_all_campaigns()

    if not campaigns:
        st.info("Nuk ka asnjë fushatë të krijuar ende. Shko te tab-i '➕ Shto/Ndrysho Fushatë' për të krijuar një të re.")
    else:
        for camp in campaigns:
            with st.expander(f"📁 {camp['name']}", expanded=False):
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.caption(f"**ID:** `{camp['id']}`")
                    st.caption(f"**Krijuar:** {camp['created_date'][:10]}")
                    st.caption(f"**Modifikuar:** {camp['last_modified'][:10]}")
                with col_info2:
                    st.caption(f"**Dokumente:** {len(camp.get('documents', []))}/{3}")
                    st.caption(f"**Total faqe:** {camp.get('total_pages', 0)}/50")
                    st.caption(f"**Madhësia:** {camp.get('total_size_kb', 0)} KB")

                st.markdown("---")
                st.markdown("**Variablat e kontekstit:**")

                if camp.get('project_context_hint'):
                    st.text_area("Project Context Hint", value=camp['project_context_hint'], height=80, disabled=True, key=f"view_proj_{camp['id']}")
                else:
                    st.caption("_Project Context Hint: I zbrazët_")

                if camp.get('summary_hint'):
                    st.text_area("Summary Hint", value=camp['summary_hint'], height=80, disabled=True, key=f"view_summ_{camp['id']}")
                else:
                    st.caption("_Summary Hint: I zbrazët_")

                if camp.get('bullets_hint'):
                    st.text_area("Bullets Hint", value=camp['bullets_hint'], height=80, disabled=True, key=f"view_bull_{camp['id']}")
                else:
                    st.caption("_Bullets Hint: I zbrazët_")

                st.markdown("---")
                st.markdown("**Dokumentet:**")

                if camp.get('documents'):
                    for doc in camp['documents']:
                        doc_col1, doc_col2 = st.columns([3, 1])
                        with doc_col1:
                            st.caption(f"📄 {doc['original_name']} ({doc['size_kb']} KB, {doc['pages']} faqe)")
                        with doc_col2:
                            if st.button("🗑️ Fshi", key=f"del_doc_{camp['id']}_{doc['filename']}"):
                                try:
                                    remove_document_from_campaign(camp['id'], doc['filename'])
                                    st.success(f"✅ U fshi dokumenti: {doc['original_name']}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Gabim: {e}")
                else:
                    st.caption("_Nuk ka dokumente të ngarkuara_")

                st.markdown("---")

                # Opsionet për fshirje
                col_del1, col_del2 = st.columns([3, 1])
                with col_del2:
                    if st.button("🗑️ Fshi Fushatën", key=f"del_camp_{camp['id']}", type="secondary"):
                        try:
                            delete_campaign(camp['id'])
                            st.success(f"✅ U fshi fushata: {camp['name']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Gabim: {e}")

with tab2:
    st.markdown("### Krijo ose modifiko fushatë")

    # Zgjidhja: krijo të re ose modifiko ekzistuese
    operation = st.radio("Operacioni", ["Krijo fushatë të re", "Modifiko fushatë ekzistuese"], horizontal=True)

    if operation == "Krijo fushatë të re":
        st.markdown("#### Krijoni një fushatë të re")

        new_name = st.text_input("Emri i fushatës (required)", placeholder="p.sh. Google Reserve UK - Restorante")
        new_project_hint = st.text_area(
            "Project Context Hint (optional)",
            placeholder='Thirrje outbound për restorante në MB për t\'u regjistruar në Google Reserve me Movylo...',
            height=120
        )
        new_summary_hint = st.text_area(
            "Summary Hint (optional)",
            placeholder='Fokuso në aftësinë e agjentit për të shpjeguar qartë bashkëpunimin me Google...',
            height=120
        )
        new_bullets_hint = st.text_area(
            "Bullets Hint (optional)",
            placeholder='Preggi: edukim digjital, qartësi, prezantim profesional...',
            height=120
        )

        st.markdown("---")
        st.markdown("**Ngarko dokumente (opsionale, max 3 files)**")
        uploaded_files = st.file_uploader(
            "Zgjidhni file-a (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="new_campaign_files"
        )

        if uploaded_files and len(uploaded_files) > 3:
            st.warning(f"⚠️ Mund të ngarkoni maksimumi 3 dokumente. Zgjodhët {len(uploaded_files)}.")

        if st.button("✅ Krijo Fushatën", type="primary", disabled=not new_name):
            try:
                # Krijo fushatën
                campaign = create_campaign(
                    name=new_name.strip(),
                    project_context_hint=new_project_hint.strip(),
                    summary_hint=new_summary_hint.strip(),
                    bullets_hint=new_bullets_hint.strip()
                )

                # Ngarko dokumentet nëse ka
                if uploaded_files:
                    for uf in uploaded_files[:3]:  # Max 3
                        # Ruaj përkohësisht
                        tmp_path = pathlib.Path("tmp_upload") / uf.name
                        tmp_path.parent.mkdir(exist_ok=True)
                        with open(tmp_path, "wb") as f:
                            f.write(uf.getbuffer())

                        try:
                            add_document_to_campaign(campaign['id'], tmp_path, uf.name)
                        except Exception as e:
                            st.warning(f"⚠️ Nuk u ngarkua {uf.name}: {e}")
                        finally:
                            if tmp_path.exists():
                                tmp_path.unlink()

                st.success(f"✅ U krijua fushata: {campaign['name']}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Gabim gjatë krijimit të fushatës: {e}")

    else:  # Modifiko ekzistuese
        st.markdown("#### Modifikoni një fushatë ekzistuese")

        campaigns = get_all_campaigns()
        if not campaigns:
            st.info("Nuk ka fushata për të modifikuar.")
        else:
            campaign_names = {c['name']: c['id'] for c in campaigns}
            selected_name = st.selectbox("Zgjidhni fushatën", list(campaign_names.keys()))
            selected_id = campaign_names[selected_name]
            selected_campaign = get_campaign_by_id(selected_id)

            if selected_campaign:
                mod_name = st.text_input("Emri i fushatës", value=selected_campaign['name'])
                mod_project_hint = st.text_area(
                    "Project Context Hint (optional)",
                    value=selected_campaign.get('project_context_hint', ''),
                    height=120
                )
                mod_summary_hint = st.text_area(
                    "Summary Hint (optional)",
                    value=selected_campaign.get('summary_hint', ''),
                    height=120
                )
                mod_bullets_hint = st.text_area(
                    "Bullets Hint (optional)",
                    value=selected_campaign.get('bullets_hint', ''),
                    height=120
                )

                st.markdown("---")
                st.markdown("**Shto dokumente shtesë**")

                current_docs = len(selected_campaign.get('documents', []))
                remaining_slots = 3 - current_docs

                if remaining_slots > 0:
                    st.caption(f"Mund të shtoni {remaining_slots} dokument(e) të tjerë.")
                    uploaded_mod_files = st.file_uploader(
                        "Zgjidhni file-a (PDF, DOCX, TXT)",
                        type=["pdf", "docx", "txt"],
                        accept_multiple_files=True,
                        key="mod_campaign_files"
                    )

                    if uploaded_mod_files and len(uploaded_mod_files) > remaining_slots:
                        st.warning(f"⚠️ Mund të ngarkoni vetëm {remaining_slots} dokument(e). Zgjodhët {len(uploaded_mod_files)}.")
                else:
                    st.info("Kjo fushatë ka tashmë 3 dokumente (maksimum). Fshini disa për të ngarkuar të tjerë.")
                    uploaded_mod_files = None

                if st.button("💾 Ruaj Ndryshimet", type="primary"):
                    try:
                        # Përditëso fushatën
                        update_campaign(
                            campaign_id=selected_id,
                            name=mod_name.strip() if mod_name != selected_campaign['name'] else None,
                            project_context_hint=mod_project_hint.strip(),
                            summary_hint=mod_summary_hint.strip(),
                            bullets_hint=mod_bullets_hint.strip()
                        )

                        # Ngarko dokumente të reja
                        if uploaded_mod_files and remaining_slots > 0:
                            for uf in uploaded_mod_files[:remaining_slots]:
                                tmp_path = pathlib.Path("tmp_upload") / uf.name
                                tmp_path.parent.mkdir(exist_ok=True)
                                with open(tmp_path, "wb") as f:
                                    f.write(uf.getbuffer())

                                try:
                                    add_document_to_campaign(selected_id, tmp_path, uf.name)
                                except Exception as e:
                                    st.warning(f"⚠️ Nuk u ngarkua {uf.name}: {e}")
                                finally:
                                    if tmp_path.exists():
                                        tmp_path.unlink()

                        st.success(f"✅ U përditësua fushata: {mod_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gabim gjatë përditësimit: {e}")

# ================== Info Footer ==================
st.markdown("---")
st.info("""
**ℹ️ Shënim:**
- Të gjitha ndryshimet ruhen automatikisht në `config/voip_rates.json`, `config/settings.json` dhe `config/campaign_contexts.json`
- Ndryshimet aplikohen menjëherë në të gjitha raportet e Smart Reports dhe në analizat automatike
- Për të rikthyer vlerat default, fshi file-at e konfigurimit dhe rinis aplikimin
- Dokumentet ruhen në `assets/campaigns/{campaign_id}/documents/`
""")

# ================== Network Limits ==================
st.markdown("---")
st.markdown("## 🌐 Network Limits (bandwidth & parallelism)")
st.caption("Vendos limite rrjeti për të mos saturuar linjën gjatë shkarkimeve/analizave.")

nl = get_network_limits()

col_n1, col_n2 = st.columns([1,1])
with col_n1:
    mpd_val = st.number_input(
        "Max parallel downloads",
        min_value=1, max_value=32,
        value=int(nl.get("max_parallel_downloads", 3)),
        step=1,
        help="Numri maksimal i shkarkimeve paralele (p.sh. audio/drive)"
    )
with col_n2:
    thr_val = st.number_input(
        "Throttle (KB/s)",
        min_value=0, max_value=102400,
        value=int(nl.get("throttle_kbps", 0)),
        step=64,
        help="Kufiri i shpejtësisë për çdo rrjedhë (0 = pa limit)"
    )

if st.button("💾 Ruaj Network Limits", use_container_width=True):
    try:
        saved = update_network_limits(mpd_val, thr_val)
        st.success(f"✅ Limits: parallel={saved['max_parallel_downloads']}, throttle={saved['throttle_kbps']} KB/s")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Nuk u ruajtën: {e}")

