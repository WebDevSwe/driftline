# DriftLine

DriftLine är en lokal samhälls- och ekonomisimulator där en liten handelsplats
växer genom invånarnas behov och den lokala ekonomins efterfrågan.

## Köra programmet

```powershell
python -m pip install -e .
python main.py
```

Testerna körs med:

```powershell
python -m pip install -e ".[test]"
pytest
```

Projektet kräver Python 3.12 eller senare.

## Simuleringsmodell

Världen börjar med tio invånare, ett torg, tält och inga företag. Varje månad
räknar motorn fram konkreta marknadssignaler för mat, arbeten, bostäder, handel,
service och industri. Företag skapas bara när efterfrågan, förväntad lönsamhet,
kapital och en möjlig ägare sammanfaller.

Den normala utvecklingen blir därför ungefär:

```text
matbrist -> jordbruk -> matöverskott -> inflyttning -> bostäder
         -> handel och service -> specialisering och industri
```

Det är ingen låst teknikstege. Om förutsättningarna förändras räknas behoven om
och samhället kan ta en annan väg.

### Invånare och drives

Alla invånare prioriterar samma grundbehov: mat, boende, inkomst, trygghet och
bekvämlighet. En drive ändrar hur tidigt och på vilket sätt personen försöker
lösa behovet. Den kan inte göra en invånare likgiltig inför hunger eller
hemlöshet.

Missnöje byggs upp månad för månad av hunger, arbetslöshet, hemlöshet, låg
stabilitet, skattetryck och en levnadsekonomi som inte går ihop. Långvarig
arbetslöshet eller ekonomisk stress kan därför leda till utflyttning. Inflyttning kräver i
stället matförsörjning och trovärdiga möjligheter till jobb eller bostad.

Invånarfönstret visar yrke eller arbetslöshet, lön, faktisk hemadress,
arbetsadress och pendlingsavstånd. En person kan nålas fast med knappen
`Nåla fast`; då ligger personen kvar överst och månadsvärden för ekonomi,
mat, hälsa, arbete och boende sparas med världen.

Världen visar också ett dragningskraftsvärde och uppskattad kriminalitet.
Dragningskraften ökar av låg skatt, stabilitet, lediga bostadsplatser och jobb.
Kombinationen bostad och jobb kan ge flera inflyttare samma månad. Hunger,
arbetslöshet, hemlöshet, kriminalitet och servicebrist sänker värdet. Lokal
matkapacitet begränsar hur stor en inflyttningsvåg kan bli, så snabb tillväxt
inte omedelbart skapar en artificiell svältspiral.

Invånare avsätter åtta procent av lönen till ett personligt pensionskapital hos
centralbanken. Vid 67 års ålder lämnar de arbetsmarknaden och får månatlig
pension så länge kapitalet och bankens reserv räcker. Dödsrisken börjar stiga
vid hög ålder och dödsfall samt pensionärer visas i statistiken. Egendom går
vidare till en annan vuxen invånare så att företag och bostäder inte försvinner
ur ekonomin utan förklaring. Centralbanken finansierar även lån, tar emot ränta
och redovisar reserv, pensionskapital, utlåning och styrränta.

### Mat

Mat skapas endast av bemannade jordbruk. Ett underskott mot befolkningens behov
plus säkerhetsmarginal gör jordbruk mycket attraktivt. Det finns inga importer
som fyller butikslager när lokal produktion saknas.

Matbehovet bedöms från verklig bemanning, inte bara åkermarkens teoretiska
kapacitet. Personer med `lantbruk` som drive reagerar särskilt starkt på behovet
och anställda behåller normalt sitt jordbruksyrke mellan månader. Osåld skörd
lagras på gårdarna i upp till tre månaders produktionskapacitet. Nya gårdar
läggs som sammanhängande 2×2-fält långt från det aktuella centrumet.

### A-kassa

A-kassa aktiveras när dess servicebudget höjs över noll. Ersättningsnivån går
från 25 till 80 procent av baslönen beroende på ambitionsnivå. Bara så många
arbetslösa som det bemannade och finansierade A-kassekontoret hinner handlägga
får ersättning den månaden; längst arbetslösa och ekonomiskt mest pressade går
först. Pengarna överförs från kommunens kassa till invånaren och visas separat
som `A-kassa till invånare` i budgetfönstret. Om kommunen inte har råd sänks
utbetalningen; systemet skapar inte längre nya pengar.
Ersättningen betalas före månadens mat- och boendeköp så att den kan stimulera
jordbruk, handel, hyresvärdar och hotell.

### Kommunens budget

Budgetfönstret skiljer på pengar i kassan, avslutat årsutfall och en prognos för
de kommande tolv månaderna. Prognosen använder dagens befolkning, löneunderlag,
arbetslöshet och servicenivå och visar beräknade intäkter, drift, A-kassa,
årsresultat, kassans uthållighet och skattesatsen som ungefär ger nollresultat.
Varje service visar aktiveringsstatus, politisk ambitionsnivå, tjänstemål,
lokalernas kapacitet, faktiskt bemannade tjänster, täckning, verklig effekt,
belastning samt kostnad per månad och år. Kommunala bygginvesteringar och
privata bygg-/markintäkter redovisas separat i månaden de uppstår.

Finansierad service skapar riktiga kommunala arbetsplatser i relation till
befolkningen: ungefär en tjänst per 20 invånare i skolan, 18 i barnomsorgen, 30
i sjukvården, 80 i polisen, 100 i brandkåren och 120 i A-kasseadministrationen
vid full finansiering. En fysisk byggnad rymmer bara ett begränsat antal
tjänster, så växande behov leder till fler skolor, kliniker och andra
servicebyggnader. Kommunen betalar lönerna och redovisar dem separat.

Serviceeffekten beräknas inte direkt från reglaget. Den kräver samtidigt
lokaler, personal, betald drift och geografisk tillgänglighet från invånarnas
adresser. Avtagande marginalnytta gör dessutom att 100 procent minskar risker
utan att garantera noll kriminalitet, noll sjukdom eller perfekt service.

Effekten landar därefter hos enskilda invånare och byggnader. Sjukvården ger
sjuka en bättre men aldrig säker chans till återhämtning, polisen minskar den
lokala risken att utsättas för brott och brandkårens närhet minskar brandrisken.
Skolan bygger gradvis kompetens hos yngre invånare, vilket ger en liten fördel
i kvalificerade service- och industrijobb. Barnomsorg ger hushåll med barn mer
vardagsork och mindre press. Personvyn visar månadens konkreta händelser och
ackumulerade vård-, brotts-, utbildnings- och barnomsorgserfarenheter. Samma
utfall går att följa som tidsserier i statistikfönstret.

Inkomstskatten hålls inne från varje faktisk månadslön och förs direkt till
kommunen. Den skapar därmed inte längre kommunala pengar utan en motsvarande
kostnad för löntagaren. Prognosen inkluderar full utlovad A-kassa men inte
okända framtida byggprojekt.

Alla ekonomiska rörelser sparas i en transaktionsbok med månad, kategori,
avsändare och mottagare. Interna flöden omfattar bland annat lön, skatt,
pensionsavsättning, hyra, matförsäljning, A-kassa och lån. Pengar som kommer
utifrån redovisas uttryckligen som exempelvis extern försäljning eller
inflyttat kapital; transport, fastighetsdrift och kommunala inköp som ännu
saknar en lokal leverantör redovisas som externa utflöden. Budget- och
statistikvyerna visar total penningmängd, extern balans och eventuell
bokföringsavvikelse. Avvikelsen ska alltid vara exakt `0 SM`.

### Lokal prisbildning

Matpris, rumshyra, lägenhetshyra, hotellpris, lönenivå och byggkostnadsnivå
förändras över tid. Matpriset reagerar på faktisk produktion och gårdslager,
boendepriser på bostadssökande och lediga platser, löner på konkurrensen om
arbetskraft och byggkostnader på både bostads- och arbetsmarknadens tryck.
Priserna rör sig gradvis för att en enskild månad inte ska skapa extrema hopp.

De aktuella priserna används i riktiga köp, hyror, löner, A-kassa,
företagsetableringar och privata samt kommunala byggprojekt. Höga matpriser gör
jordbruk mer attraktivt, höga hyror stärker bostadsincitamentet och dyrare
byggande bromsar nya projekt. Kommunens blockpris är fortfarande ett separat
politiskt styrmedel och multipliceras med den lokala byggkostnadsnivån.

### Bostäder

Tält är tillfälliga och ger framför allt vintertid sämre energi och hälsa.
Privata småhus uppstår aldrig utan en byggherre: en namngiven invånare måste ha
bostadsambition, betala byggkostnaden och behålla en ekonomisk buffert. Ett nytt
hus rymmer ägaren och upp till fyra hyresgäster. Med minst 18 månader mellan
investeringarna kan ägaren utveckla boendet genom `Hydda → Stuga → Villa →
Stort hus`; varje steg kostar pengar och skapar två nya platser. En
jordbruksägares hem redovisas som `Gård`. Driftkostnaden stiger från `1 SM` för
hydda till `10 SM` för stort hus (`5 SM` för gård). Bostaden kan därför fortsätta
utvecklas även när samhället redan har tillräckligt med boendeplatser.

När samhället blivit större kan kommunen bygga centrala flerfamiljshus med 24
lägenhetsplatser. Kommunen betalar byggkostnaden och får hyran. Byggnaderna kan
konverteras till exempelvis skola eller sjukvård när bostadskapaciteten har ett
tillräckligt överskott.

Tält finns kvar som kostnadsfritt reservboende. Hotell är en privat verksamhet
som uppstår när inflyttning och tillfälligt boendebehov motiverar den. Varje
hotellblock har 12 platser och gästen betalar `10 SM` per månad till
hotellföretaget. Nya invånare använder en ledig hotellplats direkt och kan
senare flytta till permanent bostad.

### Företag och arbete

Varje verksamhet får en efterfrågesignal. Potentiella ägare jämför verksamheter
med en poäng baserad på efterfrågan, förväntad intäkt, kapital och personlig
preferens. Högst rimlig poäng vinner; slump används endast för små variationer
som placering och individuella egenskaper.

Jobb är avståndsberoende. Invånaren väljer det billigaste transportsätt som når
arbetet: gång når 5 block gratis, cykel 18 block (`35 SM` att köpa och `1 SM`
per månad), buss 45 block (`5 SM` per månad) och bil 65 block (`220 SM` att
köpa och `16 SM` per månad). Det gör bilen till ett dyrt val för verkligt långa
resor i stället för en allmän statuspryl. Valet grundas på personens verkliga
arbetsadress. En gårdsägare kan arbeta på sin egen mark, medan anställda måste
kunna ta sig dit.

Anställda behåller normalt sitt arbete, men nya bättre betalda företag kan
rekrytera ett begränsat antal personer varje månad. En ort med full
sysselsättning låser därmed inte ute all ny handel och industri. Mataffärer får
en del av invånarnas verkliga matköp och centralbanken kan finansiera ett ungt
företags första löner. Antalet nya butiker och industrier begränsas samtidigt
av befolkningens efterfrågan. En obemannad verksamhet får 18 månader att öppna
innan platsen överges.

### Dynamiskt centrum

Torget ger startområdet en liten fördel men är inte ett permanent centrum.
Varje aktivt block får ett centralitetsvärde av sin egen aktivitet och närheten
till handel, service, arbetsplatser och bostäder. `World.central_blocks()` visar
de för tillfället starkaste platserna. Centrum kan därmed växa, flytta eller
försvagas när verksamheter förändras.

Kartblock kan klickas för att visa adress, byggnadstyp, ägare, centralitet,
boendekapacitet, verksamhetens kassa och resultat, anställda samt vilka som bor
på adressen.

Kartan och detaljvyerna använder pixelsprites från projektets `UX`-mapp. Ett
klick på ett block öppnar en kvartersvy med en stor byggnadsbild, verksamhetens
månadsekonomi och en kort förklaring av hur platsen påverkar samhället. Boende
och personer som arbetar på blocket är klickbara och leder till en personvy.
Porträttet följer personens identitet men byter åldersvariant under livet.
Personvyn samlar yrke, intresse, adress, resa, inkomst, levnadskostnad,
pensionssparande och de senaste 16 inköpen. Den förklarar också de aktuella
orsakerna bakom personens hälsa och missnöje.

Aktiverad samhällsservice får nu också en fysisk byggnad: polisstation,
brandkår, sjukvård, skola, barnomsorg eller A-kassa. Servicebyggnader och
befolkning skapar fler centrumblock omkring den starkaste lokala kärnan. Alla
dessa investeringar belastar kommunens kassa; de är inte kostnadsfria kartfält.

Byggbar yta går nu fram till en blocks marginal i stället för att lämna tre
oförklarligt tomma rader och kolumner. Nya bostäder söker sig mot befintliga
bostadskvarter och bort från industri. Industrier söker sig på motsvarande sätt
till andra industrier och bort från bostäder och gårdar; etablering nära sådana
känsliga grannar får dessutom en mark- och skyddskostnad. Bostäder och
industrier har en mindre chans att grunda ett nytt fristående område. Jordbruk
följer oftast befintlig odlingsbygd men ungefär var femte grundare kan välja ny
mark på en annan del av kartan. Därmed bryts den tidigare diagonala och
hörnbundna tillväxten.

## Kodstruktur

- `main.py` startar skrivbordsprogrammet.
- `ui.py` innehåller CustomTkinter-gränssnittet.
- `models.py` innehåller sparbara datamodeller.
- `world.py` innehåller behov, efterfrågan och månadsflödet.
- `tests/` verifierar grundregler, stabilitet och prestanda.

Sparfiler är fortsatt vanliga dictionaries/JSON-data. Nya fält har standardvärden
så att äldre invånare, byggnader och arbetsplatser kan läsas in.
