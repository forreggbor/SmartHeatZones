# SmartHeatZones v1.4.4 - Javítások Telepítése

## 📋 VÁLTOZÁSOK ÖSSZEFOGLALÓJA

### 🔴 KRITIKUS JAVÍTÁSOK

| # | Probléma | Javítás | Fájl |
|---|----------|---------|------|
| 1 | Config vs Options inkonzisztencia | Fallback logika hozzáadva | `climate.py` sor 68 |
| 2 | Kezdeti HVAC mode OFF | HEAT-re változtatva | `climate.py` sor 127 |
| 3 | Auto HVAC váltás hiányzik | Implementálva | `climate.py` sor 286-299 |
| 4 | Schedule nem kerül beállításra | Inicializálás hozzáadva | `climate.py` sor 138, 220-251 |
| 5 | State nem restaurálódik | RestoreEntity mixin | `climate.py` sor 100, 146-157 |
| 6 | Napszak fordítások hiányoznak | 16 új kulcs | `translations/hu.json` |
| 7 | Gyenge hibaellenőrzés | Javítva | `climate.py` sor 171-184 |

### ✅ MŰKÖDÉSI MÓDOSÍTÁSOK

- **Kezdeti értékelés**: Induláskor azonnal ellenőrzi a fűtési igényt
- **Schedule auto váltás**: 15 percenként ellenőrzi a napszakot
- **Részletesebb logolás**: Minden lépés naplózva DEBUG szinten
- **Jobb hibaüzenetek**: Részletes magyarázat minden eseménynél

---

## 🚀 TELEPÍTÉS LÉPÉSEI

### 1. BIZTONSÁGI MENTÉS

```bash
# SSH-val csatlakozz a HA szerverhez
ssh root@<ha_ip>

# Mentsd el a jelenlegi verziót
cd /config/custom_components
tar -czf smartheatzones_backup_$(date +%Y%m%d_%H%M%S).tar.gz smartheatzones/

# Ellenőrzés
ls -lh smartheatzones_backup*.tar.gz
```

### 2. FÁJLOK CSERÉJE

#### PyCharm SFTP-n keresztül:

```
1. Nyisd meg PyCharm-ot
2. Tools → Deployment → Browse Remote Host
3. Navigálj: /config/custom_components/smartheatzones/
4. Cseréld le a következő fájlokat:

   KÖTELEZŐ:
   ✓ climate.py          (JAVÍTOTT verzió)
   ✓ translations/hu.json (KIEGÉSZÍTETT verzió)
   
   OPCIONÁLIS:
   - translations/en.json (ha angolul is szeretnéd)
```

#### Vagy manuálisan:

```bash
# A lokális gépeden (PyCharm projektben):
# 1. Másold ki a javított climate.py tartalmát
# 2. Másold ki a javított hu.json tartalmát

# SSH-n a HA szerveren:
cd /config/custom_components/smartheatzones/

# Szerkeszd a fájlokat
nano climate.py
# (CTRL+K törli a tartalmat, majd illeszd be az újat)
# CTRL+X, Y, ENTER

cd translations/
nano hu.json
# (Ugyanúgy)
```

### 3. HOME ASSISTANT ÚJRAINDÍTÁS

```bash
# HA újraindítás
ha core restart

# Vagy a UI-ból:
# Fejlesztői eszközök → YAML → Újraindítás
```

**FONTOS:** NE csak az integráció újratöltése, hanem **teljes HA restart** kell!

---

## 🧪 TESZTELÉSI FOLYAMAT

### ELŐKÉSZÍTÉS

#### 1. Debug Logolás Bekapcsolása

`configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.smartheatzones: debug
    custom_components.smartheatzones.climate: debug
    custom_components.smartheatzones.boiler_manager: debug
```

Mentés után:
- Fejlesztői eszközök → YAML → Yaml konfigurációk újratöltése

#### 2. Böngésző Cache Törlés

- CTRL+SHIFT+DEL (Chrome/Edge)
- Válaszd: "Cached images and files"
- Frissítsd az oldalt: CTRL+F5

---

### TESZTEK SORRENDJE

#### ✅ TESZT #1: Létező Zóna Újraindítás Után

**Cél:** Ellenőrizni, hogy a javítások működnek-e.

1. **Ellenőrzés a UI-ban:**
   - Beállítások → Eszközök és szolgáltatások
   - Keresd meg: SmartHeatZones
   - Látod a zónáid? ✓

2. **Climate Entitás Ellenőrzés:**
   - Áttekintés → Keress rá: `climate.`
   - Látható a zónád termosztátja? ✓
   - Jelenik meg az aktuális hőmérséklet? ✓

3. **Log Ellenőrzés:**
   ```
   Beállítások → Rendszer → Naplók
   Szűrő: "smartheatzones"
   
   Keresendő sorok:
   ✓ "[SmartHeatZones] Creating climate entity: Földszint | Sensor=..."
   ✓ "[SmartHeatZones] [Földszint] Initialized | ... | Initial HVAC=heat"
   ✓ "[SmartHeatZones] [Földszint] Initial temperature: 19.5°C"
   
   HIBÁS ha látod:
   ✗ "Failed to ..."
   ✗ "ERROR"
   ```

---

#### ✅ TESZT #2: Target Hőmérséklet Állítás

**Cél:** Relé kapcsolás működik-e.

1. **Thermostat Kártyán:**
   - Nyisd meg a zóna termosztát kártyáját
   - Jelenlegi: 19.5°C
   - Target: Állítsd 23.0°C-ra

2. **Várt viselkedés:**
   - Azonnal megjelenik: "Fűtés" állapot
   - Kazán főkapcsoló: BE kapcsol
   - Zóna relék: BE kapcsolnak

3. **Log Ellenőrzés (KRITIKUS!):**
   ```
   ✓ "[SmartHeatZones] [Földszint] Target temperature: 21.0 → 23.0°C"
   ✓ "[SmartHeatZones] [Földszint] Auto-switched to HEAT (target 23.0 > current 19.5)"
   ✓ "[SmartHeatZones] [Földszint] Evaluate: current=19.5 target=23.0 diff=3.50 hysteresis=0.3"
   ✓ "[SmartHeatZones] [Földszint] Heating ON (Needs heat (diff=3.50°C))"
   ✓ "[SmartHeatZones] [Földszint] switch.turn_on → switch.zona_rele_1"
   ✓ "[SmartHeatZones] Zone 'Földszint' requested boiler ON (active_zones=1)"
   ✓ "[SmartHeatZones] Boiler relay switch.kazan_fo → TURN_ON"
   ```

4. **Fizikai Ellenőrzés:**
   - Menj ki a kazánhoz/relékhez
   - Hallatszik a relé kattanása? ✓
   - LED világít a reléken? ✓
   - Kazán elindul? ✓

**❌ HA NEM MŰKÖDIK:**
```
Probléma: Semmi nem történik
→ Ellenőrizd a logot: Van "Target temperature set" sor?
  - NINCS: Böngésző cache probléma, törölj mindent
  - VAN: Továbbolvass...

Probléma: "Auto-switched" nem jelenik meg
→ Helytelen fájl feltöltés
  - Győződj meg, hogy a JAVÍTOTT climate.py-t töltötted fel
  - Ellenőrizd: nano /config/custom_components/smartheatzones/climate.py
  - Keresd: "FIX #7: Auto HVAC mode váltás" sort

Probléma: "switch.turn_on" nincs a logban
→ Relék/Kazán entity_id probléma
  - Nyisd meg: Beállítások → SmartHeatZones → Fogaskerék
  - Ellenőrizd: Van-e kitöltve minden mező?
  - Relék: [switch.zona_rele_1, switch.zona_rele_2] formátumban?
  - Kazán: switch.kazan_fo pontosan így?
```

---

#### ✅ TESZT #3: HVAC Mode Manuális Váltás

**Cél:** OFF/HEAT kapcsoló működése.

1. **Thermostat kártyán:**
   - Kattints az "OFF" gombra
   - Várj 2 másodpercet
   - Kattints a "HEAT" gombra

2. **Várt viselkedés:**
   ```
   OFF → Relék KI, Kazán KI (ha nincs más aktív zóna)
   HEAT → Újraértékelés, ha kell fűtés → Relék BE
   ```

3. **Log:**
   ```
   ✓ "[SmartHeatZones] [Földszint] HVAC mode: heat → off"
   ✓ "[SmartHeatZones] [Földszint] Heating OFF (HVAC mode is OFF)"
   ✓ "[SmartHeatZones] [Földszint] switch.turn_off → switch.zona_rele_1"
   ✓ "[SmartHeatZones] Zone 'Földszint' released boiler (active_zones=0)"
   ✓ "[SmartHeatZones] Boiler relay switch.kazan_fo → TURN_OFF"
   ```

---

#### ✅ TESZT #4: Hiszterézis Működés

**Cél:** Stabil kapcsolás, nincs "villogás".

**Beállítások:**
- Hiszterézis: 0.3°C
- Target: 22.0°C
- Current: 21.7°C (közel a célhoz)

**Várható viselkedés:**
```
21.7 < 22.0 - 0.3  → 21.7 < 21.7  → HAMIS → NEM kapcsol BE
21.7 > 22.0 + 0.3  → 21.7 > 22.3  → HAMIS → NEM kapcsol KI

Tehát: Hiszterézis sávban -> NINCS kapcsolás
```

**Tesztelés:**
1. Állítsd a target-et 22.0°C-ra
2. Várj, amíg a szoba felmelegszik 21.7°C-ra
3. Figyeld a logot 5 percig

**Helyes log:**
```
✓ "[SmartHeatZones] [Földszint] Evaluate: current=21.70 target=22.00 diff=0.30 hysteresis=0.30"
✓ (Nincs "Heating ON/OFF" sor -> stabil állapot)
```

**Hibás log:**
```
✗ "[SmartHeatZones] [Földszint] Heating ON"
✗ "[SmartHeatZones] [Földszint] Heating OFF"
✗ (Ismétlődik 10 másodpercenként -> hiszterézis nem működik)
```

---

#### ✅ TESZT #5: Ajtó/Ablak Lockout

**Cél:** Nyitás esetén fűtés szünetel.

**Előfeltétel:** Van beállítva ajtó/ablak szenzor az Options-ban.

1. **Zárt ajtóval:**
   - Fűtés megy (current < target)
   - Relék BE, Kazán BE

2. **Nyisd ki az ajtót:**
   - Binary sensor: ON állapot

3. **Várt viselkedés:**
   ```
   ✓ Relék azonnal KI kapcsolnak
   ✓ Kazán KI (ha nincs más aktív zóna)
   ✓ Termosztát mutat: "Fűtés" de hvac_action: "idle"
   ```

4. **Log:**
   ```
   ✓ "[SmartHeatZones] [Földszint] Door/window open – heating paused"
   ✓ "[SmartHeatZones] [Földszint] Heating OFF (Door/window open)"
   ```

5. **Zárd be az ajtót:**
   ```
   ✓ "[SmartHeatZones] [Földszint] Door/window closed – re-evaluating heating"
   ✓ "[SmartHeatZones] [Földszint] Heating ON (Needs heat ...)"
   ```

---

#### ✅ TESZT #6: Napszak Váltás (Options-ban)

**Cél:** Fordítások működnek, napszak beállítható.

1. **Options megnyitása:**
   - Beállítások → Eszközök és szolgáltatások
   - SmartHeatZones → Zóna → Fogaskerék ikon

2. **Ellenőrizd a fordításokat:**
   ```
   ✓ "1. napszak neve" (MAGYAR, nem "label_1")
   ✓ "1. napszak kezdete"
   ✓ "1. napszak vége"
   ✓ "1. napszak célhőmérséklet"
   
   És ugyanez 2., 3., 4. napszakra is
   ```

3. **Állítsd be a napszakokat:**
   ```yaml
   1. napszak:
     Név: "Éjszaka"
     Kezdet: 22:00
     Vég: 06:00
     Hőmérséklet: 18.0
   
   2. napszak:
     Név: "Reggel"
     Kezdet: 06:00
     Vég: 08:00
     Hőmérséklet: 22.0
   
   3. napszak:
     Név: "Nappal"
     Kezdet: 08:00
     Vég: 16:00
     Hőmérséklet: 19.0
   
   4. napszak:
     Név: "Este"
     Kezdet: 16:00
     Vég: 22:00
     Hőmérséklet: 21.5
   ```

4. **Mentés után log:**
   ```
   ✓ "[SmartHeatZones] Options updated for Földszint: ..."
   ✓ "[SmartHeatZones] [Földszint] Schedule applied: Reggel (22.0°C)"
   ```

---

#### ✅ TESZT #7: Schedule Auto Váltás

**Cél:** 15 percenként ellenőrzi, jó napszakban van-e.

**Tesztelési módszer:**
1. Állítsd az időt 07:55-re a HA szerveren (opcionális, vagy várj)
2. Várj 15 percet (08:10-ig)
3. Ellenőrizd a logot

**Várt log (ha átléptél 08:00-t):**
```
✓ "[SmartHeatZones] [Földszint] Schedule changed target: 22.0 → 19.0°C"
✓ "[SmartHeatZones] [Földszint] Evaluate: current=... target=19.0 ..."
```

**Gyorsított teszt (fejlesztői):**
```python
# climate.py 163. sor módosítás:
timedelta(minutes=15)  # Eredeti

# Teszthez:
timedelta(minutes=1)   # 1 percenként ellenőriz

# NE FELEDD VISSZAÁLLÍTANI!
```

---

#### ✅ TESZT #8: Többzónás Működés

**Cél:** Kazán koordináció helyes.

**Létrehozz 2 zónát:**
- Zóna 1: Földszint (sensor.temp_f, switch.rele_f)
- Zóna 2: Emelet (sensor.temp_e, switch.rele_e)
- **MINDKETTŐ:** Kazán főkapcsoló = switch.kazan_fo (UGYANAZ!)

**Tesztelés:**

1. **Mindkét zóna OFF:**
   ```
   ✓ Kazán: KI
   ✓ Relék: Minden KI
   ```

2. **Földszint HEAT ON (current < target):**
   ```
   ✓ Földszint relék: BE
   ✓ Kazán: BE
   ✓ Emelet relék: KI
   ✓ Log: "active_zones=1"
   ```

3. **Emelet is HEAT ON:**
   ```
   ✓ Földszint relék: BE
   ✓ Emelet relék: BE
   ✓ Kazán: BE (továbbra is)
   ✓ Log: "active_zones=2"
   ```

4. **Földszint OFF kapcsol (elérte a célt):**
   ```
   ✓ Földszint relék: KI
   ✓ Emelet relék: BE (még fűt)
   ✓ Kazán: BE (mert Emelet még aktív!)
   ✓ Log: "active_zones=1"
   ```

5. **Emelet is OFF kapcsol:**
   ```
   ✓ Emelet relék: KI
   ✓ Kazán: KI (nincs több aktív zóna)
   ✓ Log: "active_zones=0"
   ✓ Log: "Boiler relay ... → TURN_OFF"
   ```

---

## 🐛 HIBAKERESÉS

### Gyakori Problémák és Megoldások

#### 1. "Entity not available" / Szürke termosztát kártya

**OK:** A szenzor vagy relék entity_id-je nem jó.

**MEGOLDÁS:**
```
1. Fejlesztői eszközök → Állapotok
2. Keresd meg: sensor.temp_foldszint (pontos név?)
3. Másold ki a teljes entity_id-t
4. SmartHeatZones → Fogaskerék → Illeszd be pontosan
```

#### 2. Fordítások még mindig "label_1" formátumban

**OK:** Böngésző cache vagy HA cache.

**MEGOLDÁS:**
```bash
# SSH-ban:
cd /config
rm -rf .cache/
ha core restart

# Böngészőben:
CTRL+SHIFT+DEL → Clear everything
CTRL+F5
```

#### 3. Relék kapcsolnak, de azonnal vissza is kapcsolnak

**OK:** Hiszterézis túl kicsi vagy szenzor zajog.

**MEGOLDÁS:**
```
Options → Hiszterézis: 0.3 → 0.5 vagy 1.0
```

#### 4. Kazán nem kapcsol KI, pedig minden zóna OFF

**OK:** Különböző kazán entity-k a zónákban.

**MEGOLDÁS:**
```
Nyisd meg MINDEN zóna Options-át:
✓ Ellenőrizd: Kazán főkapcsoló = switch.kazan_fo (PONTOSAN UGYANAZ!)
```

#### 5. "RestoreEntity" import error

**OK:** Régebbi HA verzió (< 2024.1).

**MEGOLDÁS:**
```python
# climate.py 13. sor módosítás:
# HA < 2024.1:
from homeassistant.helpers.entity import RestoreEntity

# HA >= 2024.1:
from homeassistant.helpers.restore_state import RestoreEntity
```

---

## 📊 TELJESÍTMÉNY ELLENŐRZÉS

### Optimális Működés Jelei

✅ **Log tiszta:**
- Nincs ERROR vagy WARNING sor
- DEBUG üzenetek rendszeresek (sensor update, evaluate)
- Service call-ok sikeresek

✅ **Kapcsolási gyakoriság:**
- Hiszterézis sávban: NINCS kapcsolás
- Sensor változás (0.1°C): Evaluate fut, de NEM kapcsol
- Target elérése: 1x kikapcsol, utána STABIL

✅ **Válaszidő:**
- Target állítás → Log bejegyzés: < 1 másodperc
- Log bejegyzés → Fizikai kapcsolás: < 2 másodperc
- Összesen: < 3 másodperc

✅ **Memória használat:**
```bash
# SSH-ban:
ha core stats

# SmartHeatZones < 10 MB RAM / zóna
```

---

## 🎯 SIKERES TELEPÍTÉS CHECKLIST

```
□ Biztonsági mentés elkészült
□ climate.py lecserélve (v1.4.4)
□ translations/hu.json lecserélve
□ HA újraindítva (teljes restart)
□ Böngésző cache törölve
□ Debug log bekapcsolva

TESZTEK:
□ Teszt #1: Zóna látható, temperature jelenik meg
□ Teszt #2: Target állítás → Relék kapcsolnak
□ Teszt #3: OFF/HEAT kapcsoló működik
□ Teszt #4: Hiszterézis stabil
□ Teszt #5: Ajtó lockout működik
□ Teszt #6: Fordítások magyarul
□ Teszt #7: Schedule auto váltás
□ Teszt #8: Többzónás koordináció

□ Nincs ERROR a logban
□ Fizikai relék kattannak
□ Kazán elindul/leáll helyesen
```

---

## 📞 TÁMOGATÁS

Ha a fenti lépések után sem működik:

1. **Gyűjts információt:**
   ```
   - HA verzió: Beállítások → Rendszer → Általános
   - Integráció verzió: Nézd meg climate.py 3. sor
   - Teljes log: Beállítások → Rendszer → Naplók (mentsd el txt-be)
   - Screenshot: Options flow (minden beállítás látható)
   ```

2. **GitHub Issue:**
   - https://github.com/forreggbor/SmartHeatZones/issues
   - Részletes leírás + log + screenshot

3. **Vagy kérdezz itt:**
   - Home Assistant Community
   - Reddit: r/homeassistant

---

## 🚀 KÖVETKEZŐ LÉPÉSEK (Opcionális)

### PV Integráció Előkészítése

Ha van napelemes rendszered:

1. **PV sensor azonosítása:**
   ```
   Fejlesztői eszközök → Állapotok
   Keress: "power" vagy "pv" vagy "solar"
   
   Példa: sensor.solar_power (W)
   ```

2. **Többlet energia logika (jövőbeli funkció):**
   ```python
   # Pszeudokód:
   if pv_power > 2000W:  # Többlet van
       target_temp_boost = +2.0°C
   ```

3. **Várd a következő verziót (v1.5.0):**
   - PV aware fűtés
   - Dinamikus hiszterézis
   - Prediktív indítás

---

**Verzió:** Telepítési útmutató v1.0  
**Dátum:** 2025-10-26  
**Integráció:** SmartHeatZones v1.4.4