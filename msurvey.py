import streamlit as st
import pandas as pd
import datetime

# Load data
df = pd.read_excel("msurvey_kendaraan.xlsx")

# Konversi tanggal
df['tglOrder'] = pd.to_datetime(df['tglOrder'], errors='coerce')
df['tglmasukBM'] = pd.to_datetime(df['tglmasukBM'], errors='coerce')
df['tanggal_survey'] = pd.to_datetime(df['tanggal_survey'], errors='coerce')
df['TglReportIn'] = pd.to_datetime(df['TglReportIn'], errors='coerce')
df['TglApproval'] = pd.to_datetime(df['TglApproval'], errors='coerce')

# Libur nasional
libur_nasional_str = ["17-08-2025", "30-10-2025", "25-12-2025"]
libur_nasional = [datetime.datetime.strptime(tgl, "%d-%m-%Y").date() for tgl in libur_nasional_str]

# Fungsi hitung jam kerja
def hitung_jam_kerja(start, end, libur_nasional):
    if pd.isna(start) or pd.isna(end) or start > end:
        return datetime.timedelta(0)
    jam_mulai = datetime.time(8, 30)
    jam_selesai = datetime.time(17, 30)
    total = datetime.timedelta(0)
    current_day = start.date()
    last_day = end.date()
    while current_day <= last_day:
        if current_day.weekday() < 5 and current_day not in libur_nasional:
            work_start = datetime.datetime.combine(current_day, jam_mulai)
            work_end = datetime.datetime.combine(current_day, jam_selesai)
            actual_start = max(start, work_start)
            actual_end = min(end, work_end)
            if actual_start < actual_end:
                total += actual_end - actual_start
        current_day += datetime.timedelta(days=1)
    return total

# ✅ Fungsi format ke HH:MM
def format_sla_hhmm(td):
    if pd.isna(td) or td is None:
        return "-"
    total_minutes = int(td.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02}:{minutes:02}"

# Hitung SLA (jika kedua kolom valid)
df['sla_survey'] = df.apply(
    lambda r: hitung_jam_kerja(r['tglOrder'], r['TglReportIn'], libur_nasional)
    if pd.notna(r['tglOrder']) and pd.notna(r['TglReportIn']) else None,
    axis=1
)

df['sla_submit'] = df.apply(
    lambda r: hitung_jam_kerja(
        r['TglReportIn'], r['tglmasukBM'], libur_nasional
    )
    if pd.notna(r['TglReportIn']) and pd.notna(r['tglmasukBM']) else None,
    axis=1
)

df['sla_approve'] = df.apply(
    lambda r: hitung_jam_kerja(
        r['TglReportIn'], r['TglApproval'], libur_nasional
    )
    if pd.notna(r['TglReportIn']) and pd.notna(r['TglApproval']) else None,
    axis=1
)

# Format hasil SLA ke HH:MM
df['sla_survey_str'] = df['sla_survey'].apply(format_sla_hhmm)
df['sla_submit_str'] = df['sla_submit'].apply(format_sla_hhmm)
df['sla_approve_str'] = df['sla_approve'].apply(format_sla_hhmm)

# Filter jam kerja
def filter_jam_kerja(df, kolom_waktu, libur_nasional):
    df = df.copy()
    df = df[df[kolom_waktu].notna()]
    df = df[df[kolom_waktu].dt.weekday < 5]
    df = df[
        (df[kolom_waktu].dt.time >= datetime.time(8, 30)) &
        (df[kolom_waktu].dt.time <= datetime.time(17, 30))
    ]
    df = df[~df[kolom_waktu].dt.date.isin(libur_nasional)]
    return df

df_filtered = filter_jam_kerja(df, 'TglReportIn', libur_nasional)

def mean_bottom_80(series):
    s = series.dropna()
    if len(s) == 0:
        return None
    # ambil threshold persentil 80% (exclude top 20% terbesar)
    q80 = s.quantile(0.8)
    return s[s <= q80].mean()

# Streamlit UI
st.title("📊 Monitoring SLA Survey & Submit")

maskapai_list = df_filtered['nama_maskapai'].dropna().unique().tolist()
tabs = st.tabs(maskapai_list)

for i, maskapai in enumerate(maskapai_list):
    with tabs[i]:
        st.subheader(f"✈️ Maskapai: {maskapai}")
        df_msk = df_filtered[df_filtered['nama_maskapai'] == maskapai]

        total_unik = df_msk['Appid'].nunique()
        total_all = df_msk['Appid'].count()

        # ================= SUMMARY APPROVE / REJECT =================

        total_approve = df_msk[
            df_msk['HasilVerifikasiBM'].str.upper() == 'APPROVE'
        ].shape[0]

        total_reject = df_msk[
            df_msk['HasilVerifikasiBM'].str.upper() == 'REJECT'
        ].shape[0]

        approve_pct = (total_approve / total_all * 100) if total_all > 0 else 0
        reject_pct = (total_reject / total_all * 100) if total_all > 0 else 0

        # Hitung rata-rata SLA (timedelta)
        avg_sla_survey = df_msk['sla_survey'].mean()
        avg_sla_submit = df_msk['sla_submit'].mean()
        avg_sla_approve = df_msk['sla_approve'].mean()

        avg_sla_survey_b80 = mean_bottom_80(df_msk['sla_survey'])
        avg_sla_submit_b80 = mean_bottom_80(df_msk['sla_submit'])
        avg_sla_approve_b80 = mean_bottom_80(df_msk['sla_approve'])

        # Format ke HH:MM
        avg_sla_survey_str = format_sla_hhmm(avg_sla_survey)
        avg_sla_submit_str = format_sla_hhmm(avg_sla_submit)
        avg_sla_approve_str = format_sla_hhmm(avg_sla_approve)

        avg_sla_survey_b80_str = format_sla_hhmm(avg_sla_survey_b80)
        avg_sla_submit_b80_str = format_sla_hhmm(avg_sla_submit_b80)
        avg_sla_approve_b80_str = format_sla_hhmm(avg_sla_approve_b80)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total AppID (unik)", total_unik)
        with col2:
            st.metric("Total AppID (dengan duplikat)", total_all)

        col3, col4, col5 = st.columns(3)
        with col3:
            st.metric("Rata-rata SLA Survey (HH:MM)", avg_sla_survey_str)
        with col4:
            st.metric("Rata-rata SLA Submit (HH:MM)", avg_sla_submit_str)
        with col5:
            st.metric("Rata-rata SLA Approve (HH:MM)", avg_sla_approve_str)

        colb1, colb2, colb3 = st.columns(3)
        with colb1:
            st.metric("Rata-rata SLA Survey Bottom 80% (HH:MM)", avg_sla_survey_b80_str)
        with colb2:
            st.metric("Rata-rata SLA Submit Bottom 80% (HH:MM)", avg_sla_submit_b80_str)
        with colb3:
            st.metric("Rata-rata SLA Approve Bottom 80% (HH:MM)", avg_sla_approve_b80_str)
        
        col6, col7 = st.columns(2)
        with col6:
            st.metric("✅ Total Approve", total_approve)
            st.caption(f"{approve_pct:.2f}% dari Total AppID")

        with col7:
            st.metric("❌ Total Reject", total_reject)
            st.caption(f"{reject_pct:.2f}% dari Total AppID")

        with st.expander("📋 Lihat data lengkap"):
            st.dataframe(df_msk[[
                'Appid', 'no_polisi', 'tglOrder', 'tglmasukBM', 'tanggal_survey',
                'TglReportIn', 'TglApproval', 'sla_survey_str', 'sla_submit_str','sla_approve_str'
            ]], use_container_width=True)



