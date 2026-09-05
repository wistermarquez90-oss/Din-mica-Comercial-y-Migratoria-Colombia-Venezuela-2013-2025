# -*- coding: utf-8 -*-
"""
================================================================================
CODIGO REPRODUCIBLE — CAPITULO IV (BLOQUE MIGRATORIO)
Monografia: "Dinamica Comercial y Migratoria Colombia-Venezuela 2013-2025"
Autor: Br. Wister Asdrubal Marquez Duque — ULA, Escuela de Economia
================================================================================
Genera las Figuras 4 a 16 del Capitulo IV a partir de los archivos de datos
agregados y validados de la Encuesta Pulso de la Migracion (EPM) del DANE:

  1. EPM_Perfiles_Evolucion_R1-R8.xlsx      (indicadores agregados por ronda)
  2. EPM_Modelo_Econometrico_Perfiles.xlsx  (perfiles por cohorte y modelos)

Los indicadores agregados fueron calculados previamente sobre los microdatos
oficiales del DANE aplicando los factores de expansion (FEX / FEX_PER /
FEX_HOG) y validados contra las cifras publicadas por el DANE (diferencias
< 0,1 puntos porcentuales).

Requisitos:  pip install pandas numpy matplotlib seaborn geopandas openpyxl
Salidas:     carpeta ./figuras/ con 13 archivos PNG (300 dpi)
================================================================================
"""

import os
import urllib.request

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.colorbar import ColorbarBase

# -----------------------------------------------------------------------------
# 0. PARAMETROS EDITABLES
# -----------------------------------------------------------------------------
RUTA_PERFILES = "EPM_Perfiles_Evolucion_R1-R8.xlsx"      # <- ajustar ruta
RUTA_MODELO   = "EPM_Modelo_Econometrico_Perfiles.xlsx"  # <- ajustar ruta
OUT = "figuras"
os.makedirs(OUT, exist_ok=True)

# GeoJSON oficiales para los mapas (se descargan automaticamente)
URL_COL_DPTOS = ("https://raw.githubusercontent.com/caticoa3/colombia_mapa/"
                 "master/co_2018_MGN_DPTO_POLITICO.geojson")  # Marco Geoestadistico DANE
URL_VEN_EDOS  = ("https://github.com/wmgeolab/geoBoundaries/raw/9469f09/"
                 "releaseData/gbOpen/VEN/ADM1/geoBoundaries-VEN-ADM1_simplified.geojson")

# -----------------------------------------------------------------------------
# 1. ESTILO GRAFICO GLOBAL
# -----------------------------------------------------------------------------
AZUL, AZUL2 = "#1f4e79", "#2e75b6"
NARAN, VERDE, GRIS, ROJO = "#c55a11", "#538135", "#7f7f7f", "#b02418"

plt.rcParams.update({
    "figure.dpi": 300, "savefig.dpi": 300,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.labelsize": 10, "axes.edgecolor": "#444444",
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "--",
    "legend.frameon": False, "figure.facecolor": "white",
})

FUENTE_EPM = ("Fuente: elaboracion propia con base en los microdatos de la "
              "Encuesta Pulso de la Migracion (EPM), DANE,\naplicando los "
              "factores de expansion oficiales.")

def nota_fuente(fig, texto=FUENTE_EPM, y=0.005):
    fig.text(0.01, y, texto, fontsize=7, color="#555555", style="italic")

def fmt_miles(x, pos):
    return f"{x:,.0f}".replace(",", ".")

RONDA_LBL = ["R1\njul-2021", "R2\noct-2021", "R3\nene-2022", "R4\nmar-2022",
             "R5\nmar-2023", "R6\nago-2023", "R7\nabr-2024", "R8\nmay-2025"]

cmap_azul = LinearSegmentedColormap.from_list(
    "azul", ["#eef3fa", "#9dc3e6", "#2e75b6", "#1f4e79", "#122e49"])

# -----------------------------------------------------------------------------
# 2. CARGA DE DATOS AGREGADOS
# -----------------------------------------------------------------------------
ficha   = pd.read_excel(RUTA_PERFILES, sheet_name="FICHA_TECNICA")
ind_p   = pd.read_excel(RUTA_PERFILES, sheet_name="INDICADORES_PERSONAS")
ind_h   = pd.read_excel(RUTA_PERFILES, sheet_name="INDICADORES_HOGARES")
lleg    = pd.read_excel(RUTA_PERFILES, sheet_name="LLEGADAS_POR_ANIO_2013-2025")
coh     = pd.read_excel(RUTA_PERFILES, sheet_name="COHORTES_LLEGADA_PCT")
dpto    = pd.read_excel(RUTA_PERFILES, sheet_name="DEPARTAMENTO_INGRESO_PCT")
estado  = pd.read_excel(RUTA_PERFILES, sheet_name="ESTADO_ORIGEN_VZLA_PCT")
perf_r1 = pd.read_excel(RUTA_MODELO,  sheet_name="PERFIL_COHORTES_R1")
perf_58 = pd.read_excel(RUTA_MODELO,  sheet_name="PERFILES_COHORTES_R5-R8")
mods    = pd.read_excel(RUTA_MODELO,  sheet_name="RESULTADOS_MODELOS")

ip = ind_p.set_index("INDICADOR")
rondas8 = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]

# -----------------------------------------------------------------------------
# FIGURA 4. Poblacion de referencia de la EPM por ronda
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.2, 4.4))
x = np.arange(8)
pob = ficha["POBLACION_REFERENCIA_PERSONAS"].values / 1e6
ax.bar(x, pob, color=[AZUL2]*4 + [AZUL]*4, width=0.62, zorder=3)
for xi, v in zip(x, pob):
    ax.text(xi, v + 0.04, f"{v:.2f}", ha="center", fontsize=9,
            fontweight="bold", color="#333")
ax.set_xticks(x); ax.set_xticklabels(RONDA_LBL, fontsize=8)
ax.set_ylabel("Poblacion de referencia (millones de personas 15+)")
ax.set_title("Poblacion de referencia de la EPM por ronda (personas de 15 anos y mas)")
ax.set_ylim(0, 2.55)
ax.axvline(3.5, color=ROJO, ls="--", lw=1.2)
ax.text(3.45, 2.42, "Panel (2021-2022)", ha="right", fontsize=8.5,
        color=AZUL2, fontweight="bold")
ax.text(3.58, 2.42, "Transversal semestral (2023-2025)", ha="left",
        fontsize=8.5, color=AZUL, fontweight="bold")
nota_fuente(fig)
plt.tight_layout(rect=[0, 0.06, 1, 1])
plt.savefig(f"{OUT}/fig04_poblacion_referencia.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 5. Cohortes de llegada 2013-2025
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.6, 4.6))
years = lleg["AÑO DE LLEGADA"].values
rondas = {"R5": ("#9dc3e6", "o", "R5 (mar-may 2023)"),
          "R6": ("#2e75b6", "s", "R6 (ago-sep 2023)"),
          "R7": ("#c55a11", "^", "R7 (abr-may 2024)"),
          "R8": ("#1f4e79", "D", "R8 (may-jun 2025)")}
for r, (c, m, lbl) in rondas.items():
    ax.plot(years, lleg[r].values / 1000.0, marker=m, ms=4.5, lw=1.8,
            color=c, label=lbl, zorder=3)
ax.set_title("Cohortes de llegada de la poblacion migrante venezolana residente, 2013-2025")
ax.set_ylabel("Personas que permanecen residentes (miles)")
ax.set_xlabel("Ano de primera llegada a Colombia")
ax.set_xticks(years)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_miles))
ax.legend(fontsize=8.5, ncol=2)
ax.annotate("Pico del exodo\n2018-2019", xy=(2018, 525), xytext=(2014.6, 470),
            arrowprops=dict(arrowstyle="->", color="#333"), fontsize=8.5,
            fontweight="bold")
ax.annotate("Cierre fronterizo\nCOVID-19", xy=(2020, 166), xytext=(2021.3, 380),
            arrowprops=dict(arrowstyle="->", color="#333"), fontsize=8.5)
ax.annotate("Sesgo de supervivencia:\nla cohorte 2018 pasa de 525 mil (R5)\na 153 mil (R8)",
            xy=(2018, 153), xytext=(2020.6, 230),
            arrowprops=dict(arrowstyle="->", color=ROJO), fontsize=7.8, color=ROJO)
ax.set_ylim(0, 575)
nota_fuente(fig)
plt.tight_layout(rect=[0, 0.06, 1, 1])
plt.savefig(f"{OUT}/fig05_cohortes_llegada.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 6. Composicion porcentual por cohorte de llegada
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.6, 4.4))
coh2 = coh.rename(columns={"Unnamed: 0": "Cohorte"}).set_index("Cohorte")[["R5", "R6", "R7", "R8"]]
pal_c = ["#8496b0", "#2e75b6", "#1f4e79", "#c55a11", "#e2a06b", "#538135"]
bottom = np.zeros(4)
for i, (idx, row) in enumerate(coh2.iterrows()):
    ax.bar(["R5 (2023)", "R6 (2023)", "R7 (2024)", "R8 (2025)"], row.values,
           bottom=bottom, color=pal_c[i], label=idx, width=0.55, zorder=3)
    for j, v in enumerate(row.values):
        if v > 4:
            ax.text(j, bottom[j] + v / 2, f"{v:.0f}%", ha="center", va="center",
                    color="white", fontsize=8.5, fontweight="bold")
    bottom += row.values
ax.set_ylabel("% de la poblacion migrante residente (15+)")
ax.set_title("Composicion de la poblacion migrante por cohorte de llegada")
ax.legend(title="Cohorte de llegada", fontsize=8, title_fontsize=8.5,
          bbox_to_anchor=(1.01, 1), loc="upper left")
ax.set_ylim(0, 100)
ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
nota_fuente(fig)
plt.tight_layout(rect=[0, 0.05, 0.86, 1])
plt.savefig(f"{OUT}/fig06_composicion_cohortes.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 7. Estructura por edad y feminizacion
# -----------------------------------------------------------------------------
grupos = ["% 15 a 24 años", "% 25 a 34 años", "% 35 a 44 años",
          "% 45 a 54 años", "% 55 y más años"]
labels_g = ["15-24", "25-34", "35-44", "45-54", "55 y mas"]

fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2),
                         gridspec_kw={"width_ratios": [1.35, 1]})
ax = axes[0]
xg = np.arange(5); w = 0.35
r1v = [ip.loc[g, "R1"] for g in grupos]
r7v = [ip.loc[g, "R7"] for g in grupos]
b1 = ax.bar(xg - w/2, r1v, w, color="#9dc3e6", label="R1 (2021)", zorder=3)
b2 = ax.bar(xg + w/2, r7v, w, color=AZUL, label="R7 (2024)", zorder=3)
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.5,
            f"{b.get_height():.0f}", ha="center", fontsize=8)
ax.set_xticks(xg); ax.set_xticklabels(labels_g)
ax.set_xlabel("Grupo de edad"); ax.set_ylabel("% de la poblacion (15+)")
ax.set_title("a) Estructura por grupos de edad")
ax.legend(fontsize=8.5); ax.set_ylim(0, 40)

ax = axes[1]
muj = ip.loc["% Mujeres", rondas8].astype(float).values
ax.plot(range(8), muj, marker="o", color=ROJO, lw=2, zorder=3)
ax.axhline(50, color=GRIS, ls=":", lw=1)
for i, v in enumerate(muj):
    ax.text(i, v + 0.08, f"{v:.1f}", ha="center", fontsize=7.5)
ax.set_xticks(range(8)); ax.set_xticklabels([f"R{i+1}" for i in range(8)])
ax.set_ylim(48.5, 51.6); ax.set_ylabel("% mujeres")
ax.set_title("b) Feminizacion progresiva (% mujeres)")
ax.annotate("cruce al predominio\nfemenino (R8: 51,0%)", xy=(7, 51.02),
            xytext=(4.1, 51.25), arrowprops=dict(arrowstyle="->", color="#333"),
            fontsize=8)
nota_fuente(fig, y=-0.02)
plt.tight_layout()
plt.savefig(f"{OUT}/fig07_edad_sexo.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 8. Capital humano: nivel educativo (R1) y escolaridad por cohorte
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.2),
                         gridspec_kw={"width_ratios": [1, 1.15]})
ax = axes[0]
niv = ["Posgrado", "Universitario", "Tecnico /\ntecnologico", "Bachillerato",
       "Primaria", "Ninguno"]
val = [0.3, 7.9, 9.5, 52.5, 26.0, 2.7]
cols_ed = ["#7030a0", "#1f4e79", "#2e75b6", "#c55a11", "#8496b0", "#7f7f7f"]
b = ax.barh(niv, val, color=cols_ed, zorder=3)
for bi, v in zip(b, val):
    ax.text(v + 0.8, bi.get_y() + bi.get_height()/2, f"{v:.1f}%",
            va="center", fontsize=9, fontweight="bold")
ax.set_xlim(0, 60); ax.set_xlabel("% de la poblacion migrante (15+)")
ax.set_title("a) Maximo nivel educativo alcanzado (R1, 2021)")

ax = axes[1]
xx = np.arange(len(perf_r1))
ax.bar(xx, perf_r1["Escolaridad_media"], 0.5, color="#9dc3e6",
       label="Escolaridad media (anos)", zorder=3)
ax.set_xticks(xx); ax.set_xticklabels(perf_r1["Cohorte"], fontsize=8.5)
ax.set_ylabel("Anos de escolaridad equivalentes"); ax.set_ylim(0, 11.5)
ax2 = ax.twinx()
ax2.plot(xx, perf_r1["%_Universitario+"], marker="o", color=ROJO, lw=2,
         label="% universitario o mas", zorder=4)
ax2.set_ylabel("% con universitario o mas", color=ROJO)
ax2.tick_params(axis="y", colors=ROJO); ax2.set_ylim(0, 15); ax2.grid(False)
ax.set_title("b) Escolaridad media y educacion superior\npor cohorte de llegada (R1, 2021)")
h1, l1 = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper right")
ax.set_xlabel("Cohorte de llegada")
nota_fuente(fig, y=-0.02)
plt.tight_layout()
plt.savefig(f"{OUT}/fig08_capital_humano.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 9. Estado de origen en Venezuela (barras + mapa)
# -----------------------------------------------------------------------------
import geopandas as gpd

def descargar(url, destino):
    if not os.path.exists(destino):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            open(destino, "wb").write(r.read())

descargar(URL_VEN_EDOS, "ven_estados.geojson")
descargar(URL_COL_DPTOS, "col_dptos.geojson")
ven_g = gpd.read_file("ven_estados.geojson")
col_g = gpd.read_file("col_dptos.geojson")

est2 = estado.rename(columns={"Unnamed: 0": "Estado"}).set_index("Estado")
est2.loc["Resto de estados"] = 100 - est2.sum()
orden = ["Zulia", "Carabobo", "Aragua", "Distrito Capital", "Táchira",
         "Resto de estados"]
est2 = est2.loc[orden]

ven_g2 = ven_g.copy()
ven_g2["origen_r8"] = ven_g2["shapeName"].map(est2["R8"]).fillna(np.nan)

fig = plt.figure(figsize=(11.8, 5.2))
gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1], wspace=0.05,
                      left=0.04, right=0.98, top=0.85, bottom=0.13)
ax = fig.add_subplot(gs[0]); axm = fig.add_subplot(gs[1])
xx = np.arange(len(est2)); w = 0.36
b1 = ax.bar(xx - w/2, est2["R5"], w, color="#9dc3e6", label="R5 (2023)", zorder=3)
b2 = ax.bar(xx + w/2, est2["R8"], w, color=AZUL, label="R8 (2025)", zorder=3)
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.5,
            f"{b.get_height():.1f}", ha="center", fontsize=8.5)
ax.set_xticks(xx); ax.set_xticklabels(est2.index, fontsize=8.6)
ax.set_ylabel("% de la poblacion migrante (15+)")
ax.set_title("a) Principales estados de origen, 2023 vs. 2025", fontsize=10.5)
ax.legend(fontsize=8.5)
for i, est in enumerate(orden):
    d = est2.loc[est, "R8"] - est2.loc[est, "R5"]
    if abs(d) >= 3:
        ax.annotate(f"{'+' if d > 0 else ''}{d:.1f} pp",
                    xy=(i + w/2, est2.loc[est, 'R8'] + 3.4), ha="center",
                    fontsize=8.5, fontweight="bold",
                    color=VERDE if d > 0 else ROJO)

ven_g2.plot(color="#e8e8e8", linewidth=0.5, edgecolor="white", ax=axm)
ven_g2.dropna(subset=["origen_r8"]).plot(column="origen_r8", cmap=cmap_azul,
                                         linewidth=0.6, edgecolor="white",
                                         ax=axm, vmin=0, vmax=25)
for e, (xx_, yy_) in {"Zulia": (-72.6, 9.4), "Táchira": (-72.3, 7.3),
                      "Carabobo": (-68.9, 10.9), "Aragua": (-67.2, 9.1),
                      "Distrito Capital": (-66.0, 11.1)}.items():
    axm.annotate(f"{e}\n{est2.loc[e, 'R8']:.1f}%", xy=(xx_, yy_), fontsize=7.6,
                 fontweight="bold", ha="center", color="#111", zorder=5,
                 bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="#999",
                           alpha=0.85, lw=0.5))
axm.set_title("b) Mapa de origen en Venezuela (R8, 2025)", fontsize=10.5)
axm.set_axis_off(); axm.set_xlim(-73.9, -59.5); axm.set_ylim(0.4, 12.8)
sm = plt.cm.ScalarMappable(cmap=cmap_azul, norm=plt.Normalize(0, 25))
cb = fig.colorbar(sm, ax=axm, fraction=0.03, pad=0.01, shrink=0.7)
cb.set_label("%", fontsize=8.5); cb.ax.tick_params(labelsize=8)
axm.text(-73.5, 1.2, "En gris: estados que agrupan el 42,4% restante",
         fontsize=7, color="#666", style="italic")
fig.suptitle("Estado de origen en Venezuela de la poblacion migrante residente en Colombia",
             fontsize=12, fontweight="bold", y=0.97)
nota_fuente(fig, y=0.012)
plt.savefig(f"{OUT}/fig09_origen_venezuela.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 10. Mapa de calor de Colombia: ingreso (EPM) vs. residencia (stock oficial)
# -----------------------------------------------------------------------------
# Distribucion del stock por departamento: Migracion Colombia - GEME,
# corte febrero-2024 (total 2.857.528 personas).
resid = {
    "AMAZONAS": 1694, "ANTIOQUIA": 393392, "ARAUCA": 76906, "ATLÁNTICO": 205084,
    "BOGOTÁ, D.C.": 602896, "BOLÍVAR": 94076, "BOYACÁ": 38559, "CALDAS": 19135,
    "CAQUETÁ": 1405, "CASANARE": 26224, "CAUCA": 24528, "CESAR": 70163,
    "CHOCÓ": 3565, "CÓRDOBA": 19268, "CUNDINAMARCA": 149740, "GUAINÍA": 6800,
    "GUAVIARE": 1888, "HUILA": 12743, "LA GUAJIRA": 162389, "MAGDALENA": 82590,
    "META": 38599, "NARIÑO": 42481, "NORTE DE SANTANDER": 336291,
    "PUTUMAYO": 11595, "QUINDIO": 21700, "RISARALDA": 43940,
    "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA": 1443,
    "SANTANDER": 116630, "SUCRE": 17093, "TOLIMA": 23242,
    "VALLE DEL CAUCA": 200082, "VAUPÉS": 13, "VICHADA": 11374}

dpto2 = dpto.rename(columns={"Unnamed: 0": "Depto"}).set_index("Depto")
map_ing = {"Norte de Santander": "NORTE DE SANTANDER", "La Guajira": "LA GUAJIRA",
           "Arauca": "ARAUCA", "Nariño": "NARIÑO", "Cesar": "CESAR",
           "Atlántico": "ATLÁNTICO", "Vichada": "VICHADA", "Guainía": "GUAINÍA",
           "Bogotá": "BOGOTÁ, D.C.", "Antioquia": "ANTIOQUIA"}
dpto2.index = [map_ing.get(i, "OTRO") for i in dpto2.index]
dpto2 = dpto2.groupby(level=0).sum()

col_g2 = col_g.copy()
col_g2["ingreso_r8"] = col_g2["DPTO_CNMBR"].map(dpto2["R8"]).fillna(0)
tot_resid = sum(resid.values())
col_g2["residencia_pct"] = col_g2["DPTO_CNMBR"].map(
    {k: v / tot_resid * 100 for k, v in resid.items()})

fig = plt.figure(figsize=(12.4, 7.0))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.05], hspace=0.10, wspace=0.03,
                      left=0.02, right=0.98, top=0.82, bottom=0.115)
ax1 = fig.add_subplot(gs[0, 0]); ax2m = fig.add_subplot(gs[0, 1])
cax1 = fig.add_subplot(gs[1, 0]); cax2 = fig.add_subplot(gs[1, 1])

bins_a = [0, 0.5, 2, 5, 10, 20, 35, 60]
bins_b = [0, 0.3, 1, 2, 4, 8, 14, 22]
norm_a = BoundaryNorm(bins_a, cmap_azul.N)
norm_b = BoundaryNorm(bins_b, cmap_azul.N)

for ax, var, norm, tit in [
        (ax1, "ingreso_r8", norm_a,
         "a) Departamento de ingreso a Colombia\n(% de la poblacion migrante EPM, R8 may-jun 2025)"),
        (ax2m, "residencia_pct", norm_b,
         "b) Departamento de residencia actual\n(% del stock total, Migracion Colombia, ene-2024)")]:
    col_g2.plot(column=var, cmap=cmap_azul, norm=norm, linewidth=0.45,
                edgecolor="white", ax=ax)
    ax.set_title(tit, fontsize=10.5, pad=6)
    ax.set_xlim(-79.6, -66.4); ax.set_ylim(-4.4, 12.9)
    ax.set_axis_off()

cb1 = ColorbarBase(cax1, cmap=cmap_azul, norm=norm_a, orientation="horizontal",
                   boundaries=bins_a, ticks=bins_a)
cb1.set_label("% de ingresos", fontsize=9); cb1.ax.tick_params(labelsize=8)
cb2 = ColorbarBase(cax2, cmap=cmap_azul, norm=norm_b, orientation="horizontal",
                   boundaries=bins_b, ticks=bins_b)
cb2.set_label("% del stock residente", fontsize=9); cb2.ax.tick_params(labelsize=8)

etq2 = {"NORTE DE SANTANDER": (-73.6, 9.3, "Nte. de Santander\n56,3% | 11,8%"),
        "LA GUAJIRA": (-72.6, 11.9, "La Guajira\n22,4% | 5,7%"),
        "ARAUCA": (-69.6, 6.4, "Arauca\n12,4% | 2,7%"),
        "BOGOTÁ, D.C.": (-75.4, 4.6, "Bogota\n7,4% | 21,1%"),
        "ANTIOQUIA": (-76.6, 6.9, "Antioquia\n0,9% | 13,8%"),
        "ATLÁNTICO": (-75.6, 11.0, "Atlantico\n0,2% | 7,2%")}
for d, (xx_, yy_, t) in etq2.items():
    ax1.annotate(t, xy=(xx_, yy_), fontsize=7.2, ha="center", color="#111",
                 fontweight="bold", zorder=5,
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#999",
                           alpha=0.85, lw=0.5))
ax1.text(-66.8, 8.8, "VENEZUELA", rotation=90, fontsize=9, fontweight="bold",
         color="#555", va="center")

fig.suptitle("Geografia de la migracion venezolana en Colombia: corredores de entrada vs. asentamiento",
             fontsize=13, fontweight="bold", y=0.93)
fig.text(0.02, 0.012,
         "Fuente: panel a) elaboracion propia con microdatos EPM-DANE (R8); panel b) Migracion Colombia - GEME, informe feb-2024 (corte enero-2024; total 2.857.528 personas). El primer porcentaje de cada\n"
         "etiqueta corresponde al ingreso (panel a) y el segundo a la residencia (panel b). Se omite el Archipielago de San Andres por escala.",
         fontsize=7, color="#555", style="italic")
plt.savefig(f"{OUT}/fig10_mapa_colombia.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 11. Insercion laboral
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.3),
                         gridspec_kw={"width_ratios": [1.4, 1]})
ax = axes[0]
series = [("% Trabajando (actividad semana pasada)", "Trabajando", AZUL, "o"),
          ("% Oficios del hogar (actividad semana pasada)", "Oficios del hogar", GRIS, "s"),
          ("% Buscando trabajo (actividad semana pasada)", "Buscando trabajo", ROJO, "^"),
          ("% Estudiando (actividad semana pasada)", "Estudiando", VERDE, "D")]
for key, lbl, c, m in series:
    v = ip.loc[key, rondas8].astype(float).values
    ax.plot(range(8), v, marker=m, ms=5, lw=2, color=c, label=lbl, zorder=3)
ax.set_xticks(range(8)); ax.set_xticklabels(rondas8)
ax.set_ylabel("% de la poblacion (15+)")
ax.set_title("a) Actividad principal en la semana de referencia")
ax.legend(fontsize=8.5, loc="center right")
ax.annotate("64,1%", xy=(7, 64.06), xytext=(6.1, 68), fontsize=9,
            fontweight="bold", color=AZUL, arrowprops=dict(arrowstyle="->", color=AZUL))
ax.annotate("5,1%", xy=(7, 5.09), xytext=(5.6, 12), fontsize=9,
            fontweight="bold", color=ROJO, arrowprops=dict(arrowstyle="->", color=ROJO))
ax.set_ylim(0, 75)

ax = axes[1]
dif = ip.loc["% Con dificultades para encontrar trabajo", rondas8].astype(float).values
mask = ~np.isnan(dif)
cols_d = ["#9dc3e6" if r in ("R1", "R2") else AZUL for r in rondas8]
idx_m = [i for i in range(8) if mask[i]]
ax.bar([rondas8[i] for i in idx_m], dif[mask],
       color=[cols_d[i] for i in idx_m], zorder=3, width=0.6)
for k, i in enumerate(idx_m):
    ax.text(k, dif[i] + 1, f"{dif[i]:.1f}", ha="center", fontsize=8.5,
            fontweight="bold")
ax.set_ylabel("% con dificultad para encontrar trabajo")
ax.set_title("b) Dificultad para encontrar empleo")
ax.set_ylim(0, 70)
ax.axhline(dif[mask][-1], color=ROJO, ls=":", lw=1)
nota_fuente(fig, y=-0.02)
plt.tight_layout()
plt.savefig(f"{OUT}/fig11_insercion_laboral.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 12. Regularizacion, proteccion social e inclusion financiera
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9.2, 4.6))
xr5 = np.arange(4)
series_prot = [
    ("% Afiliado a salud", "Afiliacion a salud", VERDE, "o"),
    ("% Con PPT", "Permiso de Proteccion Temporal (PPT)", AZUL, "s"),
    ("% Con cuenta en entidad financiera", "Cuenta en entidad financiera", NARAN, "^"),
    ("% Sin documento de regularización", "Sin documento de regularizacion", ROJO, "D"),
    ("% Afiliado a pensiones", "Afiliacion a pensiones", GRIS, "v"),
]
for key, lbl, c, m in series_prot:
    v = ip.loc[key, ["R5", "R6", "R7", "R8"]].astype(float).values
    ax.plot(xr5, v, marker=m, ms=6, lw=2.2, color=c, label=lbl, zorder=3)
    ax.text(3.08, v[-1], f"{v[-1]:.1f}%", fontsize=8.7, color=c,
            fontweight="bold", va="center")
salud_r12 = ip.loc["% Afiliado a salud", ["R1", "R2"]].astype(float).values
salud_r58 = ip.loc["% Afiliado a salud", ["R5", "R6", "R7", "R8"]].astype(float).values
ax.plot([-2, -1] + list(xr5), list(salud_r12) + list(salud_r58),
        ls="--", lw=1, color=VERDE, alpha=0.45, zorder=2)
ax.text(-2.15, salud_r12[0] + 1.5, f"R1: {salud_r12[0]:.1f}%", fontsize=7.5, color=VERDE)
ax.text(-1.15, salud_r12[1] - 3.5, f"R2: {salud_r12[1]:.1f}%", fontsize=7.5, color=VERDE)
ax.set_xticks([-2, -1, 0, 1, 2, 3])
ax.set_xticklabels(["R1\n2021", "R2\n2021", "R5\n2023", "R6\n2023",
                    "R7\n2024", "R8\n2025"])
ax.set_ylabel("% de la poblacion (15+)")
ax.set_title("Regularizacion migratoria, proteccion social e inclusion financiera (2021-2025)")
ax.legend(fontsize=8.3, loc="upper left")
ax.set_xlim(-2.5, 3.95); ax.set_ylim(0, 84)
nota_fuente(fig)
plt.tight_layout(rect=[0, 0.05, 1, 1])
plt.savefig(f"{OUT}/fig12_proteccion_social.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 13. Analisis familiar: hogares migrantes
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(10.2, 6.4))
xh = np.arange(4); rlbl = ["R5\n2023", "R6\n2023", "R7\n2024", "R8\n2025"]

def panel(ax, vals, titulo, color, fmt="{:.2f}"):
    ax.plot(xh, vals, marker="o", color=color, lw=2.2, ms=7, zorder=3)
    for i, v in enumerate(vals):
        ax.text(i, v + (max(vals) - min(vals)) * 0.09 + max(vals) * 0.005,
                fmt.format(v), ha="center", fontsize=9, fontweight="bold",
                color="#333")
    ax.set_xticks(xh); ax.set_xticklabels(rlbl, fontsize=8.5)
    ax.set_title(titulo, fontsize=10)
    ax.set_ylim(min(vals) * 0.93, max(vals) * 1.06)

panel(axes[0, 0], ind_h["tamano_hogar_medio"].values,
      "a) Tamano medio del hogar (personas)", AZUL)
panel(axes[0, 1], ind_h["venezolanos_por_hogar"].values,
      "b) Personas venezolanas por hogar", AZUL2)
panel(axes[1, 0], ind_h["comidas_promedio"].values,
      "c) Comidas promedio al dia en el hogar", VERDE)
axes[1, 0].axhline(3, color=GRIS, ls=":", lw=1)
axes[1, 0].set_ylim(2.4, 2.9)

ax = axes[1, 1]
vals = ind_h["dificultad_alimentos_pct"].values
ax.bar(xh, vals, 0.55, color=[ROJO if v > 60 else NARAN for v in vals], zorder=3)
for i, v in enumerate(vals):
    ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9, fontweight="bold")
ax.set_xticks(xh); ax.set_xticklabels(rlbl, fontsize=8.5)
ax.set_title("d) Hogares con dificultad para comprar alimentos (%)", fontsize=10)
ax.set_ylim(0, 95)
ax.text(0, vals[0] + 9, "* pregunta de seleccion multiple", fontsize=6.8, color="#666")
fig.suptitle("Los hogares migrantes venezolanos: tamano, composicion y seguridad alimentaria (2023-2025)",
             fontsize=12, fontweight="bold")
nota_fuente(fig, y=-0.01)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig(f"{OUT}/fig13_hogares.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 14. Intenciones de permanencia, discriminacion y remesas
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.3))
ax = axes[0]
inten = [("% Intención: Permanecer en Colombia", "Permanecer en Colombia", AZUL, "o"),
         ("% Intención: No lo sabe aún / Lo está pensando", "No lo sabe aun", GRIS, "s"),
         ("% Intención: Regresar a Venezuela", "Regresar a Venezuela", NARAN, "^"),
         ("% Intención: Trasladarse a otro país", "Trasladarse a otro pais", VERDE, "D")]
for key, lbl, c, m in inten:
    v = ip.loc[key, ["R5", "R6", "R7", "R8"]].astype(float).values
    ax.plot(xr5, v, marker=m, ms=6, lw=2.2, color=c, label=lbl, zorder=3)
ax.text(3.06, 88.17, "88,2%", color=AZUL, fontweight="bold", fontsize=9.5, va="center")
ax.set_xticks(xr5); ax.set_xticklabels(["R5\n2023", "R6\n2023", "R7\n2024", "R8\n2025"])
ax.set_ylabel("% de la poblacion (15+)")
ax.set_title("a) Intencion de residencia a un ano")
ax.legend(fontsize=8, loc="center left")
ax.set_xlim(-0.3, 3.8); ax.set_ylim(0, 100)

ax = axes[1]
disc = ip.loc["% Se ha sentido discriminado", ["R2", "R5", "R6", "R7", "R8"]].astype(float).values
rem = ip.loc["% Envió remesas a Venezuela (último mes)",
             ["R1", "R2", "R5", "R6", "R7", "R8"]].astype(float).values
ax.plot([1, 2, 3, 4, 5], disc, marker="s", ms=6, lw=2.2, color=ROJO,
        label="Se ha sentido discriminado", zorder=3)
ax.plot(range(6), rem, marker="o", ms=6, lw=2.2, color=AZUL2,
        label="Envio remesas a Venezuela (ult. mes)", zorder=3)
ax.set_xticks(range(6))
ax.set_xticklabels(["R1\n2021", "R2\n2021", "R5\n2023", "R6\n2023",
                    "R7\n2024", "R8\n2025"])
ax.text(5.06, disc[-1], f"{disc[-1]:.1f}%", color=ROJO, fontweight="bold",
        fontsize=9, va="center")
ax.text(5.06, rem[-1] + 1.5, f"{rem[-1]:.1f}%", color=AZUL2, fontweight="bold",
        fontsize=9, va="center")
ax.set_ylabel("% de la poblacion (15+)")
ax.set_title("b) Discriminacion autopercibida y envio de remesas")
ax.legend(fontsize=8, loc="upper left")
ax.set_xlim(-0.3, 5.9); ax.set_ylim(0, 40)
nota_fuente(fig, y=-0.02)
plt.tight_layout()
plt.savefig(f"{OUT}/fig14_intenciones_discriminacion.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 15. Asimilacion por cohortes de llegada (salud y PPT)
# -----------------------------------------------------------------------------
orden_c = ["≤2017", "2018-2019", "2020-2021", "2022+"]
fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.3))
for ax, var, tit in [(axes[0], "%_Salud", "a) Afiliacion a salud por cohorte de llegada"),
                     (axes[1], "%_PPT", "b) Posesion del PPT por cohorte de llegada")]:
    for r, c, m in [("R5", "#9dc3e6", "o"), ("R6", "#2e75b6", "s"),
                    ("R7", "#c55a11", "^"), ("R8", "#1f4e79", "D")]:
        sub = perf_58[perf_58["Ronda"] == r].set_index("Cohorte").loc[orden_c]
        ax.plot(range(4), sub[var], marker=m, ms=5.5, lw=2, color=c,
                label=r, zorder=3)
    ax.set_xticks(range(4))
    ax.set_xticklabels(["≤2017", "2018-2019", "2020-2021", "2022+"], fontsize=9)
    ax.set_xlabel("Cohorte de llegada"); ax.set_ylabel("% de la cohorte")
    ax.set_title(tit, fontsize=10.5)
    ax.set_ylim(15, 95)
axes[0].legend(fontsize=8.5, title="Ronda", title_fontsize=8.5)
axes[1].annotate("gradiente de asimilacion:\nmas anos en Colombia -> mayor cobertura",
                 xy=(0, 80), xytext=(0.9, 55), fontsize=8.5, style="italic",
                 arrowprops=dict(arrowstyle="->", color="#555"))
axes[1].annotate("cohorte reciente (2022+):\nrezagada (~26-34%)", xy=(3, 26),
                 xytext=(1.6, 32), fontsize=8.5, color=ROJO,
                 arrowprops=dict(arrowstyle="->", color=ROJO))
nota_fuente(fig, y=-0.02)
plt.tight_layout()
plt.savefig(f"{OUT}/fig15_asimilacion_cohortes.png", bbox_inches="tight")
plt.close()

# -----------------------------------------------------------------------------
# FIGURA 16. Modelos econometricos de perfiles (forest plot M1, M3, M4)
# -----------------------------------------------------------------------------
key_terms = {
    "M1": [("mujer", "Mujer"), ("edad", "Edad"), ("edad2", "Edad² /100")],
    "M3": [("esc_anios", "Anos de escolaridad"), ("edad", "Edad /10"),
           ("mujer", "Mujer"), ("anios_en_col", "Anos en Colombia")],
    "M4": [("esc_anios", "Anos de escolaridad"), ("mujer", "Mujer"),
           ("anios_en_col", "Anos en Colombia")],
}
mod_names = {"M1": "M1: Anos de escolaridad (R1)",
             "M3": "M3: Trabajando 0/1 (R1)",
             "M4": "M4: log ingreso mensual (R1∩R3)"}
fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.9))
for ax, (mod, terms) in zip(axes, key_terms.items()):
    sub = mods[mods["Modelo"] == mod].set_index("Termino")
    labels = []
    for j, (t, lab) in enumerate(terms):
        if t not in sub.index:
            continue
        c0 = sub.loc[t, "Coeficiente"]
        lo = sub.loc[t, "IC95_inf"]; hi = sub.loc[t, "IC95_sup"]
        scale = 100 if t == "edad2" else (10 if (t == "edad" and mod == "M3") else 1)
        c0, lo, hi = c0 * scale, lo * scale, hi * scale
        sig = sub.loc[t, "Signif"]
        sig = sig if isinstance(sig, str) else ""
        labels.append(lab)
        ax.plot([lo, hi], [j, j], color=AZUL, lw=2.2, zorder=2)
        ax.plot([c0], [j], "o", color=ROJO if sig else AZUL, ms=8, zorder=3)
        ax.text(hi, j + 0.18, f"{c0:.3f}{'*' if sig else ' (n.s.)'}",
                fontsize=8, ha="center")
    ax.axvline(0, color=GRIS, ls="--", lw=1)
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_title(mod_names[mod], fontsize=9.8)
    ax.set_xlabel("Coeficiente (IC 95%)", fontsize=9)
fig.suptitle("Determinantes del capital humano, el empleo y el ingreso de la poblacion migrante "
             "(WLS con FEX, errores cluster por hogar)", fontsize=10.5, fontweight="bold")
nota_fuente(fig, y=-0.03)
plt.tight_layout(rect=[0, 0.02, 1, 0.90])
plt.savefig(f"{OUT}/fig16_modelo_perfiles.png", bbox_inches="tight")
plt.close()

print("Listo: 13 figuras generadas en ./figuras/")
