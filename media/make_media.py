import sqlite3, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.backends.backend_pdf import PdfPages

NAVY, BLUE, GREEN, RED, GREY, LIGHT = '#0f2540', '#2563eb', '#2ca02c', '#c44e52', '#6c757d', '#f4f6f8'
plt.rcParams['font.family'] = 'DejaVu Sans'

conn = sqlite3.connect('healthcare_bi.db')
county = pd.read_sql('select * from Dim_Country_Details', conn)
hosp = pd.read_sql('select * from Dim_Hospital_Details', conn)
survey = pd.read_sql('select * from Dim_Survey_Details', conn)
fact = pd.read_sql('select * from Fact_Patient_Survey', conn)

h = hosp.drop(columns=['City']).merge(county, on='Country_Id').rename(columns={'Country_Name': 'County'})
base = fact.groupby('Hospital_Id').agg(Surveys=('No_Completed_Surveys', 'max'),
        Resp=('Survey_Response_Rate_Percent', 'max')).reset_index().merge(h, on='Hospital_Id')
sid = survey.loc[survey.Survey_Question == 'Summary star rating', 'Survey_Id'].iloc[0]
base = base.merge(fact.loc[fact.Survey_Id == sid, ['Hospital_Id', 'Patient_Survey_Star_Rating']], on='Hospital_Id', how='left')
lin = survey[survey.Survey_Question.str.contains('linear mean score')].copy()
lin['Category'] = lin.Survey_Question.str.replace(' - linear mean score', '', regex=False)
cat = fact[fact.Survey_Id.isin(lin.Survey_Id)].merge(lin, on='Survey_Id').groupby('Category').Linear_Mean_Value.mean().sort_values()
cd = base.dropna(subset=['Resp', 'Patient_Survey_Star_Rating'])
r = cd.Resp.corr(cd.Patient_Survey_Star_Rating)
top_c = base.groupby(['County', 'State']).Resp.mean().sort_values(ascending=False).head(3)
top_h = base.dropna(subset=['Resp']).sort_values('Resp', ascending=False).head(10)

def style(ax):
    for s in ['top', 'right']: ax.spines[s].set_visible(False)
    ax.tick_params(colors=NAVY)

def frame(w, h_, title, sub=None, footer=True):
    fig = plt.figure(figsize=(w, h_), facecolor='white')
    fig.text(0.05, 0.93, title, fontsize=22 if w > 11 else 26, fontweight='bold', color=NAVY, va='top', wrap=True)
    if sub: fig.text(0.05, 0.855 if w > 11 else 0.875, sub, fontsize=12 if w > 11 else 14, color=GREY, va='top')
    if footer: fig.text(0.05, 0.02, 'Source: CMS HCAHPS patient survey data, 700 hospitals, 7 states, Jul 2017 - Jun 2018',
                        fontsize=8.5, color=GREY)
    return fig

def f_medicines(w, h_):
    fig = frame(w, h_, 'Medication communication is the weakest link', 'Avg HCAHPS linear mean score by category (axis starts at 0); red = lowest three')
    ax = fig.add_axes([0.27, 0.1, 0.68, 0.66] if w > 11 else [0.33, 0.08, 0.62, 0.72]); style(ax)
    ax.barh(cat.index, cat.values, color=[RED if v < 83 else BLUE for v in cat.values])
    for i, v in enumerate(cat.values): ax.text(v + 0.5, i, f'{v:.1f}', va='center', fontsize=10, color=NAVY)
    ax.set_xlim(0, 100); ax.set_xlabel('Avg linear mean score (0-100 scale)'); return fig

def f_scatter(w, h_):
    fig = frame(w, h_, 'More responses, higher ratings', f'Response rate vs overall star rating per hospital (r = {r:.2f}); correlation, not causation')
    ax = fig.add_axes([0.09, 0.12, 0.86, 0.66] if w > 11 else [0.12, 0.08, 0.83, 0.72]); style(ax)
    ax.scatter(cd.Resp, cd.Patient_Survey_Star_Rating + (pd.Series(range(len(cd)), index=cd.index) % 7 - 3) * 0.03, alpha=0.35, color=BLUE, s=22)
    ax.set_xlabel('Survey response rate (%)'); ax.set_ylabel('Overall star rating'); return fig

def f_top(w, h_):
    fig = frame(w, h_, 'Top 10 hospitals by survey response rate', 'Specialty and surgical hospitals lead on patient engagement')
    ax = fig.add_axes([0.40, 0.1, 0.55, 0.66] if w > 11 else [0.44, 0.08, 0.51, 0.72]); style(ax)
    ax.barh(top_h.Hospital_Name.str.title().map(lambda n: (n.replace('Hospital', 'Hosp.') if len(n) > 31 else n).replace(' Llc', ' LLC').replace(' Of ', ' of ').replace(' And ', ' and ').replace(', The', ''))[::-1], top_h.Resp[::-1], color=GREEN)
    for i, v in enumerate(top_h.Resp[::-1]): ax.text(v + 0.5, i, f'{v:.0f}%', va='center', fontsize=10, color=NAVY)
    ax.set_xlim(0, 68); return fig

def f_schema(w, h_):
    fig = frame(w, h_, 'Star schema design', 'One fact table, four dimensions, 34,999 records')
    ax = fig.add_axes([0, 0, 1, 0.8]); ax.axis('off'); ax.set_xlim(0, 12); ax.set_ylim(0, 8 if w > 11 else 12)
    def box(x, y, bw, bh, title, rows, color):
        ax.add_patch(FancyBboxPatch((x, y), bw, bh, boxstyle='round,pad=0.05', fc='white', ec=color, lw=2))
        ax.add_patch(FancyBboxPatch((x, y + bh - 0.7), bw, 0.7, boxstyle='round,pad=0.05', fc=color, ec=color))
        ax.text(x + bw / 2, y + bh - 0.35, title, ha='center', va='center', color='white', fontsize=10.5, fontweight='bold')
        for i, t in enumerate(rows): ax.text(x + 0.2, y + bh - 1.15 - i * 0.5, t, fontsize=8.5, color=NAVY, va='center')
    wide = w > 11
    yb = 4.4 if wide else 7.2
    box(4.4, 0.6 if wide else 2.4, 3.2, 6.6 if wide else 7.0, 'Fact_Patient_Survey', ['Country_Id (FK)', 'Hospital_Id (FK)', 'Measure_Id (FK)', 'Survey_Id (FK)', 'No_Completed_Surveys', 'Response_Rate_Percent', 'Linear_Mean_Value', 'Answer_Percent', 'Star_Rating', '+ footnote columns'], BLUE)
    box(0.4, 4.6 if wide else 8.0, 3.2, 2.6, 'Dim_Location (County grain)', ['Country_Id (PK)', 'County / State', 'City / Zip'], NAVY)
    box(0.4, 0.8 if wide else 2.4, 3.2, 2.4, 'Dim_Hospital', ['Hospital_Id (PK)', 'Hospital_Name', 'City / Location'], NAVY)
    box(8.4, 4.6 if wide else 8.0, 3.2, 2.4, 'Dim_Measure', ['Measure_Id (PK)', 'Measure_Code', 'Start / End date'], NAVY)
    box(8.4, 0.8 if wide else 2.4, 3.2, 2.4, 'Dim_Survey', ['Survey_Id (PK)', 'Question', 'Answer'], NAVY)
    return fig

def f_cover(w, h_):
    fig = plt.figure(figsize=(w, h_), facecolor=NAVY)
    fig.text(0.06, 0.82, 'HEALTHCARE ANALYTICS  |  BI PROJECT', fontsize=12, color='#9db4d3', fontweight='bold')
    fig.text(0.06, 0.70, 'What do patient surveys from\n700 hospitals tell us?', fontsize=34 if w > 11 else 36, color='white', fontweight='bold', va='top', linespacing=1.15)
    k = [('700', 'hospitals'), ('537K', 'completed surveys'), ('23.8%', 'avg response rate'), ('2.96', 'avg star rating')]
    for i, (v, l) in enumerate(k):
        x = 0.06 + i * 0.23
        fig.text(x, 0.33, v, fontsize=30, color='#60a5fa', fontweight='bold'); fig.text(x, 0.27, l, fontsize=11, color='#cbd5e1')
    fig.text(0.06, 0.1, 'Star schema  -  Python / SQL  -  Interactive dashboard', fontsize=12, color='#9db4d3')
    return fig

def f_text(w, h_, title, body):
    fig = frame(w, h_, title)
    fig.text(0.05, 0.75, body, fontsize=16, color=NAVY, va='top', linespacing=1.6)
    return fig

W, H = 12, 6.27   # 1200x627 at dpi 100
imgs = {'01_cover': f_cover, '02_star_schema': f_schema, '03_medication_communication': f_medicines,
        '04_response_vs_rating': f_scatter, '05_top_hospitals': f_top}
for n, f in imgs.items():
    f(W, H).savefig(f'out/{n}.png', dpi=100, facecolor='auto'); plt.close('all')

# Carousel PDF, 1080x1350 portrait pages
CW, CH = 10.8, 13.5
with PdfPages('out/healthcare_survey_carousel.pdf') as pdf:
    pages = [f_cover(CW, CH), f_schema(CW, CH), f_medicines(CW, CH), f_scatter(CW, CH), f_top(CW, CH),
        f_text(CW, CH, 'Takeaways', '1. Fix medication communication first.\n    It scores lowest nationally (78.6)\n    vs 90+ for nurse and doctor communication.\n\n2. Watch response rate as an early signal.\n    It correlates with overall star rating\n    (r = 0.56), though not proof of cause.\n\n3. Handle thin data deliberately.\n    81 small hospitals have suppressed\n    results; ignoring them skews comparisons.')]
    for p in pages: pdf.savefig(p, facecolor='auto'); plt.close(p)
print('done')
