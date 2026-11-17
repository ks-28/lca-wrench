LCA Wrench – installation on the Mac
====================================

1. Put this folder "LCA-Wrench" in a permanent place, best in your home folder (the house icon) or in
   Applications. In Documents, Desktop or Downloads macOS asks for Terminal access at every start.
2. Double-click "Install LCA Wrench". macOS blocks it the first time, because the file is not from the
   App Store: System Settings → Privacy & Security → at the bottom "Open Anyway", then double-click again.
   (On older macOS versions, right-click → Open works too.)
   A Terminal window shows the progress. Takes about 3 to 5 minutes, needs internet.
   Everything is installed inside this folder only. The Activity Browser, conda and the
   Brightway projects are not changed. No administrator password needed.
3. Start: double-click the app "LCA Wrench" on the desktop (the installer puts it there), or "Start LCA Wrench" in this
   folder; the first time allow it as above.
   The browser opens LCA Wrench (Google Chrome works best). Keep the Terminal window open,
   closing it stops LCA Wrench.
4. The interface is in English. "Deutsch" at the top right switches it to German.

Data: a new project with BAFU 2026 or ecoinvent
On the start page "New project": empty, or right away with background data. Other projects stay untouched.
- BAFU 2026: the life cycle inventories of the Swiss Federal Administration (BAFU:2026) with the 25 impact
  categories of EF 3.1, freely available, loaded with sentier-brightway (about 36 MB, about a minute).
- ecoinvent with account: like in the Activity Browser, with your own user name and password of ecoinvent.org
  (sent to ecoinvent only). About 1 GB download, 10 to 30 minutes.
- ecoinvent from files: the file "ecoinvent 3.x_cutoff_ecoSpold02.7z" downloaded from ecoinvent.org and, for the
  impact methods, "ecoinvent 3.x_LCIA_implementation.7z". 10 to 30 minutes.

Comparing BAFU and ecoinvent
Build your model in a project with BAFU 2026, make a second project with ecoinvent, then open the result of
your product and the tab "Other database". Every BAFU dataset your model uses directly gets a counterpart in
ecoinvent: suggested from name, product, location and unit. Check the suggestions (the large ones first),
change them where needed, and confirm them. Confirmed matches are kept and can be exported as a JSON file in
the format of sentier-mappings, with ecoinvent datasets by code only.

Trying your own projects
At the first start LCA Wrench asks which project to open. To try it with your own data, best use
"Make a test copy": LCA Wrench copies the project file by file without opening the original. Everything
can be changed in the copy, the original stays as it is. With ecoinvent this takes a few minutes and needs
about as much disk space as the project.
- Projects from the Activity Browser 2 are opened only as a copy (otherwise the Activity Browser 2 could not
  read them any more).
- Projects from the Activity Browser 3 can also be opened directly. Databases not made in LCA Wrench are
  protected there: view and calculate yes, change only in a test copy. If the project was made with an older
  Brightway version, LCA Wrench asks first: Brightway rebuilds its calculation data when it is first opened.
- Do not have the Activity Browser and LCA Wrench open with the same project at the same time.

If something goes wrong: send the file "lca-wrench.log" from this folder. It holds the errors and the version
of LCA Wrench.

Remove: move the folder "LCA-Wrench" to the Trash. Copies LCA Wrench created are named "… (LCA Wrench)"
(older ones "… (Werkbank)" or "… (Workbench)") and can be deleted in the Activity Browser like any project.


LCA Wrench – Installation auf dem Mac (Deutsch)
===============================================

1. Diesen Ordner «LCA-Wrench» an einen festen Ort legen, am besten in den Benutzerordner (das Haus-Symbol)
   oder in «Programme». In «Dokumente», «Schreibtisch» oder «Downloads» fragt macOS beim Start jedes Mal
   nach Zugriffsrechten für das Terminal.
2. Doppelklick auf «Install LCA Wrench». macOS blockiert das beim ersten Mal, weil die Datei nicht aus
   dem App Store kommt: Systemeinstellungen → Datenschutz & Sicherheit → ganz unten «Dennoch öffnen»,
   danach nochmals doppelklicken. (Auf älteren macOS-Versionen geht auch: Rechtsklick → «Öffnen».)
   Ein Terminal-Fenster zeigt den Fortschritt. Dauer: etwa 3 bis 5 Minuten, Internet nötig.
   Alles wird nur in diesen Ordner installiert. Der Activity Browser, conda und die
   Brightway-Projekte werden nicht verändert. Kein Administrator-Passwort nötig.
3. Starten: Doppelklick auf die App «LCA Wrench» auf dem Schreibtisch (legt die Installation dorthin) oder auf «Start LCA Wrench»
   in diesem Ordner, beim ersten Mal wie oben freigeben.
   Der Browser öffnet LCA Wrench (am besten Google Chrome). Das Terminal-Fenster offen lassen,
   Schliessen beendet LCA Wrench.
4. Die Oberfläche ist englisch. «Deutsch» oben rechts schaltet auf Deutsch um (der Browser merkt es sich).

Daten: neues Projekt mit BAFU 2026 oder ecoinvent
Auf der Startseite «Neues Projekt»: leer, oder gleich mit Hintergrunddaten. Andere Projekte bleiben unberührt.
- BAFU 2026: die Ökoinventare der Bundesverwaltung (BAFU:2026) mit den 25 Wirkungskategorien von EF 3.1,
  frei verfügbar, geladen mit sentier-brightway (ca. 36 MB, etwa eine Minute).
- ecoinvent mit Konto: wie im Activity Browser, mit dem eigenen Benutzernamen und Passwort von ecoinvent.org
  (gehen nur an ecoinvent). Etwa 1 GB Download, 10 bis 30 Minuten.
- ecoinvent aus Dateien: die von ecoinvent.org heruntergeladene Datei «ecoinvent 3.x_cutoff_ecoSpold02.7z» und,
  für die Wirkungsmethoden, «ecoinvent 3.x_LCIA_implementation.7z». 10 bis 30 Minuten.

BAFU und ecoinvent vergleichen
Das Modell in einem Projekt mit BAFU 2026 bauen, ein zweites Projekt mit ecoinvent anlegen, dann beim Ergebnis
des Produkts den Reiter «Andere Datenbank» öffnen. Jeder BAFU-Datensatz, den das Modell direkt verwendet, bekommt
ein Gegenstück in ecoinvent, vorgeschlagen aus Name, Produkt, Ort und Einheit. Die Vorschläge prüfen (die grossen
zuerst), wo nötig ändern und bestätigen. Bestätigte Zuordnungen bleiben gespeichert und lassen sich als JSON-Datei
im Format von sentier-mappings exportieren, ecoinvent-Datensätze nur mit ihrem Code.

Eigene Projekte ausprobieren
Beim ersten Start fragt LCA Wrench, welches Projekt es öffnen soll. Zum Ausprobieren mit eigenen
Daten am besten «Testkopie anlegen»: LCA Wrench kopiert das Projekt Datei für Datei, ohne das Original
zu öffnen. In der Kopie lässt sich alles ändern, das Original bleibt wie es ist. Bei ecoinvent dauert das
einige Minuten und braucht etwa so viel Speicherplatz wie das Projekt.
- Projekte aus dem Activity Browser 2 öffnet LCA Wrench nur als Kopie (sonst könnte der Activity Browser 2
  sie danach nicht mehr lesen).
- Projekte aus dem Activity Browser 3 lassen sich auch direkt öffnen. Datenbanken, die nicht in LCA Wrench
  angelegt wurden, sind dort geschützt: ansehen und rechnen ja, ändern nur in einer Testkopie.
  Wurde das Projekt mit einer älteren Brightway-Version angelegt, fragt LCA Wrench vorher: Brightway baut
  beim ersten Öffnen seine Rechendaten neu auf.
- Activity Browser und LCA Wrench nicht gleichzeitig mit demselben Projekt offen haben.

Wenn etwas nicht klappt: die Datei «lca-wrench.log» in diesem Ordner schicken. Darin stehen die Fehler
und die Version von LCA Wrench.

Entfernen: den Ordner «LCA-Wrench» in den Papierkorb legen. Kopien, die LCA Wrench angelegt hat, heissen
«… (LCA Wrench)» (ältere «… (Werkbank)» oder «… (Workbench)») und lassen sich im Activity Browser wie jedes
Projekt löschen.
