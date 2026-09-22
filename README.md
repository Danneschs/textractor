#
# Textractor
**Autor:** Daniel Sibolerski

Nástroj Textractor byl vytvořen jako součást bakalářské práce na Katedře informatiky a výpočetní techniky Fakulty aplikovaných věd Západočeské univerzity v Plzni.

Téma práce: [Vyhodnocení schopnosti LLM analyzovat projektovou dokumentaci a těžit z ní klíčové parametry](https://portal.zcu.cz/StagPortletsJSR168/CleanUrl?urlid=prohlizeni-prace-detail&praceIdno=104281)

Nástroj Textractor umožňuje extrakci a formalizaci informací z nestrukturovaných dokumentů typu PDF. Otestování proběhlo konkrétně na specifikacích softwarových požadavků.

## Postup běhu
1. Načtení dokumentů ze složky ```data/raw_pdfs```.
2. Převedení na text a uložení do databáze (```data/database.db```). Pokud databáze neexistuje, bude automaticky vytvořena.
3. Poslání textu z dokumentů vybranému LLM.
4. Nahrání výstupů z LLM (extrahované/formalizované informace) do databáze.
5. Spuštění grafického uživatelského rozhraní Textractor Studio, které umožní ruční vyhodnocení této extrakce/formalizace.

## Podporované jazykové modely
Podporované a vyzkoušené jazykové modely jsou:
- ```gpt-5.4-nano```
- ```mistral-large-latest```
- `llama3.2:latest` (lokální model)

## Adresářová struktura
```bash
.
├── analysis                                            # model pro vizualizaci výsledků v Power BI
├── app                                                 # složka s nástrojem Textractor
│   ├── data                                            # vstupní a výstupní data
│   │   ├── golden_seed                                 # ručně extrahované a formalizované požadavky
│   │   └── raw_pdfs                                    # původní dokumenty pro extrakci a formalizaci
│   ├── example.env                                     # příklad souboru .env
│   ├── gui.py                                          # spouštěcí skript rozhraní Textractor Studio
│   ├── requirements.txt                                # požadované knihovny
│   ├── setup.bat                                       # sestavovací skript pro Windows
│   ├── setup.sh                                        # sestavovací skript pro Linux
│   ├── src                                             # zdrojové kódy aplikace
│   │   ├── database                                    # správa databáze
│   │   │   ├── __init__.py
│   │   │   ├── manager.py
│   │   │   ├── models.py
│   │   │   └── repository
│   │   │       ├── analyzed_text_eval.py
│   │   │       ├── analyzed_text.py
│   │   │       ├── document.py
│   │   │       ├── extracted_text_eval.py
│   │   │       ├── extracted_text.py
│   │   │       ├── extraction_run.py
│   │   │       ├── __init__.py
│   │   │       ├── model.py
│   │   │       └── prompt.py
│   │   ├── documents                                   # načítání a zpracování dokumentů
│   │   │   ├── ingestors.py
│   │   │   ├── __init__.py
│   │   │   ├── loaders.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   └── writers.py
│   │   ├── gui                                         # grafické uživatelské rozhraní Textractor studio
│   │   │   ├── base.py
│   │   │   ├── benchmark.py
│   │   │   ├── card_mapper.py
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── production.py
│   │   │   ├── session_states.py
│   │   │   └── strings.py
│   │   ├── __init__.py
│   │   ├── llms                                        # rozhraní pro komunikaci s LLM
│   │   │   ├── backends.py
│   │   │   ├── config.py
│   │   │   ├── __init__.py
│   │   │   └── schemas.py
│   │   ├── pipeline                                    # skripty pro extrakci a formalizaci
│   │   │   ├── extractor.py
│   │   │   ├── formalizer.py
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py
│   │   │   └── phase.py
│   │   └── utils.py                                    # pomocné funkce
│   └── textractor.py                                   # hlavní spouštěcí skript programu Textractor
├── doc                                                 # text práce
│   ├── fasthesis.cls
│   ├── img
│   ├── main.pdf
│   ├── main.tex
│   └── res
└── README.md

```

## Uživatelská příručka
Tato uživatelská příručka informuje o instalaci a spuštění programu Textractor na operačních systémech Microsoft Windows a Linux.

### Minimální požadavky
Spuštění aplikace bylo testováno na následujících technologiích:

1. Operační systém Microsoft Windows 11 nebo Linux (konkrétně Fedora verze 43).
2. Interpreter jazyka **Python** verze 3.14.3.
3. Správce balíčků pro Python -- **pip** verze 26.0.1.
4. Virtuální prostředí pro Python -- **venv**.

### Instalace a spuštění
Spuštění programu Textractor se dá docílit následujícími kroky:

1. Naklonovat tento repozitář.
2. Přesunout se do kořenového adresáře programu Textractor v `app/`.
3. Spustit skript `setup.sh` (pro Linux,  například pomocí příkazu `./setup.sh`.), případně `setup.bat` (pro Windows, například pomocí příkazu `setup.bat` nebo dvojím kliknutím).
4. Naplnění (případně vytvoření) souboru `.env` pro uložení proměnných do prostředí běhu, pokud není potřeba používat **jen Textractor Studio v evaluačním režimu**. Pro tyto účely je vhodné upravit připravený soubor `example.env`.
5. Nastavení virtuálního prostředí v terminálu příkazem `source .venv/bin/activate` (pro Linux), případně `.venv\Scripts\activate`.
6. Spuštění samotného programu příkazem `python3 textractor.py`, případně `py textractor.py` (pro Windows).
7. Po splnění předchozích kroků stačí následovat instrukce v terminálu od programu Textractor.

V případě nevyplnění potřebného API klíče je možné, že některé jazykové modely nebudou dostupné.

#### Instalační skript
Instalační skript vytvoří ve spouštěné složce (doporučeno spouštět v kořenovém adresáři projektu) virtuální prostředí pro jazyk Python. Dále v něm aktualizuje správce balíčků pip, pomocí kterého dalším příkazem nainstaluje potřebné knihovny pro běh programu:
- `streamlit` verze 1.55.0,
- `streamlit_pdf_viewer` verze 0.0.28,
- `tqdm` verze 4.67.3,
- `typing_extensions` verze 4.15.0.
- `python-dotenv` verze 1.2.2
- `pydantic` verze 2.12.5
- `pdfplumber` verze 0.11.9
- `openai` verze 2.30.0
- `mistralai` verze 2.1.3
- `ollama` verze 0.6.1
- `pypdfium2` verze 5.6.0
Tyto knihovny a jejich verze se nachází v souboru `requirements.txt`.

#### Soubor s proměnnými prostředí běhu
Soubor `.env` obsahuje proměnné prostředí, kde s některými program při běhu počítá a nelze ho bez nich spustit.

Důlěžité proměnné jsou API klíče pro jazykové modely použité pro extrakční a formalizační fázi v programu Textractor. Program počítá s tím, že jsou použité pouze jazykové modely společností OpenAI (proměnná s názvem `OPENAI_API_KEY`) a Mistral (proměnná s názvem `MISTRAL_API_KEY`). Případně lze použít lokální model Llama od společnosti Meta, kde API klíč není potřeba.

Při použití rozhraní Textractor Studio, tedy pro evaluaci již extrahovaných požadavků tyto proměnné pro API klíče nejsou potřebné. Pro vyhodnocení je možné doplnit volitelnou proměnnou `MODE`, která označuje, zda se má Textractor Studio spustit v produkčním nebo evaluačním režimu. Bez definování této proměnné se standardně `Textractor Studio` spustí v evaluačním režimu. Pro produkční je nutné použít `MODE=production` a pro evaluační režim `MODE=benchmark`.

Proměnná `DATABASE_PATH` určuje cestu k databázi, případně cestu, kde bude databáze vytvořena. Pokud není nastavena, použije se cesta `data/database.db`.

Výsledný soubor `.env` může vypadat například následovně:

```
OPENAI_API_KEY=api-klic-pro-openai
MISTRAL_API_KEY=api-klic-pro-mistral
DATABASE_PATH=data/database.db
MODE=benchmark
```

#
## Analýza výsledků
Pro analýzu a kontrolu výsledků byl použt [Microsoft PowerBI Desktop](https://powerbi.microsoft.com/desktop/) verze 2.153.910.0 64-bit (duben 2026), je však možné využít jiné vizualizační nástroje. Je nutné použít databázi, která obsahuje již ohodnocené výstupy LLM pomocí Textractor Studio.

Ve složce `analysis/` v kořenovém adresáři repozitáře se nachází vytvořené vizualizace v Microsoft PowerBI Desktop, které je možné naimportovat a využít.