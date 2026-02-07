import re
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console # noqa: E402

from orchestrator.agent import run_agent # noqa: E402
from orchestrator.registry import SkillRegistry # noqa: E402
from skill_factory.factory import remove_skill  # noqa: E402
from integrations.telegram_manager import TelegramManager  # noqa: E402

console = Console()


def cleanup(registry: SkillRegistry) -> None:
    """Stop and remove all running skill containers."""
    skills = registry.list_skills()
    if not skills:
        return
    console.print(f"[yellow]Cleaning up {len(skills)} skill container(s)...[/yellow]")
    for skill_info in skills:
        skill = registry.lookup(skill_info["name"])
        if skill:
            try:
                remove_skill(skill)
                console.print(f"  Removed {skill.name}")
            except Exception:
                pass


HELIX_BANNER = r"""#########################################################################
#                                            __                         #
#   _   _  _____ _      _____  __           /  \      Helix             #
#  | | | || ____| |    |_ _\ \/ /          / /\ \     v1.0.0            #
#  | |_| ||  _| | |     | | \  /          | |  | |    --------------    #
#  |  _  || |___| |___  | | /  \           \ \/ /     [STATUS: ACTIVE]  #
#  |_| |_||_____|_____||___/_/\_\           \  /                        #
#                                           /  \                        #
#   Skills that evolve on demand.          / /\ \                       #
#                                         | |  | |                      #
#                                          \ \/ /                       #
#                                           \  /                        #
#                                            \/                         #
#########################################################################"""


def expand_file_references(text: str) -> str | None:
    """Replace @filepath patterns with the file's contents.

    Returns the expanded string, or None if a referenced file is missing.
    """
    pattern = r"@([\w./\-]+)"
    matches = re.findall(pattern, text)
    if not matches:
        return text

    for filepath in matches:
        path = Path(filepath)
        if not path.exists():
            console.print(f"[red]File not found: {filepath}[/red]")
            return None
        contents = path.read_text()
        text = text.replace(f"@{filepath}", f"\n\n[Contents of {filepath}]:\n{contents}")

    return text


def main():
    console.print(f"[green]{HELIX_BANNER}[/green]", highlight=False)
    console.print("\n\n")
    console.print("[bold]Helix — Skills that evolve on demand.[/bold]")
    console.print("Type a task and the agent will create skills to solve it.")
    console.print("Type 'quit' to exit.\n")

    registry = SkillRegistry()
    telegram_manager = TelegramManager()

    try:
        while True:
            user_input = console.input("[bold green]> [/bold green]").strip()

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                break

            user_input = expand_file_references(user_input)
            if user_input is None:
                continue

            try:
                response = run_agent(user_input, registry, _telegram_manager=telegram_manager)
                console.print(f"\n[bold]{response}[/bold]\n")
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]\n")
    except KeyboardInterrupt:
        console.print("\n")
    finally:
        telegram_manager.stop()
        cleanup(registry)
        console.print("[dim]Goodbye.[/dim]")


if __name__ == "__main__":
    main()
