# SmartHeatZones Integráció - Teljes Működési Elemzés

## 1. ÁLTALÁNOS ÁTTEKINTÉS

### Cél
Többzónás intelligens fűtésvezérlés Home Assistant-ban, ahol minden zóna önállóan kezelhető termosztát, de egy közös kazán főkapcsolón osztoznak.

### Verzió
1.4.2 (2025.10+ HA verzióhoz optimalizálva)

### Fejlesztési Állapot
⚠️ **Aktív fejlesztés alatt, hibákat tartalmaz, NEM ajánlott éles környezetben!**

---

## 2. ARCHITEKTÚRA

### Fő Komponensek

```
SmartHeatZones Integráció
├── Config Flow (config_flow.py)
│   ├── Zóna létrehozás
│   └── Options Flow (beállítások)
├── Climate Platform (climate.py)
│   ├── Zónánként 1 climate entitás
│   └── Termosztát logika
├── BoilerManager (__init__.py)
│   ├── Aktív zónák nyilvántartása
│   └── Kazán főkapcsoló vezérlés
└── Konstansok (const.py)
    └── Konfiguráció kulcsok
```

### Entitás Struktúra

**Minden zóna létrehoz:**
- `climate.<zóna_név>` entitást
  - Módok: `heat`, `off`
  - Jellemzők: `target_temperature` beállítható
  - Állapot: aktuális hőmérséklet (szenzorból)

---

## 3. MŰKÖDÉSI LOGIKA

### 3.1 Zóna Vezérlés (Climate Entity)

#### Hiszterézises Termosztát Logika

```python
# Pszeudokód
current_temp = hőmérséklet_szenzor.állapot
target_temp = felhasználó_által_beállított_cél
hysteresis = 0.3  # alapértelmezett

# Fűtés szükséges?
if current_temp + (hysteresis / 2) < target_temp:
    → Zóna állapot: AKTÍV (fűtés kell)
    → Zóna relék: BE kapcsolás
    → Zóna regisztráció: aktív zónák halmazába
    
# Túl meleg?
elif current_temp - (hysteresis / 2) >= target_temp:
    → Zóna állapot: INAKTÍV
    → Zóna relék: KI kapcsolás
    → Zóna törlés: aktív zónák halmazából
    
# Hiszterézis sávban (nincs változás)
else:
    → Tartja a jelenlegi állapotot
```

**Példa:**
- Cél: 22°C, Hiszterézis: 0.3°C
- Bekapcsol ha: aktuális < 21.85°C
- Kikapcsol ha: aktuális ≥ 22.15°C
- 21.85 - 22.15 között: nincs változás

#### Ajtó/Ablak Tiltás

```python
if any(ajtó_ablak_szenzor.állapot == "on"):  # nyitva
    → Zóna relék: KI (még ha fűtés kellene is)
    → Kazán: lehet hogy fut más zóna miatt
```

### 3.2 Kazán Főkapcsoló Menedzsment (BoilerManager)

**Globális Koordináció:**

```python
# __init__.py - BoilerManager osztály
DATA_ACTIVE_ZONES = "active_zones"  # set típus
DATA_BOILER_MAIN = "boiler_main_entity_id"

# Amikor zóna aktívvá válik:
hass.data[DOMAIN][DATA_ACTIVE_ZONES].add(zone_id)
→ ellenőriz_és_kapcsol_kazánt()

# Amikor zóna inaktívvá válik:
hass.data[DOMAIN][DATA_ACTIVE_ZONES].remove(zone_id)
→ ellenőriz_és_kapcsol_kazánt()

def ellenőriz_és_kapcsol_kazánt():
    if len(active_zones) > 0:
        switch.turn_on(boiler_main_relay)
    else:
        switch.turn_off(boiler_main_relay)
```

**Fontos:** A kazán főkapcsoló NEM külön entitás, hanem egy meglévő `switch.*` entitás, amit az integráció vezérel.

### 3.3 Időzítés (Schedule)

**1-4 Napszak Definiálható:**

```yaml
# Példa konfiguráció
schedule:
  - start: "06:00"
    end: "08:00"
    temp: 22.0  # Reggel komfort
  - start: "08:00"
    end: "16:00"
    temp: 18.0  # Napközben eco
  - start: "16:00"
    end: "22:00"
    temp: 22.0  # Este komfort
  - start: "22:00"
    end: "06:00"
    temp: 16.0  # Éjszaka alacsony
```

**Működés:**
- HA induláskor: aktuális időblokk keresése → `target_temp` beállítása
- Opciók módosításakor: újraértékelés
- **HIÁNYZIK:** Automatikus átváltás napszakok között futás közben

### 3.4 Kézi Felülírás Lovelace-ből

**Termosztát Kártya Logika:**

```python
# Amikor felhasználó változtat target_temp-en:

if new_target > current_temp AND hvac_mode == OFF:
    → hvac_mode = HEAT  # Auto bekapcsol
    
if new_target < current_temp AND hvac_mode == HEAT:
    → hvac_mode = OFF  # Auto kikapcsol
```

**Cél:** Intuitív kezelés - ha melegebbre állítasz → fűt, ha hidegebbre → nem fűt.

---

## 4. KONFIGURÁCIÓ

### 4.1 Config Flow (Zóna Létrehozás)

```python
# config_flow.py
Lépés 1: Zóna név megadása
  → Létrejön: climate.<zone_name>

# Kezdeti minimális adatok:
{
    "name": "Földszint",
    "sensor": None,  # később Options-ban
    "zone_relays": [],
    "boiler_main": None,
    ...
}
```

### 4.2 Options Flow (Beállítások)

**Szerkeszthető Paraméterek:**

| Paraméter | Típus | Leírás |
|-----------|-------|--------|
| `sensor` | entity_selector (sensor) | Hőmérséklet szenzor |
| `boiler_main` | entity_selector (switch) | Közös kazán főkapcsoló |
| `zone_relays` | entity_selector (switch, multiple) | Zóna relék (1 vagy több) |
| `door_sensors` | entity_selector (binary_sensor, multiple) | Ajtó/ablak szenzor (opcionális) |
| `hysteresis` | number (0.1-2.0) | Hiszterézis °C-ban |
| `active_blocks` | number (1-4) | Aktív időblokkok száma |
| `schedule[0-3]` | Blokkonként: start, end, temp | Napszak definíciók |

**Érték Perzisztencia:**
- Utolsó mentett értékek automatikusan visszatöltődnek újranyitáskor
- Default értékek: `const.py` → `DEFAULT_*`

---

## 5. KÓDSTRUKTÚRA

### Fájlok és Felelősségek

```
custom_components/smartheatzones/
│
├── manifest.json          # Integráció metaadatok
│   └── domain: "smartheatzones"
│   └── config_flow: true
│   └── version: "1.4.2"
│   └── iot_class: "local_polling"
│
├── __init__.py            # Entry point + BoilerManager
│   ├── async_setup_entry()
│   ├── BoilerManager osztály
│   │   ├── register_zone_activity()
│   │   ├── unregister_zone_activity()
│   │   └── update_boiler_state()
│   └── hass.data[DOMAIN] inicializálás
│
├── config_flow.py         # UI konfigurációs flow
│   ├── SmartHeatZonesConfigFlow
│   │   └── async_step_user()  # Zóna létrehozás
│   └── SmartHeatZonesOptionsFlow
│       └── async_step_init()  # Beállítások szerkesztés
│
├── climate.py             # Climate platform implementáció
│   ├── SmartHeatZoneClimate(ClimateEntity)
│   │   ├── async_set_temperature()
│   │   ├── async_set_hvac_mode()
│   │   ├── _async_control_heating()  # Hiszterézis logika
│   │   └── _async_sensor_changed()   # Szenzor callback
│   └── Termosztát jellemzők
│
├── const.py               # Konstansok
│   ├── DOMAIN = "smartheatzones"
│   ├── CONF_* kulcsok (sensor, relays, ...)
│   ├── DATA_* kulcsok (active_zones, boiler_main)
│   └── DEFAULT_* értékek
│
└── translations/
    ├── en.json            # Angol fordítások
    └── hu.json            # Magyar fordítások (ha van)
```

---

## 6. AZONOSÍTOTT PROBLÉMÁK (KÓD ELEMZÉS ALAPJÁN)

### ✅ JÓ HÍREK
A kód alapvetően **JÓL VAN IMPLEMENTÁLVA**! A hiszterézis logika, relé kapcsolás és kazán menedzsment mind megvan.

### ⚠️ VALÓS PROBLÉMÁK

#### 1. **Relé Kapcsolás Valószínű Oka: Inicializálási Probléma**

**MEGTALÁLTAM!** A `climate.py` 115-116. sorában:
```python
async def async_set_temperature(self, **kwargs: Any) -> None:
    """Célhőmérséklet beállítása."""
    temp = kwargs.get(ATTR_TEMPERATURE)
    if temp is None:
        return
    self._target_temp = float(temp)
    _LOGGER.info("%s [%s] Target temperature set to %.1f°C", LOG_PREFIX, self.name, self._target_temp)
    await self._evaluate_heating()  # ← EZ MEGVAN!
    self.async_write_ha_state()
```

**A kód helyes!** De a probléma máshol van:

**VALÓDI OK:**
```python
# climate.py 69. sor - async_setup_entry()
sensor = data.get(CONF_SENSOR)  # ← Options-ból jön
relays = data.get(CONF_ZONE_RELAYS, [])
boiler_entity = data.get(CONF_BOILER_MAIN)
```

**A CONFIG FLOW-BAN** (config_flow.py 46. sor) a zóna létrehozásakor:
```python
return self.async_create_entry(title=title, data=self._data)
#                                            ^^^^^^^^^^^^
# Ez a 'data'-ba megy, DE az Options-ban 'options'-ba mentesz!
```

**PROBLÉMA:** 
- ConfigFlow: **`data`**-ba ment
- OptionsFlow: **`options`**-ba ment  
- Climate.py: **csak** `entry.options`-ból olvas (69. sor)

Ha nem nyitottad meg az Options-t és nem mentetted, akkor a `sensor`, `relays`, `boiler` mind **`None` vagy üres lista**!

**BIZONYÍTÉK:**
```python
# climate.py 102. sor
async def _evaluate_heating(self):
    if self._hvac_mode == HVACMode.OFF:
        return  # ← Ha OFF módban vagy, NEM kapcsol!
```

És a 79. sorban:
```python
self._hvac_mode = HVACMode.OFF  # ← Kezdőállapot mindig OFF!
```

#### 2. **Fordítások Nem Jelennek Meg**
**Lehetséges okok:**

```python
# A) translations/hu.json hiányzik vagy rossz helyen van
# B) manifest.json-ban nincs:
{
    "config_flow": true,
    "translation_key": "smartheatzones"  # ← LEHET HOGY HIÁNYZIK
}

# C) strings.json vs translations/ struktúra keveredés
# Régi: strings.json
# Új HA: translations/en.json, translations/hu.json
```

#### 3. **Napszak Automatikus Váltás Hiányzik**
- Nincs `async_track_time_interval()` vagy hasonló
- Csak indulásnál és options változásnál értékel

### 🐛 EGYÉB HIBÁK

#### 4. **Kazán Főkapcsoló Szinkronizáció**
- Ha különböző zónák különböző kazán relét választanak → konfliktus
- Nincs validáció vagy figyelmeztetés

#### 5. **Hibaállítás Kezelés**
- Mi van ha szenzor `unavailable` vagy `unknown`?
- Mi van ha switch nem válaszol?

#### 6. **State Restoration**
- Újraindítás után visszaáll-e a target_temp és hvac_mode?

---

## 7. MŰKÖDÉSI FOLYAMAT PÉLDA

### Scenario: Földszint Zóna Fűtése

```
1. INDULÁS
   ├── HA betölti smartheatzones integrációt
   ├── __init__.py: BoilerManager létrejön
   ├── climate.py: climate.foldszint entitás létrejön
   └── Kezdőállapot:
       ├── current_temp: 19.5°C (szenzorból)
       ├── target_temp: 22.0°C (schedule-ból)
       ├── hvac_mode: off
       └── Zóna relék: KI

2. FELHASZNÁLÓ MÓDOSÍT
   ├── Thermostat kártyán: target_temp = 23.0°C
   ├── climate.async_set_temperature() hívódik
   └── ❌ HIBA: Nincs vezérlés meghívva!
   
   # KÉNEllenőrizni kell:
   └── ✓ Kellene:
       ├── Auto váltás HEAT módba (23 > 19.5)
       ├── _async_control_heating() meghívás
       ├── Hiszterézis ellenőrzés: 19.5 < 23 - 0.15 → IGEN
       ├── Zone relays: BE kapcsolás
       ├── BoilerManager.register_zone_activity("foldszint")
       └── Kazán főkapcsoló: BE

3. HŐMÉRSÉKLET EMELKEDIK
   ├── Szenzor: 19.5 → 20.0 → ... → 22.8 → 23.0 → 23.2°C
   ├── _async_sensor_changed() callback minden változásnál
   ├── Hiszterézis ellenőrzés folyamatos:
   │   ├── 22.8 < 23.15 → Továbbra fűt
   │   └── 23.2 >= 23.15 → KIKAPCSOL
   ├── Zone relays: KI
   ├── BoilerManager.unregister_zone_activity("foldszint")
   └── Ha nincs más aktív zóna → Kazán: KI

4. AJTÓ NYITÁS
   ├── binary_sensor.ajto = "on"
   ├── Zóna detektálja
   ├── Azonnal: Zone relays KI
   └── BoilerManager: Zóna inaktív (átmeneti lockout)
```

---

## 8. AJÁNLOTT FEJLESZTÉSEK PRIORIZÁLVA

### 🔴 AZONNAL (Kritikus Javítások)

1. **Relé Kapcsolás Implementálás**
   - `async_set_temperature()` → `_async_control_heating()` hívás
   - `async_set_hvac_mode()` → `_async_control_heating()` hívás
   - `_async_control_heating()` teljes implementáció

2. **Fordítások Javítás**
   - `translations/hu.json` létrehozása
   - `manifest.json` ellenőrzés
   - Kulcsok egyeztetése

3. **Alapvető Tesztelés**
   - Debug logolás minden lépésnél
   - Hibaállítások kezelése

### 🟡 HAMAROSAN (Működési Javítások)

4. **Napszak Auto Váltás**
   - `async_track_time_change()` használata
   - Óránként ellenőrzés + target_temp frissítés

5. **State Restoration**
   - `RestoreEntity` mixin használata
   - Újraindítás után állapot visszaállítás

6. **Kazán Szinkron Validáció**
   - Options mentéskor ellenőrzés
   - Figyelmeztetés ha különböző kazán választva

### 🟢 KÉSŐBB (Extra Funkciók)

7. **PV Integráció**
   - Napelem sensor figyelése
   - Fűtés engedélyezés többlet energia esetén
   - Dinamikus target_temp boost

8. **Adaptív Vezérlés**
   - Tanulás: felfűtési idő, túllövés
   - Prediktív indítás

9. **Dashboard & Monitoring**
   - Összefoglaló kártya
   - Energiafogyasztás tracking

---

## 9. DEBUG LOGOLÁS

### Javasolt configuration.yaml

```yaml
logger:
  default: info
  logs:
    custom_components.smartheatzones: debug
    custom_components.smartheatzones.climate: debug
    custom_components.smartheatzones.config_flow: debug
```

### Logokban Keresendő

```python
# Sikeres inicializálás
"SmartHeatZones domain data initialized"
"BoilerManager created"
"Climate entity climate.foldszint created"

# Szenzor frissítés
"Sensor update: sensor.temp_foldszint = 19.5"
"Evaluating heating control"

# Relé kapcsolás
"Turning ON zone relays: [switch.rele1, switch.rele2]"
"Registering zone 'foldszint' as active"
"Boiler main relay switch.kazan_fo: turning ON"

# Hibák
"ERROR: Failed to call service switch.turn_on"
"WARNING: Temperature sensor unavailable"
```

---

## 10. ÖSSZEFOGLALÁS

### ✅ MI MŰKÖDIK
- Config Flow: zónák létrehozása ✓
- Options Flow: beállítások UI ✓
- Climate entitás megjelenik ✓
- Szenzor beolvasás ✓
- Hiszterézis logika (elvileg) ✓

### ❌ MI NEM MŰKÖDIK
- **Relék NEM kapcsolnak** (kritikus!)
- **Fordítások nem jelennek meg**
- Napszak auto váltás hiányzik
- Nincs state restoration

### 🎯 KÖVETKEZŐ LÉPÉSEK

1. **Kód letöltése és áttekintése:**
   - `climate.py` teljes elemzése
   - `__init__.py` BoilerManager ellenőrzés

2. **Debug session:**
   - Log szint debug-ra
   - Manuális tesztelés kártyából
   - Logok elemzése

3. **Kritikus javítások implementálása**
   - Relé kapcsolás működőképessé tétele
   - Fordítások helyreállítása

---

**Verzió:** Elemzés v1.0 - 2025-10-26  
**Alapul véve:** SmartHeatZones v1.4.2 README