# SmartHeatZones v1.4.2

**Multi-zone intelligent heating control for Home Assistant**  
**Többzónás intelligens fűtésvezérlés Home Assistant-hoz**

**Author / Szerző:** forreggbor  
**License:** MIT (lásd a fájl végén)

---

## 🇬🇧 English

### What is SmartHeatZones?

SmartHeatZones is a **custom Home Assistant integration** that turns your relays, sensors and thermostatic rules into a sane, robust, multi-zone heating controller.

It focuses on:

- **Zone-based heating** (per zone: temperature sensor + one or more relays)

- **Single shared boiler main relay** (kept ON while any zone needs heat)

- **Hysteresis control** (thermostat-like behaviour, no relay chattering)

- **Time-of-day schedule** (1–4 adjustable blocks per zone, editable via UI)

- **Door/window lockout** (optional; if open → no heat)

- **Manual override semantics** (target change above/below current temp toggles HEAT/OFF)

- **All configuration via GUI** (Config Flow + Options dialog)

- **Full logging at DEBUG level** (development build)

Version **1.4.2** supports Home Assistant **2025.10+** and uses contemporary HA APIs (e.g., `UnitOfTemperature`, `vol.Schema` with selectors, proper options flow).

---

### Features

- **N zones** (add one integration entry per zone)

- Per zone:
  
  - **Temperature sensor** (any HA `sensor` with a numeric state)
  
  - **Zone relays** (`switch` domain; pumps/valves; multiple allowed)
  
  - **Door/window sensors** (`binary_sensor`; optional; multiple allowed)
  
  - **Hysteresis** (°C, default 0.3)
  
  - **Schedule** (1–4 blocks, each `start`, `end`, `temp`, editable in UI)

- **Global boiler main relay** (single `switch`, shared across zones; never toggled OFF if any zone is active)

- **Thermostat-style behaviour** in Lovelace:
  
  - Increasing target **above** current → auto switch to **HEAT**
  
  - Decreasing target **below** current → auto switch to **OFF**

- **All options editable in UI**; values persist and are re-suggested on reopen

- **Robust logging** at DEBUG (sensor updates, relay calls, boiler coordination)

---

### Installation

1. Copy the directory:
   
   `custom_components/smartheatzones/`
   
   into your Home Assistant config folder (so it becomes `/config/custom_components/smartheatzones`).

2. Restart Home Assistant (Developer Tools → Restart or full restart).

3. Go to **Settings → Devices & Services → Add Integration → SmartHeatZones**  
   Create an entry for each zone (e.g., “Ground floor”, “Upper floor”, “Attic”).

4. After adding, click the gear icon (Options) on each zone and configure:
   
   - Temperature sensor (entity selector)
   
   - Boiler main relay (shared)
   
   - Zone relays (one or more)
   
   - Door/window sensors (optional)
   
   - Hysteresis
   
   - Active time blocks (1–4) and their start/end times + target temperatures

---

### Entities

Each zone entry creates a **`climate.<zone>`** entity with:

- Modes: `heat`, `off`

- Features: `target_temperature` (°C)

- State: reflects current sensor value; internal hysteresis avoids frequent toggling

**Important:** The **boiler main relay** is not exposed as a separate entity by this integration; you select an existing `switch` entity (e.g. a Shelly) to serve as the **shared boiler main relay**. SmartHeatZones keeps this relay **ON while any zone requests heat**.

---

### How it works

- The **zone evaluates** `current_temp`, `target_temp` and `hysteresis`:
  
  - If `current + hyst/2 < target` → zone **needs heat** → turns **ON** all its **zone relays** and marks itself **active** in the global set.
  
  - If `current - hyst/2 ≥ target` → zone **too hot** → turns **OFF** its **zone relays** and marks itself **inactive**.
  
  - Otherwise (within hysteresis band) → **no change**.

- The **BoilerManager** observes the set of **active zones**:
  
  - If **any** zone active → **boiler main relay ON**
  
  - If **none** active → **boiler main relay OFF**

- **Door/window sensors** (optional):
  
  - If any is open → the zone won’t request heat (zone relays remain OFF) even if target suggests HEAT.

- **Schedule**:
  
  - On HA start and at option changes, the zone computes which time block contains **now** and sets `target_temperature` accordingly.

- **Manual override**:
  
  - If you increase target above current temp while HVAC is OFF, the integration **switches to HEAT**.
  
  - If you decrease target below current temp while HVAC is HEAT, the integration **switches to OFF**.

---

### Lovelace

Use a standard **Thermostat card** for each zone’s `climate.<zone>` entity.  
For additional controls (e.g., Quick set buttons “Comfort / Eco / Away”), use Mushroom or Button cards that call `climate.set_temperature` on the zone.

---

### Troubleshooting

- **No gear icon / Options not opening**  
  Ensure `manifest.json` has `"config_flow": true`, restart HA, clear browser cache.

- **500 Internal Server Error in options**  
  Typically caused by mismatched `const.py` keys and `options_flow.py` imports. Make sure all constants exist (see this README’s list).

- **Boiler main relay turns OFF while another zone is still heating**  
  Check that **all zones** have the **same** Boiler Main Relay selected in Options. The integration propagates the last option across zones automatically, but verify after edits.

- **Relays not switching**  
  Confirm you selected real `switch.*` entities and they are controllable in HA. Watch the log (DEBUG) for service calls and errors.

- **Temperature not updating**  
  Verify the sensor state is a numeric string (not `unknown/unavailable`). The log shows when sensor updates are received.

---

### Logging

This build is **DEBUG-oriented**. You can ensure verbosity via `configuration.yaml`:

`logger:   default: info   logs:     custom_components.smartheatzones: debug`

---

### Roadmap

- Optional **adaptive learning** (heat rise rate, overshoot prevention per zone)

- **Outdoor temperature** influence and **season detection**

- **Hybrid energy mode** (prefer heat pump/AC when PV production is sufficient)

- **More UI helpers** and global dashboards

- HACS release packaging & store listing

---

### Changelog (1.4.2)

- Boiler main relay is global and shared; safe coordination across zones

- Manual thermostat semantics in Lovelace

- Options flow: value persistence + suggested defaults; 1–4 schedule blocks

- Door/window lockout

- Updated to modern HA APIs (2025.10+), options deprecation fixes

- Full DEBUG logging for development

---

## 🇭🇺 Magyar

### Mi az a SmartHeatZones?

A SmartHeatZones egy **egyedi Home Assistant integráció**, amely több zóna fűtését kezeli – mindegyik zónához hőmérő szenzort és egy vagy több relét rendelhetsz, miközben egy **közös kazán főkapcsolót** használsz. A rendszer **hiszterézises** termosztát-logikát követ, **időalapú ütemezést** támogat (napszakok), és **ajtó/ablak érzékelőkkel** is együttműködik.

Fő elvek:

- **Zóna alapú vezérlés** (zónánként szenzor + relék)

- **Közös kazán főkapcsoló** (mindaddig bekapcsolva, amíg bármely zóna fűt)

- **Hiszterézis** (stabil kapcsolás, nincs zizegés)

- **Ütemezés** (1–4 napszak zónánként, GUI-ból szerkeszthető)

- **Ajtó/ablak tiltás** (opcionális; nyitva → nincs fűtés)

- **Kézi mód** Lovelace termosztátról (célhőmérséklet fölé/felé kapcsol)

- **Minden GUI-ból állítható** (Integráció + Opciók)

- **Részletes naplózás** (DEBUG szinten)

---

### Telepítés

1. Másold a mappát:
   
   `custom_components/smartheatzones/`
   
   a Home Assistant konfigurációs könyvtárába (`/config/custom_components/smartheatzones`).

2. Indítsd újra a Home Assistant-ot.

3. **Beállítások → Eszközök és szolgáltatások → Integráció hozzáadása → SmartHeatZones**  
   Hozz létre egy bejegyzést minden zónához (pl. „Földszint”, „Emelet”, „Padlás”).

4. A létrehozás után kattints a **fogaskerék ikonra** (Opciók) és állítsd be:
   
   - Hőmérséklet szenzor
   
   - Kazán főkapcsoló (közös kapcsoló, `switch` domain)
   
   - Zóna relék (egy vagy több `switch`)
   
   - Ajtó/ablak érzékelők (`binary_sensor`; opcionális)
   
   - Hiszterézis
   
   - Aktív napszakok (1–4), és azok kezdete/vége + hőmérséklet

---

### Entitások

Minden zóna létrehoz egy **`climate.<zóna>`** entitást:

- Módok: `heat`, `off`

- Funkciók: `target_temperature` (°C)

- Állapot: a szenzorból olvasott hőmérséklet, hiszterézises döntés

**Fontos:** A **kazán főkapcsoló** nem külön entitás itt; egy létező `switch` entitást választasz, amit az integráció **közösen** használ. A kazán főkapcsoló **ON marad**, amíg bármely zóna fűtést kér.

---

### Működés

- A zóna **értékel**: `jelenlegi`, `cél`, `hiszterézis`:
  
  - Ha `jelenlegi + hiszt/2 < cél` → **fűtés kell** → **BE** kapcsolja a **zóna reléket**, és **aktívnak** jelöli magát.
  
  - Ha `jelenlegi - hiszt/2 ≥ cél` → **túl meleg** → **KI** kapcsolja a zóna reléket, és **inaktiválja** magát.
  
  - Különben (hiszterézis sávban) → **nincs változás**.

- A **BoilerManager** figyeli az **aktív zónák halmazát**:
  
  - Ha **van** aktív zóna → **kazán főkapcsoló ON**
  
  - Ha **nincs** aktív → **kazán főkapcsoló OFF**

- **Ajtó/ablak érzékelők**:
  
  - Nyitás esetén a zóna **nem kér fűtést** (zóna relék OFF), még ha a célhőmérséklet indokolná.

- **Ütemezés**:
  
  - Induláskor és beállításkor a rendszer megkeresi, melyik idősávban vagyunk, és annak megfelelően állítja a `target_temperature`-t.

- **Kézi mód Lovelace-ben**:
  
  - Célhőmérséklet **emelése** az aktuális fölé → **HEAT**
  
  - Célhőmérséklet **csökkentése** az aktuális alá → **OFF**

---

### Lovelace

Használj standard **Thermostat** kártyát a `climate.<zóna>` entitásokhoz.  
További gyorsgombokhoz (Komfort/Eco/Távollét) készíthetsz Mushroom/Button kártyákat, amelyek `climate.set_temperature` szolgáltatást hívnak.

---

### Hibakeresés

- **Nincs fogaskerék / nem nyílik meg az Opciók**  
  Ellenőrizd, hogy a `manifest.json` tartalmazza a `"config_flow": true` mezőt. Indítsd újra a HA-t, töröld a böngésző cache-t.

- **500-as hiba az Opciókban**  
  Többnyire a `const.py` és `options_flow.py` konstansai nincsenek összhangban. Ellenőrizd, hogy minden kulcs létezik (lásd lentebb).

- **Kazán főkapcsoló lekapcsol, miközben másik zóna még fűt**  
  Ellenőrizd, hogy **minden zónában ugyanaz** a kazán főkapcsoló van kiválasztva. Az integráció automatikusan terjeszti az utolsó beállítást, de érdemes ellenőrizni.

- **Relék nem kapcsolnak**  
  Bizonyosodj meg róla, hogy valódi `switch.*` entitásokat választottál, és HA-ból kapcsolhatók. Nézd a logot (DEBUG).

- **Hőmérséklet nem frissül**  
  Győződj meg arról, hogy a szenzor állapota numerikus (nem `unknown/unavailable`). A log mutatja a frissítéseket.

---

### Naplózás

Ez a build **DEBUG** módú. Javasolt `configuration.yaml`:

`logger:   default: info   logs:     custom_components.smartheatzones: debug`

---

### Tervek

- **Adaptív** vezérlés (felfűtési meredekség, túllövés-csillapítás zónánként)

- **Külső hőmérséklet** hatás és **szezonfelismerés**

- **Hibrid energia mód** (PV termelés esetén klíma/HP előnyben)

- Gazdagabb **UI** és összefoglaló kártyák

- Hivatalos **HACS** megjelenés

---

### Változások (1.4.2)

- Közös kazán főkapcsoló – biztonságos többzónás koordináció

- Termosztát-szerű kézi vezérlés Lovelace-ben

- Opciós űrlap: érték-visszatöltés, 1–4 napszak

- Ajtó/ablak tiltás

- Modern HA API-k (2025.10+), deprecations javítva

- Teljes DEBUG naplózás fejlesztéshez

---

## Constants reference (for developers)

Make sure these exist in `const.py`:

- `DOMAIN`, `PLATFORMS`

- `CONF_SENSOR`, `CONF_ZONE_RELAYS`, `CONF_BOILER_MAIN`, `CONF_DOOR_SENSORS`, `CONF_HYSTERESIS`, `CONF_SCHEDULE`, `CONF_ACTIVE_BLOCKS`

- `DATA_ACTIVE_ZONES`, `DATA_BOILER_MAIN`, `DATA_ENTRIES`

- `DEFAULT_HYSTERESIS`, `DEFAULT_SCHEDULE`

- `MIN_TEMP_C`, `MAX_TEMP_C`
