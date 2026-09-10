# DriftLine – grundbeskrivning v2

DriftLine är en lokal samhälls- och ekonomisimulator där ett litet samhälle växer fram organiskt från ett enkelt handelscentrum.

Simuleringen ska börja med grundläggande behov:

**mat → bostad → arbete → handel → service → mer avancerad ekonomi**

Invånarnas beslut ska främst styras av deras behov och den lokala ekonomin, inte av fasta sannolikheter.

## Grundprincip

Varje invånare försöker i första hand säkra:

1. mat
2. tak över huvudet
3. inkomst
4. trygghet
5. bekvämlighet/status

När de grundläggande behoven är stabila kan de börja fatta mer avancerade beslut som att starta företag, investera, flytta till bättre bostad eller köpa statusvaror.

## Samhällets start

Världen börjar mycket enkelt:

- ett litet torg eller handelsplats
- ett fåtal invånare
- inga färdiga företag
- enkel möjlighet till jordbruk
- tält eller mycket enkla bostäder
- mycket begränsad samhällsservice

De första invånarna ska naturligt dras mot verksamheter som samhället faktiskt behöver.

Om samhället saknar matproduktion ska sannolikheten att någon börjar med jordbruk öka kraftigt.

Om det finns mat men för lite bostäder ska byggande och bostadsrelaterade investeringar bli mer attraktiva.

Om grundbehoven är täckta kan andra företag börja växa fram.

## Jordbruk

Jordbruk är samhällets första basnäring.

Invånare ska inte välja jordbruk huvudsakligen på personlighet. Behovet i samhället ska väga tungt.

Exempel:

```text
matbehov = befolkningens förväntade konsumtion
matproduktion = befintlig jordbruksproduktion

om matproduktion < matbehov * säkerhetsmarginal:
    jordbruk blir mycket attraktivt
```

Personliga egenskaper kan fortfarande påverka valet, men samhällets behov ska väga tyngre.

Det gör att exempelvis en person med `lantbruk`-drivning reagerar tidigare på matbrist, medan även andra invånare kan börja odla om bristen blir tillräckligt stor.

## Företagande

En invånare startar företag när tre saker sammanfaller:

**efterfrågan + kapital + möjlighet**

Företag ska därför inte skapas huvudsakligen genom slump.

Varje verksamhet får ett uppskattat lokalt behov:

```text
business_score =
    demand
    * expected_profit
    * personal_preference
    * available_capital
```

Invånaren väljer det alternativ som ger bäst rimlig möjlighet.

Det innebär att en by med matbrist producerar fler jordbrukare, medan ett större samhälle med hög köpkraft kan få restauranger, serviceföretag och industri.

## Bostäder

Invånare ska aktivt försöka lämna tält när de ekonomiskt kan.

Ett tält är en tillfällig lösning och ska ha tydliga nackdelar:

- sämre hälsa
- högre vinterrisk
- lägre komfort
- begränsad möjlighet till statusvaror

Invånare ska jämföra:

```text
kostnad för bostad
mot
risk och kostnad för fortsatt tältboende
```

Om en invånare har råd med en enkel bostad och förväntas kunna behålla en ekonomisk buffert efter köpet ska personen normalt bygga eller köpa bostad.

De ska kunna:

- bygga eget
- köpa bostad
- hyra
- bo hos annan
- ha inneboende

Det gör att bostadsmarknaden kan fungera även innan alla har råd med eget hus.

## Byggbeslut

Byggande ska styras av konkret bostadsbrist.

Exempel:

```text
om antal människor i tält är högt
och betalningsförmåga finns:
    bostadsbyggande blir attraktivt
```

En rik invånare ska kunna bygga fler bostäder och hyra ut dem.

Därmed kan bostadsföretag uppstå naturligt ur efterfrågan.

## Centrum

Centrum ska inte vara en fast ruta i mitten av kartan.

I stället ska centrum vara ett resultat av aktivitet.

Varje block kan få ett **centralitetsvärde** baserat på exempelvis:

- handel
- offentliga tjänster
- arbetsplatser
- befolkningstäthet
- trafik/rörelse
- närhet till andra centrala block

Exempel:

```text
centrality =
    shops * 3
    + services * 3
    + workplaces * 2
    + residents
```

När flera block med högt centralitetsvärde ligger nära varandra uppstår ett centrum.

Centrum kan därför:

- växa
- flytta
- delas i flera centrum
- försvagas om verksamheter läggs ned

Torget kan vara startpunkten, men ska inte definiera centrum för alltid.

## Samhällsservice

Offentlig service ska växa efter befolkning och behov.

Exempel:

- liten bosättning: ingen eller mycket begränsad service
- växande by: enklare vård/skola
- större samhälle: polis, brandkår, barnomsorg
- stad: flera servicepunkter

Service ska samtidigt bidra till centralitet och därmed påverka var centrum utvecklas.

## Inflyttning

Människor flyttar in när samhället erbjuder rimliga möjligheter.

Inflyttning påverkas av:

- lediga jobb
- tillgång till mat
- bostadsmöjligheter
- stabilitet
- lönenivå
- service

En person kan acceptera tältboende om jobb och framtidsutsikter är goda.

Människor ska däremot inte fortsätta flytta in i stor omfattning när samhället redan har allvarlig mat- eller bostadsbrist.

## Utflyttning

Utflyttning ska ske gradvis.

En person lämnar inte automatiskt samhället efter en enstaka dålig vinter.

Det bör finnas ett slags **missnöjesvärde** som byggs upp över tid:

```text
unemployment
hunger
homelessness
low stability
lack of opportunity
```

När missnöjet varit högt under flera månader ökar sannolikheten för utflyttning.

## Ekonomisk utveckling

Samhällets naturliga ekonomiska utveckling kan ungefär följa:

```text
Jordbruk
↓
Matöverskott
↓
Befolkningsökning
↓
Bostadsbyggande
↓
Handel
↓
Service
↓
Specialiserade företag
↓
Industri / avancerade tjänster
```

Det behöver inte ske exakt i den ordningen, men ekonomin bör normalt bygga ovanpå tidigare nivåer.

## Viktig förändring i modellen

**Drives bör påverka hur invånaren löser ett behov, snarare än vilket behov den bryr sig om.**

En `företagare` och en `lantbruk`-person blir fortfarande olika individer. Men båda äter. Båda behöver bostad. Båda reagerar på ekonomiska möjligheter.

Personlighet ska därför justera beteende och trösklar, inte ersätta grundläggande behov.

## Rekommenderad riktning för omskrivningen

Bygg om beslutslogiken kring behov och efterfrågan först.

Behåll UI och datamodeller där det är möjligt.

Prioritera stabil emergent tillväxt framför fler funktioner.

Börja inte med att justera sannolikheten för att bli bonde. Ändra först **varför någon blir bonde**.

## Bakgrund från nuvarande version

Den nuvarande modellen har flera regler som bidrar till instabil utveckling:

- Jobb skapas bara genom invånarägda arbetsplatser.
- Jordbruk konkurrerar med andra företagsval.
- Invånare börjar i tält och bostäder kräver aktivt köp av block.
- Hunger, vinter, arbetslöshet och hälsa påverkar stabilitet och utflyttning.
- Centrum är idag fast definierat i mitten av kartan.

Det gör att simuleringen lätt kan hamna i en negativ spiral:

```text
för få bönder
↓
matbrist
↓
lägre stabilitet
↓
utflyttning
↓
färre företag och färre arbetare
↓
ännu lägre produktion
```

Omskrivningen bör därför fokusera på återkopplingsloopar där grundbehoven skapar tydliga ekonomiska incitament och där samhället får chans att stabilisera sig innan mer avancerade verksamheter växer fram.
