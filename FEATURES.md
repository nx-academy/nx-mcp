# Features IA — Roadmap

Ce document détaille les prochaines features IA envisagées pour `nx-mcp`.
Chacune réutilise le **pattern déjà en place** pour le quiz et le recap :

> **fonction workflow** (`nx_ai/workflows/`) → **tool MCP** (`server.py`) →
> génération OpenAI (`nx_ai/openai_service/openai_api.py`) → écriture locale →
> **PR sur `nx-academy.github.io`** (`create_pull_request_on_github`).

Conventions partagées :
- Le **nom de fichier** est dérivé via `slugify_title` / `slug_from_url`
  (`nx_ai/utils/slugify.py`).
- Chaque génération expose un paramètre **`simulate`** (dry-run : mocke l'appel
  OpenAI **et** saute la PR, voir `mock/`).
- Les fonctions workflow renvoient un dict `{filename, <contenu>, pr_url}`.
- Les prompts longs vivent dans `prompts/` (ex. `fetch_news_gpt.txt`).
- Les réponses GPT sont enveloppées dans un modèle de `nx_ai/openai_service/gpt_models.py`.

---

## 1. Générateur de cours / leçons

**Objectif** : produire une leçon Markdown structurée (format Astro) à partir d'un
sujet ou d'une liste de sources, puis ouvrir une PR. C'est l'extension naturelle du
recap, mais orientée pédagogie (cours complet plutôt que résumé d'articles).

**Tool MCP** (`server.py`)
```python
@mcp.tool()
def generate_lesson(title: str, sources: list[str] | None = None,
                    simulate: bool = False) -> dict:
    """Generate a structured Markdown lesson (intro, sections, examples,
    conclusion) and open a PR on nx-academy.github.io."""
```

**Fichiers à créer / modifier**
| Fichier | Rôle |
|---------|------|
| `nx_ai/workflows/generate_lesson.py` | `generate_lesson_beta(title, sources, filename, simulate)` — calque de `generate_recap.py` |
| `nx_ai/openai_service/openai_api.py` | `generate_lesson_with_gpt(title, sources, simulate)` |
| `nx_ai/openai_service/gpt_models.py` | `GPTGeneratedLesson` (sortie Markdown ou structurée) |
| `prompts/generate_lesson.txt` | prompt dédié (plan, sections, exemples de code, ton NX) |
| `nx_ai/github_service/github_api.py` | nouveau `type="lesson"` → path `src/pages/cours/{filename}.md`, branche `ai_{filename}-lesson` |
| `mock/generated_lesson.md` | mock pour le mode simulate |
| `tests/` | test du parsing `GPTGeneratedLesson` |

**Format de sortie** : Markdown avec frontmatter Astro (réutiliser le bloc de
`generate_recap.py` comme base), titre = `title`, sections `##`, blocs de code,
objectifs pédagogiques en intro, récap en conclusion.

**Note** : penser au découpage si la leçon est longue (le modèle peut générer un
plan d'abord, puis chaque section — itération possible plus tard).

**Effort estimé** : moyen (le plus gros est le prompt et la structure du contenu).

---

## 2. Flashcards / fiches de révision

**Objectif** : générer une liste de flashcards (question / réponse) à partir d'un
article, en complément du quiz. Sortie JSON, même cycle de PR que le quiz.

**Tool MCP** (`server.py`)
```python
@mcp.tool()
def generate_flashcards(url: str, simulate: bool = False) -> dict:
    """Generate revision flashcards (question/answer) from an article URL and
    open a PR on nx-academy.github.io."""
```

**Fichiers à créer / modifier**
| Fichier | Rôle |
|---------|------|
| `nx_ai/workflows/generate_flashcards.py` | `generate_flashcards_beta(url, filename, simulate)` — calque de `generate_quiz.py` |
| `nx_ai/openai_service/openai_api.py` | `generate_flashcards_with_gpt(url, simulate)` (web_search_preview comme le quiz) |
| `nx_ai/openai_service/gpt_models.py` | `GPTGeneratedFlashcards` (calque de `GPTGeneratedQuiz`) |
| `nx_ai/github_service/github_api.py` | `type="flashcards"` → path `public/flashcards/{filename}.json` |
| `mock/generated_flashcards.json` | mock simulate |
| `tests/` | test du parsing |

**Format de sortie** (JSON)
```json
{ "data": [ { "front": "Question / terme", "back": "Réponse / définition" } ] }
```

**Réutilisation** : la structure est quasi identique au quiz — partir de
`generate_quiz_with_gpt` et adapter le prompt (`prompts/generate_flashcards.txt`)
pour viser un format recto/verso de révision plutôt qu'un QCM.

**Effort estimé** : faible (le plus proche de l'existant).

---

## 3. Tool RAG — recherche dans le vector store

**Objectif** : exposer la recherche dans le **vector store OpenAI** (corpus de style
NX, déjà géré dans `nx_ai/vector_store_service/`) comme tool MCP en **lecture seule**.
Permet d'interroger les contenus/le style existants depuis Claude — **pas de PR**.

**Tool MCP** (`server.py`)
```python
@mcp.tool()
def search_style_corpus(query: str, simulate: bool = False) -> dict:
    """Search the NX style corpus (OpenAI vector store) and return the most
    relevant passages. Read-only, no PR."""
```

**Fichiers à créer / modifier**
| Fichier | Rôle |
|---------|------|
| `nx_ai/vector_store_service/vector_store_api.py` | une fonction `search_vector_store(query, simulate)` si elle n'existe pas déjà (sinon réutiliser le `file_search` déjà branché dans `rewrite_summary_with_personal_style`) |
| `server.py` | nouveau tool `search_style_corpus` |
| `mock/vector_store_search.json` | mock simulate |

**Détails techniques**
- Réutilise `VECTOR_STORE_ID` (env) et l'outil `file_search` déjà employé par
  `rewrite_summary_with_personal_style` (`openai_api.py`).
- Retourne une liste de passages : `[{ "text": "...", "score": 0.83, "source": "..." }]`.
- **Pas** de side-effect GitHub : c'est un tool d'exploration/lecture.

**Effort estimé** : faible à moyen (selon ce que l'API vector store renvoie déjà).

---

## Pistes complémentaires (non priorisées)

- **Amélioration du recap** : titre / description / image dynamiques, vrais liens
  « Lire l'article » (aujourd'hui `#` en dur dans `generate_recap.py`).
- **Quiz / flashcards multi-sources** : accepter plusieurs URLs en entrée.
- **Scoring / feedback de quiz** : tool qui évalue les réponses d'un apprenant et
  renvoie un feedback personnalisé.
- **Support multi-provider** : abstraire l'appel LLM pour pouvoir basculer
  OpenAI ↔ Claude (Anthropic SDK).
