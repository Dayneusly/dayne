from pathlib import Path
import base64
import gzip
import io
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "latihan1.csv"
JS_DATA_PATH = BASE_DIR / "latihan1_data.js"
REQUIRED_COLUMNS = [
    "Student_ID", "Gender", "Age", "Study_Hours", "Sleep_Hours",
    "Attendance", "Exam_Score", "Monthly_Spending", "Screen_Hours",
    "Satisfaction",
]
MODEL_FEATURES = ["Study_Hours", "Attendance", "Sleep_Hours", "Screen_Hours"]
RADAR_FEATURES = [
    "Study_Hours", "Attendance", "Sleep_Hours",
    "Exam_Score", "Satisfaction", "Screen_Hours",
]

st.set_page_config(
    page_title="Executive BI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def generate_dummy_data(rows=100):
    """Buat data contoh yang konsisten untuk pemakaian pertama."""
    rng = np.random.default_rng(42)
    study = np.clip(rng.normal(10.0, 3.2, rows), 1, 20)
    sleep = np.clip(rng.normal(7.0, 1.0, rows), 4, 10)
    attendance = np.clip(rng.normal(86, 9, rows), 55, 100)
    screen = np.clip(rng.normal(6.0, 2.0, rows), 1, 12)
    score = (
        20 + 2.15 * study + 0.38 * attendance + 2.2 * sleep
        - 1.15 * screen + rng.normal(0, 5.0, rows)
    )
    score = np.clip(score, 35, 100).round(1)
    data = pd.DataFrame({
        "Student_ID": np.arange(1, rows + 1),
        "Gender": rng.choice(["F", "M"], size=rows),
        "Age": rng.integers(17, 25, size=rows),
        "Study_Hours": study.round(1),
        "Sleep_Hours": sleep.round(1),
        "Attendance": attendance.round(1),
        "Exam_Score": score,
        "Monthly_Spending": rng.integers(400, 2501, size=rows),
        "Screen_Hours": screen.round(1),
        "Satisfaction": np.clip(
            np.rint(2 + score / 13 + rng.normal(0, 1.2, rows)), 1, 10
        ).astype(int),
    })
    return data[REQUIRED_COLUMNS]


@st.cache_data
def load_data():
    """Baca file data JS, CSV cadangan, atau buat 100 baris data dummy."""
    if JS_DATA_PATH.exists():
        source = JS_DATA_PATH.read_text(encoding="utf-8")
        prefix = "const studentCsvGzipBase64 = "
        if not source.startswith(prefix):
            raise ValueError(
                "Format latihan1_data.js tidak sesuai. Jalankan convert_csv_to_js.py."
            )
        payload = source[len(prefix):].strip()
        if payload.endswith(";"):
            payload = payload[:-1]
        try:
            encoded = json.loads(payload)
            compressed = base64.b64decode(encoded, validate=True)
            csv_bytes = gzip.decompress(compressed)
            data = pd.read_csv(io.BytesIO(csv_bytes))
        except (json.JSONDecodeError, ValueError, OSError) as error:
            raise ValueError(
                "Isi latihan1_data.js tidak valid. Buat ulang dengan convert_csv_to_js.py."
            ) from error
    elif CSV_PATH.exists():
        data = pd.read_csv(CSV_PATH)
    else:
        data = generate_dummy_data()

    data.columns = [str(column).strip() for column in data.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError("Kolom CSV yang belum ada: " + ", ".join(missing))

    data = data[REQUIRED_COLUMNS].copy()
    data["Gender"] = data["Gender"].astype(str).str.strip().str.upper()
    for column in REQUIRED_COLUMNS:
        if column != "Gender":
            data[column] = pd.to_numeric(data[column], errors="coerce")
    return data.dropna(subset=["Student_ID", "Exam_Score"]).reset_index(drop=True)


def fit_ols(data):
    """Hitung koefisien OLS dan R² dari baris data yang lengkap."""
    usable = data[MODEL_FEATURES + ["Exam_Score"]].dropna()
    if usable.empty:
        coefficients = np.zeros(len(MODEL_FEATURES) + 1)
        r_squared = 0.0
    else:
        x = usable[MODEL_FEATURES].to_numpy(dtype=float)
        y = usable["Exam_Score"].to_numpy(dtype=float)
        design = np.column_stack([np.ones(len(x)), x])
        coefficients, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
        predictions = design @ coefficients
        ss_total = np.sum((y - y.mean()) ** 2)
        ss_residual = np.sum((y - predictions) ** 2)
        r_squared = 1 - ss_residual / ss_total if ss_total > 0 else 0.0
    weights = {"intercept": float(coefficients[0])}
    weights.update({
        name: float(value)
        for name, value in zip(MODEL_FEATURES, coefficients[1:])
    })
    weights["r2"] = float(r_squared)
    return weights, len(usable)


def radar_profiles(data):
    """Skalakan rata-rata indikator F/M ke rentang 0–100."""
    values = data[RADAR_FEATURES].apply(pd.to_numeric, errors="coerce")
    lows = values.min()
    highs = values.max()
    profiles = {}
    for gender in ("F", "M"):
        means = data.loc[data["Gender"] == gender, RADAR_FEATURES].mean()
        scaled = []
        for column in RADAR_FEATURES:
            span = highs[column] - lows[column]
            number = means[column]
            scaled.append(
                0.0 if pd.isna(number) or span == 0
                else float((number - lows[column]) / span * 100)
            )
        profiles[gender] = scaled
    return profiles


def grade_for(score):
    if score >= 85:
        return "A · Sangat Baik"
    if score >= 75:
        return "B · Baik"
    if score >= 65:
        return "C · Cukup"
    if score >= 50:
        return "D · Perlu Perhatian"
    return "E · Intervensi Prioritas"


def make_radar(data):
    profile = radar_profiles(data)
    chart = go.Figure()
    for gender, color, fill in [
        ("F", "#7c9cff", "rgba(124,156,255,.18)"),
        ("M", "#38d9c4", "rgba(56,217,196,.14)"),
    ]:
        chart.add_trace(go.Scatterpolar(
            r=profile[gender] + [profile[gender][0]],
            theta=[name.replace("_", " ") for name in RADAR_FEATURES]
            + [RADAR_FEATURES[0].replace("_", " ")],
            fill="toself",
            name="Female (F)" if gender == "F" else "Male (M)",
            line={"color": color},
            fillcolor=fill,
        ))
    chart.update_layout(
        template="plotly_dark",
        height=370,
        margin={"l": 35, "r": 35, "t": 25, "b": 35},
        polar={
            "radialaxis": {"visible": True, "range": [0, 100], "showticklabels": False},
            "bgcolor": "rgba(0,0,0,0)",
        },
        legend={"orientation": "h", "y": -0.12},
    )
    return chart


def correlation_figure(matrix, target):
    correlations = matrix[target].drop(labels=[target], errors="ignore")
    correlations = correlations.reindex(
        correlations.abs().sort_values(ascending=True).index
    )
    colors = ["#38d9c4" if value >= 0 else "#fb7185" for value in correlations]
    chart = go.Figure(go.Bar(
        x=correlations.values,
        y=[name.replace("_", " ") for name in correlations.index],
        orientation="h",
        marker_color=colors,
        text=[f"{value:.2f}" for value in correlations.values],
        textposition="outside",
        cliponaxis=False,
    ))
    chart.update_layout(
        template="plotly_dark",
        height=380,
        margin={"l": 10, "r": 35, "t": 15, "b": 35},
        xaxis={"range": [-1.08, 1.08], "title": "Pearson r", "zeroline": True},
        yaxis={"title": ""},
        showlegend=False,
    )
    return chart


def heatmap_figure(matrix):
    labels = [name.replace("_", " ") for name in matrix.columns]
    numbers = matrix.to_numpy(dtype=float)
    text = [[f"{value:.2f}" for value in row] for row in numbers]
    chart = go.Figure(go.Heatmap(
        z=numbers,
        x=labels,
        y=labels,
        zmin=-1,
        zmax=1,
        colorscale="RdBu",
        text=text,
        texttemplate="%{text}",
        hovertemplate="%{y} × %{x}: %{z:.3f}<extra></extra>",
        colorbar={"title": "r"},
    ))
    chart.update_layout(
        template="plotly_dark",
        height=620,
        margin={"l": 10, "r": 10, "t": 20, "b": 130},
        xaxis={"tickangle": -40},
        yaxis={"autorange": "reversed"},
    )
    return chart


st.title("📊 Executive BI Dashboard")
st.caption("Student performance · Descriptive analytics · OLS what-if simulator")

try:
    all_data = load_data()
except (OSError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Data tidak bisa dimuat: {error}")
    st.stop()

with st.sidebar:
    st.header("Filter")
    gender_choice = st.selectbox(
        "Gender",
        ["Semua", "F", "M"],
        format_func=lambda value: {
            "Semua": "Semua gender",
            "F": "Female (F)",
            "M": "Male (M)",
        }[value],
    )
    st.divider()
    st.caption("Sumber data: " + CSV_PATH.name)
    st.caption("Tip: gunakan Ctrl+P untuk mencetak atau menyimpan report sebagai PDF.")

data = all_data.copy()
if gender_choice in ("F", "M"):
    data = data[data["Gender"] == gender_choice].copy()

numeric_cols = [
    column for column in REQUIRED_COLUMNS
    if column != "Gender" and column != "Student_ID"
]
numeric_data = data[numeric_cols].apply(pd.to_numeric, errors="coerce")
correlations = numeric_data.corr().fillna(0)
weights, model_rows = fit_ols(data)
stats = numeric_data.describe().T
at_risk = int((data["Exam_Score"] < 60).sum())
score_mean = data["Exam_Score"].mean()

if len(data):
    score_correlations = correlations["Exam_Score"].drop("Exam_Score", errors="ignore")
    strongest = score_correlations.loc[score_correlations.abs().idxmax()]
    strongest_name = score_correlations.abs().idxmax().replace("_", " ")
    direction = "positif" if strongest >= 0 else "negatif"
    insight = (
        f"Dataset berisi {len(data)} siswa pada filter ini. Rata-rata Exam Score "
        f"{score_mean:.1f}/100; {at_risk} siswa memiliki skor di bawah 60. "
        f"Hubungan terkuat dengan Exam Score adalah {strongest_name} "
        f"(r = {strongest:.2f}, {direction})."
    )
else:
    insight = "Tidak ada data untuk gender yang dipilih."
st.info("✦  " + insight)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Rata-rata Exam Score", f"{score_mean:.1f}" if len(data) else "—", "dari 100 poin")
kpi2.metric("Rata-rata Study Hours", f"{data['Study_Hours'].mean():.1f}" if len(data) else "—", "jam per hari")
kpi3.metric("Rata-rata Attendance", f"{data['Attendance'].mean():.1f}%" if len(data) else "—")
kpi4.metric("Butuh Intervensi", f"{at_risk}", f"{at_risk / len(data) * 100:.1f}% dari siswa" if len(data) else "Tidak ada data")

left, right = st.columns([1.15, 0.85], gap="large")
with left:
    st.subheader("What-If Simulator")
    st.caption("Ubah nilai input untuk melihat prediksi dari model OLS.")
    sliders_left, sliders_right = st.columns(2)
    with sliders_left:
        study_value = st.slider("Study Hours", 0.0, 20.0, 10.0, 0.5)
        attendance_value = st.slider("Attendance (%)", 40, 100, 85, 1)
    with sliders_right:
        sleep_value = st.slider("Sleep Hours", 3.0, 12.0, 7.0, 0.5)
        screen_value = st.slider("Screen Hours", 0.0, 16.0, 6.0, 0.5)

    inputs = {
        "Study_Hours": study_value,
        "Attendance": attendance_value,
        "Sleep_Hours": sleep_value,
        "Screen_Hours": screen_value,
    }
    prediction_unclipped = weights["intercept"] + sum(
        weights[feature] * inputs[feature] for feature in MODEL_FEATURES
    )
    prediction = float(np.clip(prediction_unclipped, 0, 100))
    score_col, grade_col = st.columns(2)
    score_col.metric("Estimasi Exam Score", f"{prediction:.1f}")
    grade_col.metric("Grade", grade_for(prediction))

    with st.expander("Behind the Scenes · lihat persamaan dan breakdown"):
        st.caption(
            f"Ordinary Least Squares · R² pada data terpilih = {weights['r2']:.4f} "
            f"({weights['r2'] * 100:.2f}% variasi dijelaskan) · "
            f"{model_rows} baris dipakai untuk fitting."
        )
        equation = f"Exam Score = {weights['intercept']:.3f}"
        for feature in MODEL_FEATURES:
            equation += f" + ({weights[feature]:.3f} × {feature})"
        st.code(equation, language="text")
        breakdown = [
            {"Komponen": "Intercept", "Input": "—", "Koefisien": weights["intercept"], "Kontribusi": weights["intercept"]}
        ]
        for feature in MODEL_FEATURES:
            breakdown.append({
                "Komponen": feature.replace("_", " "),
                "Input": inputs[feature],
                "Koefisien": weights[feature],
                "Kontribusi": weights[feature] * inputs[feature],
            })
        st.dataframe(pd.DataFrame(breakdown), hide_index=True, use_container_width=True)
        st.caption(f"Prediksi sebelum dibatasi ke rentang 0–100: {prediction_unclipped:.2f}")

with right:
    st.subheader("Profil Akademik per Gender")
    st.caption("Rata-rata indikator diskalakan ke 0–100 untuk membandingkan profil.")
    st.plotly_chart(make_radar(all_data), use_container_width=True)

st.divider()
st.subheader("Analisis Faktor Korelasi Target")
target = st.selectbox(
    "Pilih target (Y)",
    numeric_cols,
    index=numeric_cols.index("Exam_Score"),
    format_func=lambda value: value.replace("_", " "),
)
factor_options = [column for column in numeric_cols if column != target]
default_factor = "Study_Hours" if "Study_Hours" in factor_options else factor_options[0]
factor = st.selectbox(
    "Pilih faktor (X) untuk scatter plot",
    factor_options,
    index=factor_options.index(default_factor),
    format_func=lambda value: value.replace("_", " "),
)

chart_left, chart_right = st.columns(2, gap="large")
with chart_left:
    st.markdown("**Ranking korelasi faktor**")
    st.plotly_chart(correlation_figure(correlations, target), use_container_width=True)
with chart_right:
    st.markdown(f"**Scatter: {factor.replace('_', ' ')} vs {target.replace('_', ' ')}**")
    scatter = go.Figure(go.Scatter(
        x=data[factor],
        y=data[target],
        mode="markers",
        text=["ID " + str(value) + " · " + str(gender)
              for value, gender in zip(data["Student_ID"], data["Gender"])],
        hovertemplate="%{text}<br>X: %{x}<br>Y: %{y}<extra></extra>",
        marker={"color": "#7c9cff", "size": 9, "opacity": 0.8},
    ))
    scatter.update_layout(
        template="plotly_dark",
        height=380,
        margin={"l": 10, "r": 10, "t": 15, "b": 45},
        xaxis_title=factor.replace("_", " "),
        yaxis_title=target.replace("_", " "),
    )
    st.plotly_chart(scatter, use_container_width=True)

st.divider()
st.subheader("Matriks Korelasi")
st.caption("Pearson r: biru menunjukkan korelasi positif, merah menunjukkan korelasi negatif.")
st.plotly_chart(heatmap_figure(correlations), use_container_width=True)

with st.expander("Statistik deskriptif"):
    st.dataframe(stats.round(2), use_container_width=True)

st.divider()
st.subheader("Data Siswa")
search = st.text_input("Cari data", placeholder="Cari ID, gender, nilai, atau angka…")
table_data = data.copy()
if search.strip():
    mask = table_data.astype(str).apply(
        lambda column: column.str.contains(search.strip(), case=False, na=False)
    ).any(axis=1)
    table_data = table_data[mask]
st.caption(f"Menampilkan {len(table_data)} dari {len(data)} siswa pada filter ini.")
st.dataframe(table_data, hide_index=True, use_container_width=True)
csv_bytes = table_data.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "↓ Ekspor data yang tampil sebagai CSV",
    data=csv_bytes,
    file_name="student_data.csv",
    mime="text/csv",
)
