"""
================================================================================
MODELO WOOLDRIDGE (1995) CORREGIDO - COMERCIO VENEZUELA-COLOMBIA (2013-2024)
================================================================================
Modelo de correccion de sesgo de seleccion en datos de panel:
  Etapa 1: Probit del margen extensivo (decision de comerciar) -> IMR
  Etapa 2: Panel de efectos fijos del margen intensivo + IMR (Wooldridge)

CORRECCIONES RESPECTO AL CODIGO ORIGINAL:
  1. El IMR se evalua sobre el INDICE LINEAL (X*beta) del Probit, no sobre las
     probabilidades predichas. Ademas se acota Phi(z) para evitar divisiones
     por cero (proteccion numerica).
  2. El modelo FE estandar se estima SIN el IMR y el modelo Wooldridge CON el
     IMR. En el codigo original ambos eran el mismo modelo (se estimaba dos
     veces el FE+IMR), lo que impedia comparar y evaluar la correccion.
  3. Si el panel no esta balanceado (celdas producto-anio ausentes), se
     completan con flujo = 0, pues en datos de comercio la ausencia del registro
     equivale a que no hubo operacion. Sin esto, el Probit de importaciones no
     es estimable (no habria ceros en la muestra).
  4. No se imputa el IMR con su media (el original usaba fillna(mean)), practica
     que introduce ruido; con datos completos no debe haber IMR faltantes.
  5. No se imputa el IMR con su media (el original usaba fillna(mean)), practica
     que introduce ruido; con datos completos no debe haber IMR faltantes.
  6. La variable 'border' NO es binaria: toma valores 0, 1 y 2 (frontera
     abierta / cerrada / apertura parcial-reapertura, segun la historia
     reciente de la frontera colombo-venezolana). El codigo original la
     trataba como numerica continua. Se corrige creando las dummies
     'frontera_cerrada' y 'frontera_parcial' con base = frontera abierta.
  7. Errores robustos agrupados (cluster) por producto en todos los modelos.
  8. La prueba de Hausman se calcula con errores convencionales (no cluster):
     el test requiere eficiencia de RE bajo H0; con covarianzas cluster el
     estadistico salia negativo (V_FE - V_RE no semidefinida positiva).
  6. Graficas: titulos y etiquetas adaptados al sentido real del flujo
     (exportacion o importacion), heatmap robusto a filas con suma cero,
     leyendas solo cuando existen anos de frontera cerrada, y manejo seguro
     de indices en residuos y valores ajustados.

USO:
  python modelo_wooldridge_corregido.py <ruta_excel> <carpeta_salida> <etiqueta_flujo>
  Ejemplo:
  python modelo_wooldridge_corregido.py Exportaciones.xlsx salida_exp "Exportaciones Venezuela -> Colombia"
================================================================================
"""

import os
import sys
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import chi2
from statsmodels.api import add_constant
from statsmodels.discrete.discrete_model import Probit
from linearmodels.panel import PanelOLS, PooledOLS, RandomEffects, compare

warnings.filterwarnings('ignore')

# =============================================================================
# 0. PARAMETROS DE EJECUCION
# =============================================================================
if len(sys.argv) >= 4:
    RUTA_EXCEL = sys.argv[1]
    DIRECTORIO_SALIDA = sys.argv[2]
    FLUJO = sys.argv[3]
else:
    RUTA_EXCEL = "Exportaciones.xlsx"
    DIRECTORIO_SALIDA = "salida_wooldridge"
    FLUJO = "Exportaciones"

FLUJO_LOWER = FLUJO.lower()
ES_EXPORTACION = 'export' in FLUJO_LOWER
NOMBRE_FLUJO_CORTO = 'Exportaciones' if ES_EXPORTACION else 'Importaciones'
SENTIDO = 'Venezuela → Colombia' if ES_EXPORTACION else 'Colombia → Venezuela'

os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)

# =============================================================================
# CONFIGURACION DE COLORES Y ESTILOS
# =============================================================================
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.titlesize'] = 14
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams['axes.linewidth'] = 0.8

COLORES = {
    'primary': '#2E4057',    # Azul oscuro
    'secondary': '#048A81',  # Verde cerceta
    'accent': '#F4A261',     # Naranja suave
    'alert': '#E76F51',      # Rojo terracota
    'neutral': '#264653',    # Verde muy oscuro
    'fondo': '#B0BEC5'       # Gris
}
colores_top = ['#E63946', '#F77F00', '#06A77D', '#118AB2', '#073B4C', '#2E4057', '#048A81', '#F4A261']


def detectar_columna(nombres_posibles, columnas):
    for nombre in nombres_posibles:
        if nombre in columnas:
            return nombre
        for col in columnas:
            if col.lower() == nombre.lower():
                return col
            if len(nombre) >= 3 and (nombre.lower() in col.lower() or col.lower() in nombre.lower()):
                return col
    return None


def agregar_sombra_frontera(ax, df_local):
    """Sombrea los anos segun el estado de la frontera (1=cerrada, 2=parcial)."""
    if 'border' not in df_local.columns:
        return
    for valor, color, etiqueta in [(1, COLORES['alert'], 'Frontera cerrada'),
                                   (2, COLORES['accent'], 'Apertura parcial')]:
        anios_estado = np.sort(df_local[df_local['border'] == valor]['anio'].dropna().unique())
        if len(anios_estado) == 0:
            continue
        bloques = [[anios_estado[0]]]
        for a in anios_estado[1:]:
            if a == bloques[-1][-1] + 1:
                bloques[-1].append(a)
            else:
                bloques.append([a])
        for i, bloque in enumerate(bloques):
            label = etiqueta if i == 0 else ""
            ax.axvspan(min(bloque) - 0.5, max(bloque) + 0.5, color=color,
                       alpha=0.15, label=label, zorder=0)


# =============================================================================
# 1. CARGA DE DATOS
# =============================================================================
print("=" * 80)
print(f"CARGANDO DATOS - {FLUJO.upper()}")
print("=" * 80)

df = pd.read_excel(RUTA_EXCEL) if RUTA_EXCEL.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(RUTA_EXCEL)
print(f"Archivo: {RUTA_EXCEL}  |  Filas: {len(df)}  |  Columnas: {len(df.columns)}")

# =============================================================================
# 2. DETECCION Y RENOMBRADO DE VARIABLES
# =============================================================================
col_producto = detectar_columna(['producto', 'hs2', 'codigo', 'id_producto'], df.columns) or df.columns[0]
col_anio = detectar_columna(['anio', 'año', 'year', 'periodo'], df.columns) or df.columns[1]
col_flujo = detectar_columna(['exportaciones', 'importaciones', 'export', 'import', 'trade', 'valor'], df.columns) or df.columns[2]
col_pib_col = detectar_columna(['pib_col', 'pibcol', 'gdp_col'], df.columns)
col_pib_ven = detectar_columna(['pib_ven', 'pibven', 'gdp_ven'], df.columns)
col_border = detectar_columna(['border', 'frontera', 'cierre', 'cierre_frontera'], df.columns)
col_perecedero = detectar_columna(['perecedero', 'perishable', 'dummy_perecedero'], df.columns)
col_nombre = detectar_columna(['nombre_producto', 'nombre', 'descripcion'], df.columns)

mapeo = {col_producto: 'producto', col_anio: 'anio', col_flujo: 'exportaciones'}
if col_nombre: mapeo[col_nombre] = 'nombre_producto'
if col_pib_col: mapeo[col_pib_col] = 'pib_col'
if col_pib_ven: mapeo[col_pib_ven] = 'pib_ven'
if col_border: mapeo[col_border] = 'border'
if col_perecedero: mapeo[col_perecedero] = 'perecedero'

for old, new in mapeo.items():
    if new not in df.columns and old in df.columns:
        df = df.rename(columns={old: new})

# =============================================================================
# 3. CREACION DE VARIABLES Y BALANCEO DEL PANEL
# =============================================================================
print("\n" + "=" * 80)
print("PREPARANDO VARIABLES")
print("=" * 80)

df['anio'] = pd.to_numeric(df['anio'], errors='coerce')
df['exportaciones'] = pd.to_numeric(df['exportaciones'], errors='coerce')
for c in ['pib_col', 'pib_ven', 'border', 'perecedero']:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')

# --- CORRECCION 3: balancear el panel (celdas ausentes = flujo cero) ---
productos_unicos = df['producto'].nunique()
anios_unicos = df['anio'].nunique()
celdas_esperadas = productos_unicos * anios_unicos
celdas_faltantes = celdas_esperadas - len(df)

if celdas_faltantes > 0:
    print(f"Panel no balanceado: {celdas_faltantes} celdas producto-anio ausentes de {celdas_esperadas}.")
    print("Se completan con flujo = 0 (ausencia de registro = no hubo operacion comercial).")
    fijas = df.groupby('producto').agg(
        nombre_producto=('nombre_producto', 'first') if 'nombre_producto' in df.columns else ('producto', 'first'),
        perecedero=('perecedero', 'first')).reset_index()
    macro = df.groupby('anio')[['pib_col', 'pib_ven', 'border']].first().reset_index()
    idx_full = pd.MultiIndex.from_product(
        [fijas['producto'], sorted(df['anio'].unique())], names=['producto', 'anio'])
    df = df.set_index(['producto', 'anio']).reindex(idx_full).reset_index()
    df['exportaciones'] = df['exportaciones'].fillna(0)
    df = df.drop(columns=[c for c in ['nombre_producto', 'perecedero', 'pib_col', 'pib_ven', 'border'] if c in df.columns])
    df = df.merge(fijas, on='producto', how='left').merge(macro, on='anio', how='left')

# Variables del modelo
df['dummy_exporta'] = (df['exportaciones'] > 0).astype(int)
df['ln_exportaciones'] = np.where(df['exportaciones'] > 0, np.log(df['exportaciones']), np.nan)
df['ln_pib_col'] = np.log(df['pib_col'])
df['ln_pib_ven'] = np.log(df['pib_ven'])
df['border'] = df['border'].fillna(0).astype(int)
df['perecedero'] = df['perecedero'].fillna(0)

# --- CORRECCION 6: border es categorica (0=abierta, 1=cerrada, 2=parcial) ---
df['frontera_cerrada'] = (df['border'] == 1).astype(int)
df['frontera_parcial'] = (df['border'] == 2).astype(int)
print(f"Estados de la frontera (0=abierta, 1=cerrada, 2=parcial): {sorted(df['border'].unique())}")
print(f"Anios frontera cerrada: {sorted(df[df['border'] == 1]['anio'].unique())}")
print(f"Anios apertura parcial: {sorted(df[df['border'] == 2]['anio'].unique())}")

print(f"Observaciones: {len(df)} | Productos: {df['producto'].nunique()} | Anios: {df['anio'].nunique()}")
print(f"Distribucion dummy (0 = sin flujo, 1 = con flujo): {df['dummy_exporta'].value_counts().to_dict()}")

# =============================================================================
# 4. LIMPIEZA Y ESTADISTICAS DESCRIPTIVAS
# =============================================================================
vars_modelo = ['producto', 'anio', 'exportaciones', 'dummy_exporta',
               'ln_pib_col', 'ln_pib_ven', 'border', 'perecedero']
df = df.dropna(subset=[v for v in vars_modelo if v in df.columns]).copy()

print("\n" + "=" * 80)
print("ESTADISTICAS DESCRIPTIVAS")
print("=" * 80)
desc = df[['exportaciones', 'ln_pib_col', 'ln_pib_ven', 'frontera_cerrada',
           'frontera_parcial', 'perecedero', 'dummy_exporta']].describe().T
print(desc.round(4))

# =============================================================================
# 5. ETAPA 1: PROBIT (MARGEN EXTENSIVO) E IMR
# =============================================================================
print("\n" + "=" * 80)
print("ETAPA 1: PROBIT (DECISION DE COMERCIAR)")
print("=" * 80)

probit_vars = ['ln_pib_col', 'ln_pib_ven', 'frontera_cerrada', 'frontera_parcial', 'perecedero']
X_probit = add_constant(df[probit_vars].astype(float), has_constant='add')
y_probit = df['dummy_exporta'].astype(int)

probit_model = Probit(y_probit, X_probit).fit(disp=0)
print(probit_model.summary())

# --- CORRECCION CLAVE 1: IMR sobre el indice lineal X*beta, no sobre probabilidades ---
linear_index = np.dot(X_probit, probit_model.params)
phi = stats.norm.pdf(linear_index)
Phi = np.clip(stats.norm.cdf(linear_index), 1e-10, 1 - 1e-10)  # proteccion numerica
df['IMR'] = phi / Phi

print(f"\nIMR - media: {df['IMR'].mean():.4f} | min: {df['IMR'].min():.4f} | max: {df['IMR'].max():.4f}")
print(f"Pseudo R2 del Probit: {probit_model.prsquared:.4f}")

res_probit = pd.DataFrame({
    'Variable': probit_model.params.index,
    'Coeficiente': probit_model.params.values,
    'SE': probit_model.bse.values,
    'z': probit_model.tvalues.values,
    'P_valor': probit_model.pvalues.values,
    'Sig': ['***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.1 else '' for p in probit_model.pvalues]
})

# =============================================================================
# 6. ETAPA 2: PANEL DE FLUJOS POSITIVOS (MARGEN INTENSIVO)
# =============================================================================
print("\n" + "=" * 80)
print("ETAPA 2: PANEL CON CORRECCION DE WOOLDRIDGE (FE + IMR)")
print("=" * 80)

df_panel = df[df['dummy_exporta'] == 1].dropna(subset=['ln_exportaciones']).copy()
df_panel = df_panel.set_index(['producto', 'anio']).sort_index()
y_panel = df_panel['ln_exportaciones'].astype(float)

X_base = ['ln_pib_col', 'ln_pib_ven', 'frontera_cerrada', 'frontera_parcial']            # sin IMR
X_wool = ['ln_pib_col', 'ln_pib_ven', 'frontera_cerrada', 'frontera_parcial', 'IMR']     # con IMR

print(f"Observaciones del panel (flujos positivos): {len(df_panel)}")

# Pooled OLS (con IMR, referencia)
model_pooled = PooledOLS(y_panel, add_constant(df_panel[X_wool])).fit(
    cov_type='clustered', cluster_entity=True)

# Efectos aleatorios (con IMR, referencia)
model_re = RandomEffects(y_panel, add_constant(df_panel[X_wool])).fit(
    cov_type='clustered', cluster_entity=True)

# --- CORRECCION CLAVE 2: FE estandar SIN IMR ---
model_fe_std = PanelOLS(y_panel, df_panel[X_base], entity_effects=True).fit(
    cov_type='clustered', cluster_entity=True)

# Wooldridge: FE + IMR
model_wooldridge = PanelOLS(y_panel, df_panel[X_wool], entity_effects=True).fit(
    cov_type='clustered', cluster_entity=True)

print("\n--- POOLED OLS ---");      print(model_pooled.summary)
print("\n--- EFECTOS ALEATORIOS ---"); print(model_re.summary)
print("\n--- EFECTOS FIJOS (SIN IMR) ---"); print(model_fe_std.summary)
print("\n--- WOOLDRIDGE (FE + IMR) ---");  print(model_wooldridge.summary)

print("\n" + "=" * 80)
print("COMPARACION DE MODELOS DE PANEL")
print("=" * 80)
comp = compare({'Pooled OLS': model_pooled, 'Efectos Aleatorios': model_re,
                'FE Estandar': model_fe_std, 'Wooldridge (FE+IMR)': model_wooldridge}, stars=True)
print(comp)

# Prueba de Hausman (FE estandar vs RE sin IMR para comparabilidad).
# Se estima con errores CONVENCIONALES (no robustos): el test exige que el
# estimador RE sea eficiente bajo H0 para que V_FE - V_RE sea semidefinida
# positiva; con covarianzas cluster el estadistico puede salir negativo.
model_re_base = RandomEffects(y_panel, add_constant(df_panel[X_base])).fit()
model_fe_haus = PanelOLS(y_panel, df_panel[X_base], entity_effects=True).fit()
b_fe, b_re = model_fe_haus.params, model_re_base.params.drop('const', errors='ignore')
v_fe, v_re = model_fe_haus.cov, model_re_base.cov.drop(index='const', columns='const', errors='ignore')
common = b_fe.index.intersection(b_re.index)
diff = (b_fe[common] - b_re[common]).values
var_diff = (v_fe.loc[common, common] - v_re.loc[common, common]).values
hausman_nota = ''
try:
    h_stat = float(diff.T @ np.linalg.pinv(var_diff) @ diff)
    if h_stat < 0:
        # Estadistico negativo => la diferencia de covarianzas no es PSD:
        # evidencia de que los efectos no se correlacionan con los regresores
        # (no se rechaza RE). Se acota a 0 por convencion.
        h_stat, h_pval = 0.0, 1.0
        hausman_nota = ' (estadistico crudo negativo: V_FE - V_RE no es semidefinida positiva; se acota a cero)'
    else:
        h_pval = float(1 - chi2.cdf(h_stat, len(diff)))
except Exception:
    h_stat, h_pval = np.nan, np.nan
print(f"\nPrueba de Hausman (FE vs RE): chi2 = {h_stat:.4f} | p-valor = {h_pval:.4f}{hausman_nota}")
print("Decision:", "Efectos FIJOS preferidos (se rechaza H0)" if h_pval < 0.05
      else "Efectos ALEATORIOS no rechazados" if not np.isnan(h_pval) else "No computable")

# =============================================================================
# 7. GRAFICAS
# =============================================================================
print("\n" + "=" * 80)
print("GENERANDO GRAFICAS")
print("=" * 80)

sns.set_style("whitegrid", {'grid.color': '#E0E0E0'})
cmap_custom = LinearSegmentedColormap.from_list('custom_cmap', [COLORES['alert'], 'white', COLORES['primary']])
hay_cierre = (df['border'] > 0).any()
ruta_fig = lambda nombre: os.path.join(DIRECTORIO_SALIDA, nombre)

# --- 1. Evolucion del flujo y del margen extensivo ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
fig.patch.set_facecolor('white')
yearly_total = df.groupby('anio')['exportaciones'].sum() / 1e6
ax1.bar(yearly_total.index, yearly_total.values, color=COLORES['primary'], alpha=0.9,
        edgecolor='black', linewidth=0.5)
ax1.set_ylabel(f'{NOMBRE_FLUJO_CORTO} (Millones USD)', fontweight='bold')
ax1.set_title(f'Evolución de {NOMBRE_FLUJO_CORTO} {SENTIDO}', fontweight='bold', pad=15)
ax1.grid(axis='y', alpha=0.3)
agregar_sombra_frontera(ax1, df)
if hay_cierre: ax1.legend(loc='upper right')

yearly_products = df.groupby('anio')['dummy_exporta'].sum()
ax2.bar(yearly_products.index, yearly_products.values, color=COLORES['secondary'], alpha=0.9,
        edgecolor='black', linewidth=0.5)
ax2.set_xlabel('Año', fontweight='bold')
ax2.set_ylabel('Productos con flujo positivo', fontweight='bold')
ax2.set_title('Número de Productos con Flujo Positivo', fontweight='bold', pad=15)
ax2.grid(axis='y', alpha=0.3)
agregar_sombra_frontera(ax2, df)
if hay_cierre: ax2.legend(loc='upper right')
plt.tight_layout()
plt.savefig(ruta_fig('01_evolucion.png'), facecolor='white')
plt.close()

# --- 2. Heatmap producto x anio (participacion % dentro de cada producto) ---
idx_col = 'nombre_producto' if 'nombre_producto' in df.columns else 'producto'
pivot = df.pivot_table(values='exportaciones', index=idx_col, columns='anio', aggfunc='sum', fill_value=0)
if pivot.shape[0] > 1 and pivot.shape[1] > 1:
    row_sum = pivot.sum(axis=1).replace(0, np.nan)  # evita division por cero
    pivot_pct = pivot.div(row_sum, axis=0) * 100
    pivot_pct = pivot_pct.dropna(how='all')
    fig, ax = plt.subplots(figsize=(14, min(12, max(6, pivot_pct.shape[0] * 0.35))))
    fig.patch.set_facecolor('white')
    sns.heatmap(pivot_pct, cmap=cmap_custom, linewidths=0.5, linecolor='lightgray',
                cbar_kws={'label': 'Participacion dentro del producto (%)'}, ax=ax)
    ax.set_title(f'Distribución Temporal de {NOMBRE_FLUJO_CORTO} por Producto', fontweight='bold', pad=15)
    ax.set_ylabel('')
    plt.tight_layout()
    plt.savefig(ruta_fig('02_heatmap.png'), facecolor='white')
    plt.close()

# --- 3. Matriz de correlacion ---
corr_vars = ['exportaciones', 'ln_pib_col', 'ln_pib_ven', 'frontera_cerrada', 'frontera_parcial', 'perecedero']
fig, ax = plt.subplots(figsize=(9, 7))
fig.patch.set_facecolor('white')
corr = df[corr_vars].corr()
sns.heatmap(corr, cmap=cmap_custom, center=0, square=True, linewidths=1, annot=True,
            fmt='.3f', ax=ax, linecolor='white', vmin=-1, vmax=1)
ax.set_title('Matriz de Correlación', fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig(ruta_fig('03_correlacion.png'), facecolor='white')
plt.close()

# --- 4. Coeficientes del modelo Wooldridge con IC 95% ---
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('white')
coefs = model_wooldridge.params.drop('const', errors='ignore')
errs = model_wooldridge.std_errors[coefs.index]
pvals = model_wooldridge.pvalues[coefs.index]
order = [v for v in ['ln_pib_col', 'ln_pib_ven', 'frontera_cerrada', 'frontera_parcial', 'IMR'] if v in coefs.index]
coefs, errs, pvals = coefs.reindex(order), errs.reindex(order), pvals.reindex(order)
nombres = {'ln_pib_col': 'PIB Colombia (log)', 'ln_pib_ven': 'PIB Venezuela (log)',
           'frontera_cerrada': 'Frontera cerrada', 'frontera_parcial': 'Apertura parcial',
           'IMR': 'IMR (selección)'}
y_pos = np.arange(len(coefs))
colors = [COLORES['secondary'] if p < 0.05 else COLORES['neutral'] for p in pvals]
ax.barh(y_pos, coefs.values, xerr=1.96 * errs.values, color=colors, alpha=0.9,
        capsize=4, edgecolor='black')
ax.set_yticks(y_pos)
ax.set_yticklabels([nombres.get(v, v) for v in order])
ax.axvline(x=0, color='black', linewidth=1)
ax.set_xlabel('Coeficiente (IC 95%)', fontweight='bold')
ax.set_title(f'Wooldridge (FE + IMR) - {NOMBRE_FLUJO_CORTO}', fontweight='bold', pad=15)
ax.grid(axis='x', alpha=0.3)
for i, (c, p) in enumerate(zip(coefs.values, pvals.values)):
    sig = '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.1 else ''
    ax.text(c + (0.02 if c >= 0 else -0.02), i, f'{c:.3f}{sig}', va='center',
            ha='left' if c >= 0 else 'right', fontsize=9)
plt.tight_layout()
plt.savefig(ruta_fig('04_coeficientes.png'), facecolor='white')
plt.close()

# --- 5. Diagnostico de residuos ---
residuals = model_wooldridge.resids
fitted = model_wooldridge.fitted_values.values.squeeze()
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
fig.patch.set_facecolor('white')

ax1.scatter(fitted, residuals, alpha=0.6, color=COLORES['primary'], s=25, edgecolor='white')
ax1.axhline(y=0, color=COLORES['alert'], linestyle='--', linewidth=1.5)
ax1.set_xlabel('Valores ajustados'); ax1.set_ylabel('Residuos')
ax1.set_title('Residuos vs Ajustados', fontweight='bold'); ax1.grid(alpha=0.3)

stats.probplot(residuals.squeeze(), dist="norm", plot=ax2)
ax2.get_lines()[0].set_markerfacecolor(COLORES['secondary'])
ax2.get_lines()[0].set_markeredgecolor(COLORES['secondary'])
ax2.get_lines()[0].set_markersize(4); ax2.get_lines()[0].set_alpha(0.6)
ax2.get_lines()[1].set_color(COLORES['alert']); ax2.get_lines()[1].set_linewidth(2)
ax2.set_title('Q-Q Plot de Normalidad', fontweight='bold'); ax2.grid(alpha=0.3)

res_np = residuals.squeeze().values
sns.histplot(res_np, bins=25, stat='density', color=COLORES['accent'], edgecolor='black', alpha=0.7, ax=ax3)
mu, sigma = stats.norm.fit(res_np)
x = np.linspace(res_np.min(), res_np.max(), 100)
ax3.plot(x, stats.norm.pdf(x, mu, sigma), color=COLORES['primary'], linewidth=2.5)
ax3.set_xlabel('Residuos'); ax3.set_ylabel('Densidad')
ax3.set_title('Histograma de Residuos', fontweight='bold'); ax3.grid(alpha=0.3)

resid_df = residuals.reset_index()
col_res = [c for c in resid_df.columns if c not in ('producto', 'anio')][0]
ax4.scatter(resid_df['anio'], resid_df[col_res], alpha=0.6, color=COLORES['primary'], s=25, edgecolor='white')
ax4.axhline(y=0, color=COLORES['alert'], linestyle='--', linewidth=1.5)
agregar_sombra_frontera(ax4, df)
if hay_cierre: ax4.legend(loc='upper right')
ax4.set_xlabel('Año'); ax4.set_ylabel('Residuos')
ax4.set_title('Residuos en el Tiempo', fontweight='bold'); ax4.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(ruta_fig('05_residuos.png'), facecolor='white')
plt.close()

# --- 6. Variables macro vs flujo ---
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.patch.set_facecolor('white')
for ax, pib_col_name, titulo in [(axes[0, 0], 'pib_col', 'PIB Colombia'),
                                 (axes[0, 1], 'pib_ven', 'PIB Venezuela')]:
    pib_y = df.groupby('anio')[pib_col_name].first() / 1e9
    ax2 = ax.twinx()
    ax.plot(pib_y.index, pib_y.values, color=COLORES['secondary'], linewidth=2.5, marker='o', label='PIB (miles de millones USD)')
    ax2.plot(yearly_total.index, yearly_total.values, color=COLORES['primary'], linewidth=2.5, marker='s', label=f'{NOMBRE_FLUJO_CORTO} (millones USD)')
    agregar_sombra_frontera(ax, df)
    ax.set_title(f'{titulo} vs {NOMBRE_FLUJO_CORTO}', fontweight='bold')
    ax.set_xlabel('Año'); ax.grid(alpha=0.3)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='lower left', fontsize=8)

ax = axes[1, 0]
be = df.groupby(['anio', 'border'])['exportaciones'].mean().unstack().reindex(columns=[0, 1, 2])
paleta_border = [COLORES['primary'], COLORES['alert'], COLORES['accent']][:be.notna().any().sum()]
be.plot(kind='bar', ax=ax, color=paleta_border, alpha=0.85)
leyendas_border = {0: 'Abierta', 1: 'Cerrada', 2: 'Parcial'}
ax.legend([leyendas_border[c] for c in be.columns], fontsize=8)
ax.set_xticklabels([str(int(a)) for a in be.index], rotation=45)
ax.set_title('Flujo Promedio por Estado de la Frontera', fontweight='bold')
ax.set_xlabel('Año'); ax.grid(alpha=0.3)

ax = axes[1, 1]
ax.hist(df['IMR'], bins=40, alpha=0.8, color=COLORES['accent'], edgecolor='black', density=True)
ax.axvline(df['IMR'].mean(), color=COLORES['primary'], linestyle='--', label=f"Media: {df['IMR'].mean():.3f}")
ax.legend()
ax.set_title('Distribución del IMR', fontweight='bold'); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(ruta_fig('06_variables.png'), facecolor='white')
plt.close()

# --- 7. Margenes extensivo e intensivo ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
fig.patch.set_facecolor('white')
ext = df.groupby('anio')['dummy_exporta'].sum()
total_prod = df.groupby('anio')['producto'].nunique()
ext_pct = (ext / total_prod) * 100
ax1.plot(ext_pct.index, ext_pct.values, color=COLORES['primary'], linewidth=2.5, marker='o', markersize=8)
ax1.fill_between(ext_pct.index, ext_pct.values, alpha=0.2, color=COLORES['primary'])
agregar_sombra_frontera(ax1, df)
if hay_cierre: ax1.legend()
ax1.set_title('Margen Extensivo (% productos activos)', fontweight='bold')
ax1.set_xlabel('Año'); ax1.set_ylabel('%'); ax1.grid(alpha=0.3)

intens = df[df['dummy_exporta'] == 1].groupby('anio')['exportaciones'].mean() / 1e6
ax2.plot(intens.index, intens.values, color=COLORES['secondary'], linewidth=2.5, marker='s', markersize=8)
ax2.fill_between(intens.index, intens.values, alpha=0.2, color=COLORES['secondary'])
agregar_sombra_frontera(ax2, df)
if hay_cierre: ax2.legend()
ax2.set_title('Margen Intensivo (promedio millones USD)', fontweight='bold')
ax2.set_xlabel('Año'); ax2.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(ruta_fig('07_margenes.png'), facecolor='white')
plt.close()

# --- 8. Prediccion vs real ---
fig, ax = plt.subplots(figsize=(8, 8))
fig.patch.set_facecolor('white')
y_real = df_panel['ln_exportaciones'].squeeze()
y_pred = pd.Series(fitted, index=y_real.index)
ax.scatter(y_real, y_pred, alpha=0.6, color=COLORES['primary'], s=30, edgecolor='white')
min_v = min(float(y_real.min()), float(y_pred.min()))
max_v = max(float(y_real.max()), float(y_pred.max()))
ax.plot([min_v, max_v], [min_v, max_v], color=COLORES['alert'], linewidth=2, linestyle='--', label='Linea 45 grados')
ax.legend()
ax.set_xlabel('log(flujo) real'); ax.set_ylabel('log(flujo) ajustado')
ax.set_title(f'Predicción vs Real | R2 = {model_wooldridge.rsquared:.4f}', fontweight='bold')
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(ruta_fig('08_prediccion.png'), facecolor='white')
plt.close()

# --- 9. Trayectoria margen extensivo-intensivo (quiver) ---
fig, ax = plt.subplots(figsize=(10, 8))
fig.patch.set_facecolor('white')
anios_validos = sorted(df['anio'].dropna().unique())
x_coords = df.groupby('anio')['dummy_exporta'].sum().reindex(anios_validos).values
y_coords = (df[df['dummy_exporta'] == 1].groupby('anio')['exportaciones'].mean() / 1e6).reindex(anios_validos).values
validos = ~np.isnan(y_coords)
x_coords, y_coords, anios_validos = x_coords[validos], y_coords[validos], np.array(anios_validos)[validos]
u, v = np.diff(x_coords), np.diff(y_coords)
ax.scatter(x_coords, y_coords, color=COLORES['primary'], s=60, zorder=3, edgecolor='white')
ax.quiver(x_coords[:-1], y_coords[:-1], u, v, angles='xy', scale_units='xy', scale=1,
          color=COLORES['alert'], width=0.004, alpha=0.8)
for i, txt in enumerate(anios_validos):
    ax.annotate(str(int(txt)), (x_coords[i], y_coords[i]), xytext=(8, 5),
                textcoords='offset points', fontsize=10, color=COLORES['primary'], fontweight='bold')
ax.set_xlabel('Margen extensivo (N productos con flujo)', fontweight='bold')
ax.set_ylabel('Margen intensivo (promedio millones USD)', fontweight='bold')
ax.set_title('Trayectoria Extensivo-Intensivo', fontweight='bold', pad=15)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(ruta_fig('09_vectores_diversificacion.png'), facecolor='white')
plt.close()

# --- 10. Evolucion Top 8 productos (escala log) ---
fig, ax = plt.subplots(figsize=(12, 7))
fig.patch.set_facecolor('white')
col_etiqueta = 'nombre_producto' if 'nombre_producto' in df.columns else 'producto'
top_8_prods = df.groupby(col_etiqueta)['exportaciones'].sum().nlargest(8).index
df_top = df[df[col_etiqueta].isin(top_8_prods)]
pivot_top = df_top.pivot_table(index='anio', columns=col_etiqueta, values='exportaciones',
                               aggfunc='sum').fillna(0).replace(0, 1)
marcadores = ['o', 's', '^', 'D', 'v', 'p', '*', 'X']
for i, col in enumerate(pivot_top.columns):
    nombre_limpio = str(col)[:35] + '...' if len(str(col)) > 35 else str(col)
    ax.plot(pivot_top.index, pivot_top[col], marker=marcadores[i % len(marcadores)],
            linewidth=2.5, label=nombre_limpio, color=colores_top[i % len(colores_top)],
            alpha=0.9, markersize=7)
ax.set_yscale('log')
agregar_sombra_frontera(ax, df)
ax.set_xlabel('Año', fontweight='bold')
ax.set_ylabel(f'{NOMBRE_FLUJO_CORTO} (USD, escala log)', fontweight='bold')
ax.set_title(f'Evolución Histórica: Top 8 Productos - {NOMBRE_FLUJO_CORTO}', fontweight='bold', pad=15)
ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=9, borderaxespad=0.)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(ruta_fig('10_evolucion_top_productos.png'), facecolor='white')
plt.close()

# --- 11. Violin del margen intensivo segun frontera ---
fig, ax = plt.subplots(figsize=(9, 6))
fig.patch.set_facecolor('white')
df_violin = df[df['dummy_exporta'] == 1].copy()
df_violin['Frontera'] = df_violin['border'].map({0: 'Abierta', 1: 'Cerrada', 2: 'Parcial'})
orden_frontera = [e for e in ['Abierta', 'Parcial', 'Cerrada'] if e in df_violin['Frontera'].unique()]
paleta_violin = {'Abierta': COLORES['secondary'], 'Cerrada': COLORES['alert'], 'Parcial': COLORES['accent']}
sns.violinplot(x='Frontera', y='ln_exportaciones', data=df_violin, order=orden_frontera,
               palette=[paleta_violin[e] for e in orden_frontera], ax=ax, inner="quartile")
ax.set_title('Distribución del Margen Intensivo segun Frontera', fontweight='bold', pad=15)
ax.set_ylabel('log(flujo)', fontweight='bold'); ax.set_xlabel('Estado de la frontera', fontweight='bold')
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(ruta_fig('11_violin_frontera.png'), facecolor='white')
plt.close()

# --- 12. Ciclo de vida del producto ---
fig, ax = plt.subplots(figsize=(10, 7))
fig.patch.set_facecolor('white')
df_activos = df[df['dummy_exporta'] == 1]
vida = df_activos.groupby('producto').agg(anios_activos=('anio', 'count'),
                                          volumen_promedio=('exportaciones', 'mean'))
vida['volumen_promedio'] = vida['volumen_promedio'] / 1e6
ax.scatter(vida['anios_activos'], vida['volumen_promedio'], color=COLORES['primary'],
           s=80, alpha=0.8, edgecolor='white')
ax.axvline(vida['anios_activos'].median(), color=COLORES['alert'], linestyle='--', alpha=0.7,
           label=f"Mediana permanencia: {vida['anios_activos'].median():.0f} anios")
ax.axhline(vida['volumen_promedio'].median(), color=COLORES['secondary'], linestyle='--', alpha=0.7,
           label=f"Mediana volumen: {vida['volumen_promedio'].median():.2f} M USD")
ax.legend()
ax.set_xlabel('Años con flujo positivo (permanencia)', fontweight='bold')
ax.set_ylabel('Volumen promedio (millones USD)', fontweight='bold')
ax.set_title('Ciclo de Vida y Matriz de Productos', fontweight='bold', pad=15)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(ruta_fig('12_ciclo_vida_productos.png'), facecolor='white')
plt.close()

# --- 13. KDE del IMR ---
fig, ax = plt.subplots(figsize=(9, 6))
fig.patch.set_facecolor('white')
sns.kdeplot(df['IMR'], fill=True, color=COLORES['accent'], ax=ax, alpha=0.6, linewidth=2)
ax.axvline(df['IMR'].mean(), color=COLORES['primary'], linestyle='--', label=f"Media: {df['IMR'].mean():.3f}")
ax.set_title('Densidad de Probabilidad del Inverse Mills Ratio (IMR)', fontweight='bold', pad=15)
ax.set_xlabel('Valor del IMR', fontweight='bold'); ax.set_ylabel('Densidad', fontweight='bold')
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(ruta_fig('13_densidad_imr.png'), facecolor='white')
plt.close()

print("Graficas 1-13 exportadas en PNG (300 dpi).")

# =============================================================================
# 8. EXPORTACION DE RESULTADOS A EXCEL
# =============================================================================
print("\n" + "=" * 80)
print("EXPORTANDO RESULTADOS A EXCEL")
print("=" * 80)

ruta_excel_out = os.path.join(DIRECTORIO_SALIDA, f'resultados_wooldridge_{FLUJO_LOWER.split()[0]}.xlsx')
with pd.ExcelWriter(ruta_excel_out, engine='openpyxl') as writer:
    desc.round(4).to_excel(writer, sheet_name='Descriptivas')
    res_probit.round(6).to_excel(writer, sheet_name='Probit_Etapa1', index=False)

    def tabla_modelo(m, nombre):
        t = pd.DataFrame({'Variable': m.params.index, 'Coef': m.params.values,
                          'SE': m.std_errors.values, 't': m.tstats.values,
                          'p_valor': m.pvalues.values})
        t['Sig'] = ['***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.1 else '' for p in t['p_valor']]
        t['Modelo'] = nombre
        t['R2'] = m.rsquared
        t['N'] = m.nobs
        return t.round(6)

    pd.concat([tabla_modelo(model_pooled, 'Pooled OLS'),
               tabla_modelo(model_re, 'Efectos Aleatorios'),
               tabla_modelo(model_fe_std, 'FE Estandar (sin IMR)'),
               tabla_modelo(model_wooldridge, 'Wooldridge (FE+IMR)')]).to_excel(
        writer, sheet_name='Panel_Etapa2', index=False)

    diag = pd.DataFrame({
        'Indicador': ['N observaciones panel', 'N productos', 'N anios',
                      'R2 Pooled', 'R2 RE', 'R2 FE estandar', 'R2 Wooldridge',
                      'Pseudo R2 Probit', 'Hausman chi2', 'Hausman p-valor',
                      'Decision Hausman', 'Coef IMR (Wooldridge)', 'p-valor IMR',
                      'Sesgo de seleccion'],
        'Valor': [len(df_panel), df_panel.reset_index()['producto'].nunique(),
                  df_panel.reset_index()['anio'].nunique(),
                  round(model_pooled.rsquared, 4), round(model_re.rsquared, 4),
                  round(model_fe_std.rsquared, 4), round(model_wooldridge.rsquared, 4),
                  round(probit_model.prsquared, 4),
                  round(h_stat, 4) if not np.isnan(h_stat) else 'N/A',
                  round(h_pval, 4) if not np.isnan(h_pval) else 'N/A',
                  'Efectos fijos preferidos' if h_pval < 0.05 else 'RE no rechazados',
                  round(model_wooldridge.params.get('IMR', np.nan), 4),
                  round(model_wooldridge.pvalues.get('IMR', np.nan), 4),
                  ('Significativo' if model_wooldridge.pvalues.get('IMR', 1) < 0.1 else 'No significativo')]})
    diag.to_excel(writer, sheet_name='Diagnostico', index=False)
    df.to_excel(writer, sheet_name='Datos_con_IMR', index=False)

print(f"Excel de resultados: {ruta_excel_out}")

# =============================================================================
# 9. RESUMEN FINAL
# =============================================================================
print("\n" + "=" * 80)
print(f"RESUMEN FINAL - {FLUJO.upper()}")
print("=" * 80)
print(f"Observaciones panel: {len(df_panel)} | Productos: {df_panel.reset_index()['producto'].nunique()} | Anios: {df_panel.reset_index()['anio'].nunique()}")
print(f"R2 Wooldridge: {model_wooldridge.rsquared:.4f}")
print("\nCoeficientes Wooldridge (FE + IMR):")
for var in model_wooldridge.params.index:
    c, p = model_wooldridge.params[var], model_wooldridge.pvalues[var]
    s = '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.1 else ''
    print(f"  {var:15s}: {c:9.4f} {s}  (p = {p:.4f})")
print(f"\nHausman: chi2 = {h_stat:.4f} (p = {h_pval:.4f}) -> {'FE' if h_pval < 0.05 else 'RE'}")
print(f"Anios con frontera cerrada: {sorted(df[df['border'] == 1]['anio'].unique())}")
print(f"Anios con apertura parcial: {sorted(df[df['border'] == 2]['anio'].unique())}")
print(f"Salidas en: {DIRECTORIO_SALIDA}")
print("=" * 80)
