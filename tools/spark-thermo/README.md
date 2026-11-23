# spark-thermo: Hitze-Schutz für Trainings auf einer fremden GPU-Maschine

Entstanden für die DGX Spark (überhitzt leicht). Funktioniert auf jedem Linux-Rechner mit NVIDIA-GPU.

## Was ist drin?

| Datei | Wo läuft es | Aufgabe |
|---|---|---|
| `thermo.py` | Remote, neben den Jobs | Wachhund: misst alle 5 s, pausiert ab 85 °C, macht unter 70 °C weiter, beendet ab 90 °C |
| `gov.py` | Remote, im Training | Bremse: rechnet nur die Hälfte der Zeit, wartet ab 75 °C bis 70 °C |
| `run.sh` | Remote | Startet einen Job mit Log, startet nichts, wenn `STOP` da ist |
| `env.sh` | Remote | Alle Caches im Arbeitsordner, damit Löschen alles entfernt |
| `status.sh` | Lokal | Temperatur, Wachhund, RAM, Log-Ende anzeigen |
| `wait_job.sh` | Lokal | Warten, bis ein Job fertig ist oder `STOP` erscheint |

Alles braucht nur `python3` und `bash`. `gov.py` nutzt torch nur, wenn dein Code es schon geladen hat.

## Die Regeln

- Nur **ein** schwerer Job gleichzeitig.
- Gemessen wird die **heißeste Thermal-Zone** (`/sys/class/thermal`), nicht nur die GPU.
- **Pause** ab 85 °C (SIGSTOP), **weiter** unter 70 °C (SIGCONT).
- **Abbruch** ab 90 °C oder wenn die GPU sich wegen Hitze drosselt (HW/SW-Slowdown-Zähler steigt).
  Dann schreibt der Wachhund `STOP`, und `run.sh` startet keinen Job mehr.
- Der Wachhund steuert **nur eigene Prozesse**, deren Programm im Arbeitsordner liegt (z. B. `venv/bin/python`).

## Anleitung

### 1. Auf die Maschine kopieren

```bash
ssh user@host 'mkdir -p ~/thermo-work/code'
scp thermo.py gov.py run.sh env.sh user@host:~/thermo-work/code/
ssh user@host 'mv ~/thermo-work/code/env.sh ~/thermo-work/env.sh'
```

Anderer Ordner? Überall `THERMO_BASE=/pfad` setzen (remote) bzw. `THERMO_BASE_REMOTE=/pfad` (lokal).

### 2. Wachhund starten (in tmux, damit er weiterläuft)

```bash
ssh user@host
tmux -S ~/thermo-work/tmux.sock new -d -s thermo '/usr/bin/python3 ~/thermo-work/code/thermo.py'
```

Wichtig: mit `/usr/bin/python3` starten, **nicht** mit dem venv-Python, sonst stoppt er sich selbst.

### 3. Bremse ins Training einbauen

```python
try:
    import gov          # liegt in ~/thermo-work/code, env.sh setzt PYTHONPATH
except ImportError:     # z. B. auf dem Laptop
    gov = None

for epoch in range(epochs):
    ...                 # ein Epoch / ein Batch
    if gov:
        gov.tick()
print(gov.summary() if gov else "")
```

### 4. Job starten

```bash
tmux -S ~/thermo-work/tmux.sock new -d -s job \
  'bash ~/thermo-work/code/run.sh probe ~/thermo-work/venv/bin/python train.py'
```

Erst eine **Probe von 10 min** laufen lassen und die Temperatur anschauen, dann den echten Lauf.

### 5. Lokal überwachen

```bash
export SPARK_HOST=user@host
bash status.sh 24 probe      # letzte 2 min, Log "probe"
bash wait_job.sh 30          # bis 30 min warten
```

`status.sh` zeigt: höchste Zone, Leistung, Wachhund-Meldungen, ob `STOP` da ist, RAM.

### 6. Nach einem Abbruch

`STOP` ansehen (`cat ~/thermo-work/STOP`), Ursache klären, dann `rm ~/thermo-work/STOP`.

### 7. Aufräumen (auf fremden Maschinen immer)

```bash
ls -la ~ > vorher.txt                     # vor dem ersten Kopieren, lokal speichern
tmux -S ~/thermo-work/tmux.sock kill-server
rm -rf ~/thermo-work
nvidia-smi                                # keine eigenen Prozesse mehr
ls -la ~ > nachher.txt                    # mit vorher.txt vergleichen und aufheben
```

## Logs

| Datei | Inhalt |
|---|---|
| `logs/temp.csv` | eine Zeile alle 5 s: GPU-Temperatur, Leistung, Takt, Zähler, Zone, NVMe, Zustand |
| `logs/watchdog.log` | PAUSE / RESUME / KILL mit Zeit und Temperatur |
| `logs/jobs.log` | eine Zeile pro beendetem Job mit Rückgabewert |
| `logs/<name>.log` | Ausgabe des Jobs |
