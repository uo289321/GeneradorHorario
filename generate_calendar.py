
# --- Download HTML ---
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

url = "https://gobierno.ingenieriainformatica.uniovi.es/grado/plan/plan.php?y=25-26&t=s1&DS.T.2=DS.T.2&DS.S.3=DS.S.3&DS.L.3=DS.L.3&DS.TG.3=DS.TG.3&CVVS.T.1=CVVS.T.1&CVVS.S.2=CVVS.S.2&CVVS.L.1=CVVS.L.1&CVVS.TG.1=CVVS.TG.1&IR.T.1=IR.T.1&IR.S.2=IR.S.2&IR.L.1=IR.L.1&IR.TG.1=IR.TG.1&SI.T.2=SI.T.2&SI.S.2=SI.S.2&SI.L.1=SI.L.1&SI.TG.1=SI.TG.1&SR.T.1=SR.T.1&SR.S.1=SR.S.1&SR.L.2=SR.L.2&SR.TG.2=SR.TG.2&vista=web"
response = requests.get(url)
if response.status_code == 200:
    html = response.text
    print("Downloaded successfully from web.")
else:
    raise Exception(f"Failed to download. Status code: {response.status_code}")




soup = BeautifulSoup(html, "html.parser")

# Extract all class schedules
cal_events = []
for h2 in soup.find_all("h2"):
    subject = h2.get_text(strip=True)
    ol = h2.find_next_sibling("ol")
    if not ol:
        continue
    for li in ol.find_all("li"):
        text = li.get_text(" ", strip=True)
        # Example: 'Jueves, 11/09/2025, 13.30-15.30, A-2-02, (2)'
        m = re.match(r"(\w+), (\d{2}/\d{2}/\d{4}), (\d{1,2}\.\d{2})-(\d{1,2}\.\d{2}), ([^,]+),", text)
        if m:
            day, date, start, end, room = m.groups()
            start_dt = datetime.strptime(f"{date} {start}", "%d/%m/%Y %H.%M")
            end_dt = datetime.strptime(f"{date} {end}", "%d/%m/%Y %H.%M")
            cal_events.append({
                "subject": subject,
                "room": room.strip(),
                "start": start_dt,
                "end": end_dt
            })

# Find the range of dates
if cal_events:
    min_date = min(e["start"] for e in cal_events)
    max_date = max(e["end"] for e in cal_events)
else:
    min_date = max_date = datetime.today()

def date_range(start, end):
    days = (end - start).days + 1
    for i in range(days):
        yield start + timedelta(days=i)

def events_on_day(day):
    return [e for e in cal_events if e["start"].date() == day.date()]

# Build week-view calendar: columns are days, rows are time slots
import calendar
import locale
locale.setlocale(locale.LC_TIME, "es_ES.UTF-8") if hasattr(locale, 'setlocale') else None

# Map Spanish day names to weekday index
day_map = {
    'Lunes': 0, 'Martes': 1, 'Miércoles': 2, 'Miercoles': 2, 'Jueves': 3, 'Viernes': 4, 'Sábado': 5, 'Sabado': 5, 'Domingo': 6
}
days_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']


# Group events by week (Monday as first day), using string keys to avoid duplicates
from collections import defaultdict
def get_week_start(dt):
    return dt - timedelta(days=dt.weekday())

weeks = defaultdict(list)
week_start_strs = {}
for e in cal_events:
    week_start = get_week_start(e['start'])
    week_str = week_start.strftime('%d/%m/%Y')
    weeks[week_str].append(e)
    week_start_strs[week_str] = week_start

all_week_strs = sorted(week_start_strs.keys(), key=lambda s: datetime.strptime(s, '%d/%m/%Y'))

# Find global min/max time for all events (for consistent slot range)
min_time = 24 * 60
max_time = 0
for e in cal_events:
    min_time = min(min_time, e['start'].hour * 60 + e['start'].minute)
    end_minutes = e['end'].hour * 60 + e['end'].minute
    if e['end'].minute % 30 != 0:
        end_minutes += 30 - (e['end'].minute % 30)
    max_time = max(max_time, end_minutes)
# Force calendar to always go up to 21:00 (9 PM)
min_time = min(min_time, 8 * 60)  # 08:00 earliest
max_time = max(max_time, 21 * 60) # 21:00 latest
num_slots = (max_time - min_time) // 30

# HTML output: one table per week
html_out = ["<html><head><title>Calendario Semanal de Clases</title><link rel='stylesheet' href='calendar.css'></head><body>"]
html_out.append("<h1>Calendario Semanal de Clases</h1>")
for week_str in all_week_strs:
    html_out.append(f"<h2>Semana del {week_str}</h2>")
    html_out.append("<table>")
    # Calculate the date for each day in this week
    week_start_dt = datetime.strptime(week_str, '%d/%m/%Y')
    day_dates = [(week_start_dt + timedelta(days=i)).strftime('%d/%m/%Y') for i in range(5)]
    # Build week grid
    week_events = weeks[week_str]
    # Determine which days have no classes at all
    days_with_classes = set(e['start'].weekday() for e in week_events)
    no_class_days = [d for d in range(5) if d not in days_with_classes]
    html_out.append("<tr><th>Hora</th>" + ''.join(f"<th>{d}<br/>{day_dates[i]}</th>" for i, d in enumerate(days_order)) + "</tr>")
    calendar_grid = {}
    rowspans = {}
    for e in week_events:
        wd = e['start'].weekday()
        start_min = e['start'].hour * 60 + e['start'].minute
        end_min = e['end'].hour * 60 + e['end'].minute
        if end_min % 30 != 0:
            end_min += 30 - (end_min % 30)
        start_slot = (start_min - min_time) // 30
        end_slot = (end_min - min_time) // 30
        span = end_slot - start_slot
        calendar_grid[(start_slot, wd)] = e
        rowspans[(start_slot, wd)] = span
        for s in range(start_slot + 1, end_slot):
            calendar_grid[(s, wd)] = None
    for s in range(num_slots):
        slot_start = min_time + s * 30
        slot_end = slot_start + 30
        h1, m1 = divmod(slot_start, 60)
        h2, m2 = divmod(slot_end, 60)
        row = [f"<td>{h1:02d}:{m1:02d} - {h2:02d}:{m2:02d}</td>"]
        for d in range(5):
            # If a previous rowspan covers this cell, skip
            skip = False
            for prev_s in range(s):
                prev_rowspan = rowspans.get((prev_s, d), 1)
                if prev_rowspan > (s - prev_s) and calendar_grid.get((prev_s, d)) is not None:
                    skip = True
                    break
            if skip:
                continue
            cell = calendar_grid.get((s, d), 'empty')
            if cell == 'empty':
                row.append("<td></td>")
            elif cell is None:
                continue
            else:
                span = rowspans.get((s, d), 1)
                subj_full = cell['subject']
                subj_clean = subj_full.replace('Planificación de la asignatura', '').strip()
                code_match = re.match(r"([A-Z]+)\.([A-Z]+)\.([0-9]+)", subj_clean)
                if code_match:
                    code_group = f"{code_match.group(1)} {code_match.group(2)}.{code_match.group(3)}"
                else:
                    code_group = subj_clean
                room = cell['room']
                row.append(f"<td class='event' rowspan='{span}'>{code_group}<br/>({room})</td>")
        html_out.append("<tr>" + ''.join(row) + "</tr>")
    html_out.append("</table>")
html_out.append("</body></html>")

with open("index.html", "w", encoding="utf-8") as f:
    f.write("\n".join(html_out))

print("index.html generated.")
