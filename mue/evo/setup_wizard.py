"""MUE Setup Wizard — First-run interactive configuration.

Runs ONLY on first launch (0 genes). Asks user for:
- Language preference (English / Francais)
- Domain specialization
- Objectives / goals
- Working style / evolution strategy
- Agent name

All messages are bilingual. After setup, saves mue_config.json
and the agent boots into evolution mode.
"""

import json
import sys
from pathlib import Path

# ── BILINGUAL STRINGS ─────────────────────────────────────────────────────

T = {
    "en": {
        "welcome": """
  MUE v0.9 — Self-Evolving AI Agent

  Welcome! I'm MUE, an autonomous agent that evolves by modifying
  its own source code. Before I begin, let me ask a few questions
  to configure myself for your needs.

""",
        "lang_q": "  Language / Langue — [EN] English or [FR] Francais ? ",
        "lang_invalid": "  Please type EN or FR.",
        "name_q": "  Give me a name (or press Enter for 'Mue'): ",
        "domain_intro": """
  What should I specialize in?

    1. Trading — market analysis, strategies, risk management
    2. Coding — software engineering, algorithms, automation
    3. Research — data analysis, papers, experiments
    4. Creative — writing, design, content generation
    5. Security — vulnerability analysis, hardening
    6. General — all-purpose, adapt dynamically
""",
        "domain_q": "  Choose [1-6] (default: 6): ",
        "domain_invalid": "  Please enter 1-6.",
        "objectives_q": "  What are your main objectives? (comma-separated, or press Enter): ",
        "style_intro": """
  How should I work?

    1. Balanced — careful mutations, steady improvement
    2. Bold — aggressive exploration, more risk
    3. Conservative — only fix bugs, minimal changes
    4. Innovative — prioritize novel approaches
""",
        "style_q": "  Choose [1-4] (default: 1): ",
        "style_invalid": "  Please enter 1-4.",
        "done": """
  Configuration complete! I'll now boot up and begin evolving.

  Type /help mue to see available commands.
  Type /quit mue to return to normal Claude Code.
  Type /mue status to see my current state.

  Starting evolution...
""",
        "yes": "yes",
        "no": "no",
        "domain_names": ["trading", "coding", "research", "creative", "security", "general"],
        "style_names": ["balanced", "bold", "conservative", "innovative"],
    },
    "fr": {
        "welcome": """
  MUE v0.9 — Agent IA Auto-Evolutif

  Bienvenue ! Je suis MUE, un agent autonome qui evolue en modifiant
  son propre code source. Avant de commencer, laissez-moi vous poser
  quelques questions pour me configurer selon vos besoins.

""",
        "lang_q": "  Language / Langue — [EN] English or [FR] Francais ? ",
        "lang_invalid": "  Tapez EN ou FR.",
        "name_q": "  Donnez-moi un nom (ou Entree pour 'Mue'): ",
        "domain_intro": """
  Dans quel domaine dois-je me specialiser ?

    1. Trading — analyse de marches, strategies, gestion de risque
    2. Coding — genie logiciel, algorithmes, automatisation
    3. Recherche — analyse de donnees, articles, experiences
    4. Creatif — ecriture, design, generation de contenu
    5. Securite — analyse de vulnerabilites, durcissement
    6. General — tout domaine, adaptation dynamique
""",
        "domain_q": "  Choisissez [1-6] (defaut: 6): ",
        "domain_invalid": "  Veuillez entrer 1-6.",
        "objectives_q": "  Quels sont vos objectifs principaux ? (separes par des virgules, ou Entree): ",
        "style_intro": """
  Comment dois-je travailler ?

    1. Equilibre — mutations prudentes, amelioration constante
    2. Audacieux — exploration agressive, plus de risques
    3. Conservateur — seulement corriger les bugs, changements minimaux
    4. Innovant — prioriser les approches nouvelles
""",
        "style_q": "  Choisissez [1-4] (defaut: 1): ",
        "style_invalid": "  Veuillez entrer 1-4.",
        "done": """
  Configuration terminee ! Je vais maintenant demarrer et commencer a evoluer.

  Tapez /help mue pour voir les commandes disponibles.
  Tapez /quit mue pour revenir a Claude Code normal.
  Tapez /mue status pour voir mon etat actuel.

  Demarrage de l'evolution...
""",
        "yes": "oui",
        "no": "non",
        "domain_names": ["trading", "coding", "research", "creative", "security", "general"],
        "style_names": ["balanced", "bold", "conservative", "innovative"],
    },
}


class SetupWizard:
    """Interactive first-run configuration wizard."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.lang = "en"
        self.config = {}

    def msg(self, key: str) -> str:
        return T[self.lang].get(key, T["en"][key])

    def ask(self, prompt_key: str) -> str:
        """Ask a question and return answer."""
        try:
            return input(self.msg(prompt_key)).strip()
        except (EOFError, KeyboardInterrupt):
            return ""

    def run_interactive(self) -> dict:
        """Full interactive setup. Returns config dict."""
        print(self.msg("welcome"))

        # 1. Language
        while True:
            lang = self.ask("lang_q").upper()
            if lang in ("EN", "FR", ""):
                self.lang = "en" if lang in ("EN", "") else "fr"
                break
            print(self.msg("lang_invalid"))

        print()  # spacer

        # 2. Name
        name = self.ask("name_q")
        if name:
            self.config["name"] = name

        # 3. Domain
        print(self.msg("domain_intro"))
        while True:
            domain_choice = self.ask("domain_q")
            if not domain_choice:
                domain_choice = "6"
            if domain_choice in ("1", "2", "3", "4", "5", "6"):
                idx = int(domain_choice) - 1
                self.config["domain"] = self.msg("domain_names")[idx]
                break
            print(self.msg("domain_invalid"))

        # 4. Objectives
        objectives = self.ask("objectives_q")
        if objectives:
            self.config["objectives"] = [o.strip() for o in objectives.split(",") if o.strip()]

        # 5. Working style
        print(self.msg("style_intro"))
        while True:
            style_choice = self.ask("style_q")
            if not style_choice:
                style_choice = "1"
            if style_choice in ("1", "2", "3", "4"):
                idx = int(style_choice) - 1
                self.config["evolution_strategy"] = self.msg("style_names")[idx]
                break
            print(self.msg("style_invalid"))

        # 6. Save
        self.config["language"] = self.lang
        self.config["setup_complete"] = True
        self.config_path.write_text(json.dumps(self.config, indent=2), encoding="utf-8")

        print(self.msg("done"))
        return self.config

    def run_noninteractive(self, answers: dict = None) -> dict:
        """Non-interactive setup from pre-provided answers (for Claude Code chat mode).

        If answers not provided, returns the questions that need answering.
        """
        if answers:
            self.lang = answers.get("language", "en")
            self.config = {
                "name": answers.get("name", "Mue"),
                "domain": answers.get("domain", "general"),
                "objectives": answers.get("objectives", []),
                "evolution_strategy": answers.get("evolution_strategy", "balanced"),
                "language": self.lang,
                "setup_complete": True,
            }
            self.config_path.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
            print(self.msg("done"))
            return self.config

        # Return the questionnaire for the LLM to ask
        return {
            "needs_setup": True,
            "questions": {
                "language": {
                    "text": T["en"]["lang_q"],
                    "options": ["EN", "FR"],
                    "default": "EN",
                },
                "name": {
                    "text": T["en"]["name_q"],
                    "default": "Mue",
                },
                "domain": {
                    "text": T["en"]["domain_intro"],
                    "options": [1, 2, 3, 4, 5, 6],
                    "default": 6,
                    "labels": T["en"]["domain_names"],
                },
                "objectives": {
                    "text": T["en"]["objectives_q"],
                },
                "evolution_strategy": {
                    "text": T["en"]["style_intro"],
                    "options": [1, 2, 3, 4],
                    "default": 1,
                    "labels": T["en"]["style_names"],
                },
            },
        }
